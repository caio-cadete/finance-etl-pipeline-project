def create_schema(cursor):
    """
    Define a arquitetura do banco de dados relacional.
    Organizado em: Tabelas -> Triggers -> Views Analiticas.
    """
    # Ativa integridade referencial
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. DEFINIÇÃO DE TABELAS (Entidades)
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tb_clientes (
            cliente_id INTEGER PRIMARY KEY,
            nome_cliente TEXT,
            email TEXT,
            status_cliente TEXT,
            cidade TEXT,
            estado TEXT,
            data_cadastro DATE,
            data_desativacao DATE,
            CHECK (
                (data_desativacao IS NOT NULL AND status_cliente = 'Cancelado') OR 
                (data_desativacao IS NULL AND status_cliente = 'Ativo')
            )
        );

        CREATE TABLE IF NOT EXISTS tb_cobrancas (
            cobranca_id INTEGER PRIMARY KEY,
            cliente_id INTEGER,
            valor_cobranca REAL,
            data_vencimento DATE,
            status_cobranca TEXT,
            tipo_cobranca TEXT,
            forma_pagamento TEXT,
            criado_em DATE,
            data_pagamento DATE,
            FOREIGN KEY (cliente_id) REFERENCES tb_clientes (cliente_id) 
                ON DELETE CASCADE 
                ON UPDATE CASCADE
        );
    """)
    print("   ✔️  Entidades: tb_clientes e tb_cobrancas configuradas.")

    # 2. REGRAS DE NEGOCIO (Automaçes via Triggers)
    cursor.executescript("""
        CREATE TRIGGER IF NOT EXISTS tr_sincronizar_status_insert
        AFTER INSERT ON tb_clientes
        BEGIN
            UPDATE tb_clientes 
            SET status_cliente = CASE 
                WHEN NEW.data_desativacao IS NOT NULL THEN 'Cancelado'
                ELSE 'Ativo'
            END
            WHERE cliente_id = NEW.cliente_id;
        END;
                             
        CREATE TRIGGER IF NOT EXISTS tr_sincronizar_status_update
        AFTER UPDATE OF data_desativacao ON tb_clientes
        BEGIN
            UPDATE tb_clientes 
            SET status_cliente = CASE 
                WHEN NEW.data_desativacao IS NOT NULL THEN 'Cancelado'
                ELSE 'Ativo'
            END
            WHERE cliente_id = NEW.cliente_id;
        END;
    """)
    print("   ✔️  Automação: Triggers de sincronização de status ativos.")
    # 3. CAMADA ANALÍTICA (Views para Join e Agregações)
    cursor.executescript("""
        -- View 1: Join Detalhado (O Planilhao Base)
        DROP VIEW IF EXISTS vw_faturamento_consolidado;
        CREATE VIEW vw_faturamento_consolidado AS
        SELECT 
            c.nome_cliente, c.email, c.cidade, c.estado, c.status_cliente,
            f.valor_cobranca, f.data_vencimento, f.status_cobranca, 
            f.tipo_cobranca, f.forma_pagamento, f.data_pagamento
        FROM tb_cobrancas f
        INNER JOIN tb_clientes c ON f.cliente_id = c.cliente_id;

        -- View 2: Agregacao por Estado (KPI Geografico)
        DROP VIEW IF EXISTS vw_resumo_por_estado;
        CREATE VIEW vw_resumo_por_estado AS
        SELECT 
            estado,
            COUNT(*) AS total_cobrancas,
            ROUND(SUM(valor_cobranca), 2) AS faturamento_total,
            ROUND(AVG(valor_cobranca), 2) AS ticket_medio
        FROM vw_faturamento_consolidado
        GROUP BY estado
        ORDER BY faturamento_total DESC;

        -- View 3: Inadimplencia (Filtros e Calculo de Datas)
        DROP VIEW IF EXISTS vw_clientes_inadimplentes;
        CREATE VIEW vw_clientes_inadimplentes AS
        SELECT 
            nome_cliente,
            email,
            valor_cobranca,
            data_vencimento,
            -- julianday calcula a diferenca real em dias entre hoje e o vencimento
            CAST(julianday('now') - julianday(data_vencimento) AS INTEGER) AS dias_atraso
        FROM vw_faturamento_consolidado
        WHERE status_cobranca = 'Atrasada' 
          AND data_vencimento < date('now');

        -- View 4: Analise de Churn (Agregacao de Status)
        DROP VIEW IF EXISTS vw_analise_churn;
        CREATE VIEW vw_analise_churn AS
        SELECT 
            status_cliente,
            COUNT(DISTINCT nome_cliente) AS qtd_clientes,
            ROUND(SUM(valor_cobranca), 2) AS faturamento_gerado
        FROM vw_faturamento_consolidado
        GROUP BY status_cliente;
                         
        
        -- View 5: Regra de Alerta (Negócio) - Parte 3
        DROP VIEW IF EXISTS vw_alerta_inadimplencia_critica;
        CREATE VIEW vw_alerta_inadimplencia_critica AS
        WITH UltimasCobrancas AS (
            SELECT 
                cliente_id,
                status_cobranca,
                data_vencimento,
                data_pagamento,
                -- Cria um ranking das cobranças da mais nova para a mais antiga
                ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY data_vencimento DESC) as rnk
            FROM tb_cobrancas
        ),
        DevedoresTresMeses AS (
            SELECT 
                cliente_id,
                MIN(data_vencimento) as data_primeira_aberto,
                MAX(data_vencimento) as data_ultima_aberto
            FROM UltimasCobrancas
            WHERE rnk <= 3 -- Olhamos apenas as 3 mais recentes
            GROUP BY cliente_id
            -- Só entra no alerta se TODAS as 3 últimas estiverem devendo
            HAVING SUM(CASE WHEN status_cobranca IN ('Atrasada', 'Em Aberto') THEN 1 ELSE 0 END) = 3
        ),
        UltimoPagamento AS (
            SELECT 
                cliente_id, 
                MAX(data_pagamento) as data_ultima_paga
            FROM tb_cobrancas
            WHERE status_cobranca = 'Paga'
            GROUP BY cliente_id
        )
        SELECT 
            c.nome_cliente,
            u.data_ultima_paga,
            d.data_primeira_aberto,
            d.data_ultima_aberto
        FROM DevedoresTresMeses d
        JOIN tb_clientes c ON d.cliente_id = c.cliente_id
        LEFT JOIN UltimoPagamento u ON d.cliente_id = u.cliente_id;
    """)
    
    print("   ✔️  Analytics: 5 Views de inteligência de negócio integradas (incluindo Regra de Alerta).")
