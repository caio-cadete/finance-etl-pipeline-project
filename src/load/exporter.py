import os
import pandas as pd

def salvar_camadas_processadas(silver_layers, processed_dir, gold_layers, analytics_dir):
    """
    Exporta as camadas Silver e Gold para Parquet (técnico) e CSV (humano/BR).
    """
    # Salvando Camada Silver
    for name, df in silver_layers.items():
        df.to_parquet(os.path.join(processed_dir, f"{name}.parquet"), index=False)
        df.to_csv(os.path.join(processed_dir, f"{name}.csv"), sep=';', encoding='utf-8-sig', decimal=',', index=False)
        print(f"    💾 [Silver] Base '{name}' pronta.")

    # Salvando Camada Gold
    for name, df in gold_layers.items():
        df.to_parquet(os.path.join(analytics_dir, f"{name}.parquet"), index=False)
        df.to_csv(os.path.join(analytics_dir, f"{name}.csv"), sep=';', encoding='utf-8-sig', decimal=',', index=False)
        print(f"    📈 [Gold]   Estudo '{name}' publicado.")

def generate_business_alerts(conn, output_dir):
    """
    Parte 3: Implementa a regra de alerta de negócio (3 meses sem pagar).
    O log agora identifica qual alerta está sendo processado.
    """
    nome_alerta = "Inadimplência Crítica" # Identificador do alerta
    
    print("\n" + "-"*40)
    print(f"🔔 PROCESSANDO REGRAS DE ALERTA")
    print("-"*40)
    
    try:
        df_alerta = pd.read_sql("SELECT * FROM vw_alerta_inadimplencia_critica", conn)
        
        if not df_alerta.empty:
            qtd_encontrada = len(df_alerta)
            
            os.makedirs(output_dir, exist_ok=True)
            df_alerta.to_csv(os.path.join(output_dir, "alerta_inadimplencia_critica.csv"), sep=';', encoding='utf-8-sig', decimal=',', index=False)
            
            print(f"    🔍 REGRA: Clientes com 3 meses consecutivos de inadimplência.")
            print(f"    📊 {qtd_encontrada} clientes encontrados no alerta de {nome_alerta}.")
            print(f"    🚀 AÇÃO: Arquivo 'alerta_inadimplencia_critica.xlsx' gerado para simulação de envio via POST.")
        else:
            print(f"   ℹ️  STATUS: Nenhum cliente para o alerta de {nome_alerta}.")
            
    except Exception as e:
        print(f"   ❌ Erro ao gerar alerta {nome_alerta}: {e}")



def load_silver_layer(conn, df_cli_clean, df_cob_clean):
    """
    Parte 2: Processamento e Carga da Camada Silver no SQLite.
    Mantém a regra de integridade para garantir faturamento auditável.
    """
    print("\n" + "-"*40)
    print("⚙️  PROCESSAMENTO: CAMADA SILVER")
    print("-"*40)

    # --- Processando Clientes ---
    print("\n👥 Processando Clientes...")
    df_cli_clean.to_sql('tb_clientes', conn, if_exists='append', index=False)
    print(f"   ✔️  {len(df_cli_clean):,} registros importados com sucesso.")

    # --- Processando Cobranças ---
    print("\n💰 Processando Cobranças...")
    
    # Integridade: Remove IDs órfãos
    total_raw = len(df_cob_clean)
    df_cob_clean_filtered = df_cob_clean[df_cob_clean['cliente_id'].isin(df_cli_clean['cliente_id'])]
    removidos = total_raw - len(df_cob_clean_filtered)
    
    df_cob_clean_filtered.to_sql('tb_cobrancas', conn, if_exists='append', index=False, chunksize=5000)
    print(f"   ✔️  {len(df_cob_clean_filtered):,} registros processados.")
    
    if removidos > 0:      
        print(f"   ⚠️  INTEGRIDADE: {removidos} cobranças descartadas por não possuírem um Cliente correspondente (ID órfão).")
        print(f"      Isso garante que o faturamento no Power BI seja 100% auditável.")
    
    return df_cob_clean_filtered

def generate_gold_layer(conn):
    """
    Parte 3: Extração das Views SQL para a Camada Analítica (Gold).
    Gera os DataFrames que alimentam o Power BI e arquivos externos.
    """
    print("\n" + "-"*40)
    print("📊 GERANDO CAMADA ANALÍTICA (GOLD)")
    print("-"*40)
    
    gold_layers = {
        "estudo_geo": pd.read_sql("SELECT * FROM vw_resumo_por_estado", conn),
        "estudo_inadimplencia": pd.read_sql("SELECT * FROM vw_clientes_inadimplentes", conn),
        "estudo_churn": pd.read_sql("SELECT * FROM vw_analise_churn", conn),
        "base_consolidada": pd.read_sql("SELECT * FROM vw_faturamento_consolidado", conn)
    }
    
    total_clientes = gold_layers['estudo_churn']['qtd_clientes'].sum()
    print(f"   ✔️  KPIs Geográficos: {len(gold_layers['estudo_geo'])} estados.")
    print(f"   ✔️  Inadimplência: {len(gold_layers['estudo_inadimplencia']):,} registros detectados.")
    print(f"   ✔️  Churn: {len(gold_layers['estudo_churn'])} categorias analisadas para {total_clientes:,.0f} clientes.")
    
    return gold_layers