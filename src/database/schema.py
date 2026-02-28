def create_schema(cursor):
    # ATENÇÃO: Ativa o suporte a Foreign Keys no SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
        -- 1. TABELA DE CLIENTES
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

        -- 2. TABELA DE COBRANÇAS
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

        -- 3. TRIGGERS (Sincronização de Status)
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

        DROP VIEW IF EXISTS vw_faturamento_consolidado;
        CREATE VIEW vw_faturamento_consolidado AS
        SELECT 
            c.nome_cliente,
            c.email,
            c.cidade,
            c.estado,
            c.status_cliente,
            f.valor_cobranca,
            f.data_vencimento,
            f.status_cobranca,
            f.tipo_cobranca,
            f.forma_pagamento,
            f.data_pagamento
        FROM tb_cobrancas f
        INNER JOIN tb_clientes c ON f.cliente_id = c.cliente_id;
    """)
    
    print("🗄️ Schema atualizado: Tabelas, Triggers e View Analítica criadas.")