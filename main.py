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
              .pipe(remover_duplicados_id))

def pipeline_transform_billings(df, cols_data):
    """Encadeamento de transformações para Cobranças."""
    return (df.pipe(tratar_datas_especificas, colunas_data=cols_data)
              .pipe(limpar_valor_monetario)
              .pipe(normalizar_status_cobranca)
              .pipe(normalizar_tipo_cobranca)
              .pipe(limpar_forma_pagamento))

def generate_business_alerts(conn, output_dir):
    """
    Parte 3: Implementa a regra de alerta de negócio (3 meses sem pagar).
    Exporta para Excel simulando o envio para uma API.
    """
    print("\n" + "-"*40)
    print("🔔 PROCESSANDO REGRAS DE ALERTA")
    print("-"*40)
    
    try:
        # A View vw_alerta_inadimplencia_critica deve estar no seu schema.py
        df_alerta = pd.read_sql("SELECT * FROM vw_alerta_inadimplencia_critica", conn)
        
        if not df_alerta.empty:
            # Garante que a pasta data/alerts existe
            os.makedirs(output_dir, exist_ok=True)
            alert_path = os.path.join(output_dir, "alerta_inadimplencia_critica.xlsx").replace("\\", "/")
            df_alerta.to_excel(alert_path, index=False)

            
            print(f"   🚀 AÇÃO: Arquivo 'alerta_inadimplencia_critica.xlsx' gerado para simulação de envio.")
        else:
            print("   ℹ️  STATUS: Nenhum cliente cumpre o critério de 3 meses de inadimplência consecutiva.")
            
    except Exception as e:
        print(f"   ❌ Erro ao gerar alerta da Parte 3: {e}")

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
    
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode = DELETE;")
            create_schema(conn.cursor())

            # --- PROCESSAMENTO DE DADOS (CAMADA SILVER) ---
            print("\n" + "-"*40)
            print("⚙️  PROCESSAMENTO: CAMADA SILVER")
            print("-"*40)
            print("\n👥 Processando Clientes...")
            df_cli = extract_data("data/raw/clientes.xlsx", schema_key='clientes')
            df_cli_clean = pipeline_transform_clientes(df_cli, load_config()['clientes']['colunas_data'])
            df_cli_clean.to_sql('tb_clientes', conn, if_exists='append', index=False)
            print(f"   ✔️  {len(df_cli_clean):,} registros importados com sucesso.")

            print("\n💰 Processando Cobranças...")
            df_cob = extract_data("data/raw/cobrancas.csv", schema_key='cobrancas')
            df_cob_clean = pipeline_transform_billings(df_cob, load_config()['cobrancas']['colunas_data'])
            
            # Integridade
            total_raw = len(df_cob_clean)
            df_cob_clean = df_cob_clean[df_cob_clean['cliente_id'].isin(df_cli_clean['cliente_id'])]
            removidos = total_raw - len(df_cob_clean)
            
            df_cob_clean.to_sql('tb_cobrancas', conn, if_exists='append', index=False, chunksize=5000)
            print(f"   ✔️  {len(df_cob_clean):,} registros processados.")
            if removidos > 0:      
                print(f"   ⚠️  INTEGRIDADE: {removidos} cobranças descartadas por não possuírem um Cliente correspondente (ID órfão).")
                print(f"      Isso garante que o faturamento no Power BI seja 100% auditável.")

            # --- CAMADA ANALÍTICA (GOLD) ---
            print("\n" + "-"*40)
            print("📊 GERANDO CAMADA ANALÍTICA (GOLD)")
            print("-"*40)
            
            estudo_geo = pd.read_sql("SELECT * FROM vw_resumo_por_estado", conn)
            estudo_inadimplencia = pd.read_sql("SELECT * FROM vw_clientes_inadimplentes", conn)
            estudo_churn = pd.read_sql("SELECT * FROM vw_analise_churn", conn)
            base_consolidada = pd.read_sql("SELECT * FROM vw_faturamento_consolidado", conn)
            
            total_clientes = estudo_churn['qtd_clientes'].sum()
            print(f"   ✔️  KPIs Geográficos: {len(estudo_geo)} estados.")
            print(f"   ✔️  Inadimplência: {len(estudo_inadimplencia):,} registros detectados.")
            print(f"   ✔️  Churn: {len(estudo_churn)} categorias analisadas para {total_clientes:,.0f} clientes.")

            conn.commit()

            generate_business_alerts(conn, ALERTS_DIR)

        # --- ESTÁGIO 4: EXPORTAÇÃO ---
        print("\n" + "-"*40)
        print("💾 EXPORTANDO ARTEFATOS FINAIS")
        print("-"*40)

        # Mapeamento para exportação organizada
        silver_layers = {
            "clientes": df_cli_clean, 
            "cobrancas": df_cob_clean, 
            "base_consolidada": base_consolidada
        }
        
        gold_layers = {
            "estudo_geografico": estudo_geo, 
            "estudo_inadimplencia": estudo_inadimplencia, 
            "estudo_churn": estudo_churn
        }

        # Salvando Camada Silver (data/processed)
        for name, df in silver_layers.items():
            df.to_parquet(os.path.join(PROCESSED_DIR, f"{name}.parquet"), index=False)
            df.to_csv(os.path.join(PROCESSED_DIR, f"{name}.csv"), sep=';', encoding='utf-8-sig', index=False)
            print(f"   💾 [Silver] Base '{name}' pronta.")

        # Salvando Camada Gold (data/processed/analytics)
        for name, df in gold_layers.items():
            df.to_parquet(os.path.join(ANALYTICS_DIR, f"{name}.parquet"), index=False)
            df.to_csv(os.path.join(ANALYTICS_DIR, f"{name}.csv"), sep=';', encoding='utf-8-sig', index=False)
            print(f"   📈 [Gold]   Estudo '{name}' publicado.")

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