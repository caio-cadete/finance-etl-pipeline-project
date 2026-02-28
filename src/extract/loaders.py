import pandas as pd
import yaml
import os

def load_config():
    """Reads the YAML configuration file"""
    # Usando caminhos relativos para funcionar em qualquer máquina
    config_path = os.path.join("config", "schema.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_clients(file_path):
    """
    Reads the Clients Excel file using rules from schema.yaml
    """
    config = load_config()
    # Verifica se a chave 'clientes' existe no seu yaml
    schema = config.get('clientes')
    
    if not schema:
        raise ValueError("Key 'clientes' not found in schema.yaml")

    # Lê o Excel usando a aba definida no YAML
    df = pd.read_excel(file_path, sheet_name=schema.get('aba', 'Sheet1'))
    
    return df