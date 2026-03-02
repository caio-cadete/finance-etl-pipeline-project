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
    aplicar_regras_negocio_status,
    tratar_segmentacao_clientes
)
from src.transform.transform_date import tratar_datas_especificas
from src.transform.transform_billings import (
    limpar_valor_monetario, normalizar_status_cobranca,
    normalizar_tipo_cobranca, limpar_forma_pagamento
)
from src.load.exporter import salvar_camadas_processadas, generate_business_alerts, load_silver_layer, generate_gold_layer


# --- CONFIGURAÇÕES DE CAMINHO ---
RAW_FILE = "data/raw/clientes.xlsx"
DB_PATH = "data/database/etl_local.db"
PROCESSED_DIR = "data/processed"
ALERTS_DIR = "data/alerts"  
ANALYTICS_DIR = os.path.join(PROCESSED_DIR, "analytics")

def pipeline_transform_clientes(df, cols_data):
    """Agrupa todas as transformações de clientes em um único fluxo."""
    return (df.pipe(limpar_nomes_clientes)
              .pipe(padronizar_emails)
              .pipe(limpar_status_cliente)
              .pipe(tratar_datas_especificas, colunas_data=cols_data)
              .pipe(aplicar_regras_negocio_status)
              .pipe(limpar_localidade)
              .pipe(remover_duplicados_id)
              .pipe(tratar_segmentacao_clientes))

def pipeline_transform_billings(df, cols_data):
    """Encadeamento de transformações para Cobranças."""
    return (df.pipe(tratar_datas_especificas, colunas_data=cols_data)
              .pipe(limpar_valor_monetario)
              .pipe(normalizar_status_cobranca)
              .pipe(normalizar_tipo_cobranca)
              .pipe(limpar_forma_pagamento))

# --- EXECUÇÃO PRINCIPAL ---

def run_pipeline():
    print("\n" + "="*60)
    print("🚀 INICIANDO EXECUÇÃO DO PIPELINE DE PRODUÇÃO")
    print("="*60)

    # --- ESTÁGIO 1: IDEMPOTÊNCIA ---
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            for suffix in ["-journal", "-wal", "-shm"]:
                tmp_file = f"{DB_PATH}{suffix}"
                if os.path.exists(tmp_file): os.remove(tmp_file)
            print("\n✔️  RESET: Ambiente limpo e execuções anteriores removidas.")
        except PermissionError:
            print("\n❌ ERRO: O banco de dados está aberto em outro programa.")
            return

    # Garantia de diretórios
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(ALERTS_DIR, exist_ok=True)
    os.makedirs(ANALYTICS_DIR, exist_ok=True)

    # --- ESTÁGIO 2: SQL SCHEMA ---
    print("\n" + "-"*40)
    print("🗄️  CONFIGURANDO AMBIENTE SQL")
    print("-"*40)

    # 1. Extração e Transformação (Fora do bloco do banco)
    df_cli = extract_data("data/raw/clientes.xlsx", schema_key='clientes')
    df_cli_clean = pipeline_transform_clientes(df_cli, load_config()['clientes']['colunas_data'])

    df_cob = extract_data("data/raw/cobrancas.csv", schema_key='cobrancas')
    df_cob_clean = pipeline_transform_billings(df_cob, load_config()['cobrancas']['colunas_data'])
    
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode = DELETE;")
            create_schema(conn.cursor())

            # --- CAMADA SILVER ---
            df_cob_final = load_silver_layer(conn, df_cli_clean, df_cob_clean)
            # --- CAMADA GOLD ---
            gold_data = generate_gold_layer(conn)

            conn.commit()

            generate_business_alerts(conn, ALERTS_DIR)

        # --- ESTÁGIO 4: EXPORTAÇÃO ---
        print("\n" + "-"*40)
        print("💾 EXPORTANDO ARTEFATOS FINAIS")
        print("-"*40)

        # Mapeamento para exportação organizada
        # Usamos os DataFrames que passaram pela Silver e a consolidada que veio da Gold
        silver_layers = {
            "clientes": df_cli_clean, 
            "cobrancas": df_cob_final, # Usamos o df filtrado pela função de carga
            "base_consolidada": gold_data["base_consolidada"]
        }

        # Mapeamos as tabelas analíticas retornadas no dicionário gold_data
        gold_layers = {
            "estudo_geografico": gold_data["estudo_geo"], 
            "estudo_inadimplencia": gold_data["estudo_inadimplencia"], 
            "estudo_churn": gold_data["estudo_churn"]
        }

        salvar_camadas_processadas(silver_layers, PROCESSED_DIR, gold_layers, ANALYTICS_DIR)
        
    

        print("\n" + "="*60)
        print("✅ PIPELINE CONCLUÍDO COM SUCESSO")
        print(f"📂 Repositório [Silver]: {PROCESSED_DIR}")
        print(f"📂 Repositório [Gold]:   {ANALYTICS_DIR.replace('\\', '/')}")
        print(f"🔔 Central de Alertas:  {ALERTS_DIR.replace('\\', '/')}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ FALHA CRÍTICA: {str(e)}")

if __name__ == "__main__":
    run_pipeline()