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
            alert_path = os.path.join(output_dir, "alerta_inadimplencia_critica.xlsx").replace("\\", "/")
            df_alerta.to_excel(alert_path, index=False)
            
            print(f"    🔍 REGRA: Clientes com 3 meses consecutivos de inadimplência.")
            print(f"    📊 {qtd_encontrada} clientes encontrados no alerta de {nome_alerta}.")
            print(f"    🚀 AÇÃO: Arquivo 'alerta_inadimplencia_critica.xlsx' gerado para simulação de envio via POST.")
        else:
            print(f"   ℹ️  STATUS: Nenhum cliente para o alerta de {nome_alerta}.")
            
    except Exception as e:
        print(f"   ❌ Erro ao gerar alerta {nome_alerta}: {e}")