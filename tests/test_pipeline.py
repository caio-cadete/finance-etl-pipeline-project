import os
from src.extract.loaders import extract_clients, load_config # Centralizei os imports
from src.transform.transform import (
    limpar_nomes_clientes, 
    padronizar_emails, 
    limpar_status_cliente, 
    tratar_datas_especificas,
    limpar_localidade
)

def test_pipeline():
    print("🚀 Starting test for clientes.xlsx...")
    raw_file = "data/raw/clientes.xlsx"
    
    try:
        # 1. Extract & Config
        df = extract_clients(raw_file)
        config = load_config()
        cols_data = config.get('clientes', {}).get('colunas_data', [])
        print(f"✅ Successfully loaded {len(df)} rows.")

        # 2. Criar Trilhas de Auditoria (Backup das colunas que serão tratadas)
        # Além das datas, vamos salvar nomes, status e localidade
        cols_para_auditar = cols_data + ['nome_cliente', 'status_cliente', 'cidade', 'estado']
        
        for col in cols_para_auditar:
            if col in df.columns:
                df[f'{col}_original'] = df[col] # Cria o backup antes da transformação

        # 3. Transform (Agora as funções vão alterar as colunas principais)
        df = limpar_nomes_clientes(df)
        df = padronizar_emails(df)
        df = limpar_status_cliente(df)
        df = tratar_datas_especificas(df, cols_data)
        df = limpar_localidade(df)

        # 4. Configuração da pasta de saída
        output_dir = 'tests_output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, 'teste_final.csv')
        
        # 5. Export
        # Reordenamos as colunas para que original e tratada fiquem juntas no CSV
        # Isso facilita muito o "olhômetro" no Excel
        cols_ordenadas = sorted(df.columns)
        df = df[cols_ordenadas]

        df.to_csv(output_path, sep=';', encoding='utf-8-sig', index=False)
        print(f"✅ Arquivo gerado em: {output_path}")
        print(f"📅 Colunas auditadas com sucesso!")

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")

if __name__ == "__main__":
    test_pipeline()