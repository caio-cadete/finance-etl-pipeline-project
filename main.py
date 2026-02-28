import os
import sqlite3
import pandas as pd
from src.extract.loaders import extract_data, load_config
from src.database.schema import create_schema
from src.transform.transform_clients import (
    limpar_nomes_clientes, 
    padronizar_emails, 
    limpar_status_cliente, 
    limpar_localidade,
    remover_duplicados_id,
    aplicar_regras_negocio_status
)
from src.transform.transform_data import tratar_datas_especificas
from src.transform.transform_billings import (
    limpar_valor_monetario, normalizar_status_cobranca,
    normalizar_tipo_cobranca, limpar_forma_pagamento
)


# Configurações de Caminho (Facilita manutenção futura)
RAW_FILE = "data/raw/clientes.xlsx"
DB_PATH = "data/database/etl_local.db"
PROCESSED_DIR = "data/processed"

def pipeline_transform_clientes(df, cols_data):
    """Agrupa todas as transformações de clientes em um único fluxo."""
    return (df.pipe(limpar_nomes_clientes)
              .pipe(padronizar_emails)
              .pipe(limpar_status_cliente)
              .pipe(tratar_datas_especificas, colunas_data=cols_data)
              .pipe(aplicar_regras_negocio_status)
              .pipe(limpar_localidade)
              .pipe(remover_duplicados_id))

def pipeline_transform_billings(df, cols_data):
    """Encadeamento de transformações para Cobranças."""
    return (df.pipe(tratar_datas_especificas, colunas_data=cols_data)
              .pipe(limpar_valor_monetario)
              .pipe(normalizar_status_cobranca)
              .pipe(normalizar_tipo_cobranca)
              .pipe(limpar_forma_pagamento))

# --- EXECUÇÃO PRINCIPAL ---

def run_full_pipeline():
    print("🚀 Iniciando Pipeline de Produção: Clientes & Cobranças")

    # --- NOVO: GARANTIA DE EXECUÇÃO LIMPA ---
    if os.path.exists(DB_PATH):
        try:
            # Tenta deletar o banco e o journal antes de começar a nova rodada
            os.remove(DB_PATH)
            if os.path.exists(f"{DB_PATH}-journal"):
                os.remove(f"{DB_PATH}-journal")
            print("🧹 Limpeza realizada: Iniciando banco do zero.")
        except PermissionError:
            print("⚠️ Erro: Feche o Power BI antes de rodar o script!")
            return
    # ----------------------------------------
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    config = load_config()

    try:
        # 1. Adicionamos timeout para evitar 'database is locked' se o Power BI estiver lendo
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            # 2. PRAGMA DELETE: Força o arquivo -journal a sumir no commit
            conn.execute("PRAGMA journal_mode = DELETE;")
            
            cursor = conn.cursor()
            create_schema(cursor) # Garante que ambas as tabelas existam

            # --- PARTE 1: CLIENTES ---
            print("\n👥 Processando Clientes...")
            raw_clientes = "data/raw/clientes.xlsx"
            df_cli = extract_data(raw_clientes, schema_key='clientes')
            cols_data_cli = config.get('clientes', {}).get('colunas_data', [])
            df_cli_clean = pipeline_transform_clientes(df_cli, cols_data_cli)
            
            cursor.execute("DELETE FROM tb_clientes")
            df_cli_clean.to_sql('tb_clientes', conn, if_exists='append', index=False)
            print("✅ Clientes persistidos no SQLite.")

            # --- PARTE 2: COBRANÇAS ---
            print("\n💰 Processando Cobranças...")
            raw_cobrancas = "data/raw/cobrancas.csv"
            df_cob = extract_data(raw_cobrancas, schema_key='cobrancas')
            cols_data_cob = config.get('cobrancas', {}).get('colunas_data', [])
            df_cob_clean = pipeline_transform_billings(df_cob, cols_data_cob)

            # 🛡️ FILTRO DE INTEGRIDADE REFERENCIAL
            # Só mantém cobranças cujo cliente_id existe no DataFrame de clientes que acabamos de processar
            clientes_validos = df_cli_clean['cliente_id'].unique()
            df_cob_clean = df_cob_clean[df_cob_clean['cliente_id'].isin(clientes_validos)]
            
            print(f"⚠️ Removidas {len(df_cob) - len(df_cob_clean)} cobranças de clientes inexistentes.")
            
            # Agora sim, fazemos a carga com o chunksize para evitar o erro de variáveis
            try:
                cursor.execute("DELETE FROM tb_cobrancas")
                df_cob_clean.to_sql(
                    'tb_cobrancas', 
                    conn, 
                    if_exists='append', 
                    index=False, 
                    chunksize=5000, 
                )

            # 3. FORÇAR O FECHAMENTO (Commit + Checkpoint)
                # Isso mata o arquivo -journal imediatamente
                conn.commit()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

                print(f"✅ {len(df_cob_clean)} Cobranças válidas persistidas no SQLite.")
            except Exception as sql_e:
                print(f"❌ ERRO ESPECÍFICO DO SQLITE: {sql_e}")
                raise sql_e
            

            
            # --- PARTE 3: EXPORTAÇÃO FINAL ---
            print("\n📂 Exportando arquivos processados para a pasta 'processed'...")
            
            # Exportação de Clientes (Parquet para Power BI e CSV para Auditoria)
            df_cli_clean.to_parquet(os.path.join(PROCESSED_DIR, "clientes.parquet"), index=False)
            df_cli_clean.to_csv(os.path.join(PROCESSED_DIR, "clientes.csv"), sep=';', encoding='utf-8-sig', index=False)
            
            # Exportação de Cobranças (Parquet para Power BI e CSV para Auditoria)
            df_cob_clean.to_parquet(os.path.join(PROCESSED_DIR, "cobrancas.parquet"), index=False)
            df_cob_clean.to_csv(os.path.join(PROCESSED_DIR, "cobrancas.csv"), sep=';', encoding='utf-8-sig', index=False)
            
            print(f"✅ Arquivos gerados em {PROCESSED_DIR}:")

        print("\n🏁 Pipeline completo finalizado com sucesso!")

    except Exception as e:
        print(f"❌ Erro crítico no Pipeline: {e}")
        print("--- DEBUG COLUNAS ---")
        print(f"Colunas no DataFrame: {df_cob_clean.columns.tolist()}")

if __name__ == "__main__":
    run_full_pipeline()

