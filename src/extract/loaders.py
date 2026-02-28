import pandas as pd
import yaml
import os

def load_config():
    """Lê o arquivo de configuração YAML de forma resiliente."""
    # Garante que o caminho funcione independente de onde o script é chamado
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(base_path, "config", "schema.yaml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado em: {config_path}")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_data(file_path, schema_key):
    """
    Extrator genérico que lê Excel ou CSV baseado no schema.yaml.
    """
    config = load_config()
    schema = config.get(schema_key)
    
    if not schema:
        raise ValueError(f"Chave '{schema_key}' não encontrada no schema.yaml")

    ext = os.path.splitext(file_path)[-1].lower()
    
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, sheet_name=schema.get('aba', 'Sheet1'))
        
    elif ext == '.csv':
        # AJUSTE: Pegamos o separador do YAML. Se não existir, o padrão é ';'
        sep_config = schema.get('separador', ';')
        
        # AJUSTE: Usamos 'utf-8-sig' ou 'latin-1' para evitar erros de acentuação (BOM)
        # O 'low_memory=False' evita avisos de tipos mistos em arquivos grandes
        df = pd.read_csv(
            file_path, 
            sep=sep_config, 
            encoding='utf-8-sig', 
            low_memory=False
        )
    else:
        raise TypeError(f"Formato de arquivo {ext} não suportado.")
    
    return df