import os
import pandas as pd
from src.extract.loaders import extract_clients, load_config
from src.transform.transform_clients import (
    limpar_nomes_clientes, 
    padronizar_emails, 
    limpar_status_cliente, 
    tratar_datas_especificas,
    limpar_localidade,
    anular_ids_duplicados,
    aplicar_regras_negocio_status
)

def test_pipeline():
    raw_file = "data/raw/clientes.xlsx"
    file_basename = os.path.splitext(os.path.basename(raw_file))[0]
    output_filename = f"teste_{file_basename}.csv"
    output_dir = 'tests_output'
    
    print(f"🚀 Iniciando teste de auditoria para: {os.path.basename(raw_file)}")
    
    try:
        # 1. EXTRACT
        df = extract_clients(raw_file)
        config = load_config()
        cols_data = config.get(file_basename, {}).get('colunas_data', [])
        print(f"✅ Carga inicial: {len(df)} linhas.")

        # 2. BACKUP PARA AUDITORIA (Lado a Lado)
        # Automatizado: cria cópia de todas as colunas originais antes da transformação
        for col in df.columns:
            df[f'{col}_original'] = df[col].copy()

        # 3. TRANSFORM
        # Aqui as funções atuam nas colunas principais, mantendo as _original intactas
        df = (df.pipe(limpar_nomes_clientes)
                .pipe(padronizar_emails)
                .pipe(limpar_status_cliente)
                .pipe(tratar_datas_especificas, colunas_data=cols_data)
                .pipe(aplicar_regras_negocio_status)
                .pipe(limpar_localidade)
                .pipe(anular_ids_duplicados))

        # 4. EXPORT SETUP
        os.makedirs(output_dir, exist_ok=True) 
        output_path = os.path.join(output_dir, output_filename)
        
        # 5. ORDENAÇÃO LADO A LADO (Padrão: Coluna Limpa | Coluna Original)
        # Filtramos as colunas base (sem o sufixo _original)
        colunas_limpas = [c for c in df.columns if not c.endswith('_original')]
        
        # Criamos a lista final intercalada
        colunas_finais = []
        for col in colunas_limpas:
            colunas_finais.append(col)
            if f"{col}_original" in df.columns:
                colunas_finais.append(f"{col}_original")
        
        df_final = df[colunas_finais]

        # 6. SALVAMENTO
        df_final.to_csv(output_path, sep=';', encoding='utf-8-sig', index=False)
        print(f"✅ Relatório de auditoria gerado: {output_path}")
        print("💡 Dica: Abra o CSV e compare as colunas 'limpas' com as 'originais' vizinhas.")

    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")

if __name__ == "__main__":
    test_pipeline()