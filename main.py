import os
import sqlite3
import pandas as pd
from src.extract.loaders import extract_clients, load_config
from src.database.schema import create_schema
from src.transform.transform_clients import (
    limpar_nomes_clientes, 
    padronizar_emails, 
    limpar_status_cliente, 
    tratar_datas_especificas,
    limpar_localidade,
    remover_duplicados_id,
    aplicar_regras_negocio_status
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

def run_pipeline():
    print("🚀 Iniciando Pipeline de Produção: Clientes")
    
    try:
        # 1. EXTRACT
        df = extract_clients(RAW_FILE)
        config = load_config()
        file_basename = os.path.splitext(os.path.basename(RAW_FILE))[0]
        cols_data = config.get(file_basename, {}).get('colunas_data', [])

        # 2. TRANSFORM
        # Usando o encadeamento para manter o main limpo
        df = pipeline_transform_clientes(df, cols_data)

        # 3. LOAD & DATABASE SETUP
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # 'with' garante que a conexão feche sozinha no final do bloco
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            create_schema(cursor)
            
            # Limpeza e Carga
            cursor.execute("DELETE FROM tb_clientes")
            df.to_sql('tb_clientes', conn, if_exists='append', index=False)
            print("✅ Dados persistidos no SQLite (Integridade Validada)")

            # 4. SINCRONIZAÇÃO (Read-back)
            df_processado = pd.read_sql("SELECT * FROM tb_clientes", conn)

        # 5. EXPORTAÇÃO
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        
        # Dica: use f-strings para caminhos dinâmicos
        df_processado.to_csv(os.path.join(PROCESSED_DIR, "clientes.csv"), sep=';', encoding='utf-8-sig', index=False)
        df_processado.to_parquet(os.path.join(PROCESSED_DIR, "clientes.parquet"), index=False)

        print(f"📂 Arquivos exportados para {PROCESSED_DIR}")
        print("🏁 Pipeline de Clientes finalizado com sucesso!")

    except Exception as e:
        print(f"❌ Erro crítico no Pipeline: {e}")
        # Debug simplificado
        if 'df' in locals():
            print(f"\n--- 🔍 DEBUG: Colunas: {df.columns.tolist()} | Status: {df['status_cliente'].unique() if 'status_cliente' in df.columns else 'N/A'}")

if __name__ == "__main__":
    run_pipeline()