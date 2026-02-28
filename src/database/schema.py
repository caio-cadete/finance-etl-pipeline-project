def create_schema(cursor):
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
            
            -- 1. CHECK CONSTRAINT: Garante a coerência mútua
            CHECK (
                (data_desativacao IS NOT NULL AND status_cliente = 'Cancelado') OR 
                (data_desativacao IS NULL AND status_cliente = 'Ativo')
            )
        );

        -- 2. TRIGGER DE INSERÇÃO: Ajusta o status no momento do INSERT
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

        -- 3. TRIGGER DE ATUALIZAÇÃO: Garante que se a data mudar depois, o status mude junto
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