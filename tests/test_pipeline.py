import os
from src.extract.loaders import extract_clients, load_config # Centralizei os imports
from src.transform.transform import (
    limpar_nomes_clientes, 
    padronizar_emails, 
    limpar_status_cliente, 
    tratar_datas_especificas
)

def test_pipeline():
    print("🚀 Starting test for clientes.xlsx...")
    raw_file = "data/raw/clientes.xlsx"
    
    try:
        # 1. Extract & Config
        df = extract_clients(raw_file)
        config = load_config() # Carrega o YAML aqui dinamicamente (Caso haja mudança no YAML, o código se adapta sozinho)
        cols_data = config.get('clientes', {}).get('colunas_data', [])
        print(f"✅ Successfully loaded {len(df)} rows.")

        # 2. Criar colunas de comparação (Audit Trail)
        for col in cols_data:
            if col in df.columns:
                df[f'{col}_original'] = df[col]
        
        # 3. Transform
        df = limpar_nomes_clientes(df)
        df = padronizar_emails(df)
        df = limpar_status_cliente(df)
        df = tratar_datas_especificas(df, cols_data)

        # 4. Configuração da pasta de saída
        output_dir = 'tests_output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, 'teste_final.csv')
        
        # 5. Export
        df.to_csv(output_path, sep=';', encoding='utf-8-sig', index=False)
        print(f"✅ Arquivo gerado em: {output_path}")
        print(f"📅 Colunas de data tratadas: {cols_data}")

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")

if __name__ == "__main__":
    test_pipeline()