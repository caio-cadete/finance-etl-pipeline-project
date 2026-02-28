import pandas as pd
import re


def limpar_nomes_clientes(df):
    """
    Parte 1: Resolve duplicidade de nomes (Ex: Acme vs Acme LTDA)
    """
    if 'nome_cliente' in df.columns:
        # Tudo para maiúsculo para comparação justa
        df['nome_cliente_padrao'] = df['nome_cliente'].str.upper()

        # Regex para remover sufixos jurídicos e termos redundantes
        padroes = r'\b(LTDA|LTDA\.|LIMITADA|S\.A|S/A)\b'
        
        df['nome_cliente_padrao'] = (
            df['nome_cliente_padrao']
            .str.replace(padroes, '', regex=True)
            .str.replace(r'\s+', ' ', regex=True)
            .str.strip()
        )
    return df

def padronizar_emails(df):
    """
    Garante que o e-mail siga a regra: contato{id}@{nome_limpo}.com
    Remove espaços, caracteres especiais e coloca em minúsculo.
    """
    if all(col in df.columns for col in ['cliente_id', 'nome_cliente_padrao']):
        # 1. Criamos o "slug" do nome (ex: "Beta Tech" -> "betatech")
        # Aproveitamos o nome_cliente_padrao que já limpamos antes (sem o LTDA)
        nome_slug = (
            df['nome_cliente_padrao']
            .str.lower()
            .str.replace(r'\s+', '', regex=True) # Remove espaços
            .str.normalize('NFKD')               # Remove acentos
            .str.encode('ascii', errors='ignore')
            .str.decode('utf-8')
        )

        # 2. Reconstrói o e-mail para garantir 100% de consistência
        df['email_padrao'] = "contato" + df['cliente_id'].astype(str) + "@" + nome_slug + ".com"
        
    return df

def limpar_status_cliente(df):
    """
    Parte 1: Padroniza status (Ativo, ATIVO, cancelado -> Ativo, Cancelado)
    """
    if 'status_cliente' in df.columns:
        df['status_cliente'] = df['status_cliente'].str.strip().str.capitalize()
    return df

def tratar_datas_especificas(df, colunas_data):
    """
    Parte 1: Resolve o desafio dos 5 formatos de data e o Serial Date do Excel (45259)
    """
    for col in colunas_data:
        if col in df.columns:
            # 1. Trata números tipo 45259 (Excel Date Serial)
            is_numeric = pd.to_numeric(df[col], errors='coerce')
            mask_numeric = is_numeric.notna()
            
            df.loc[mask_numeric, col] = pd.to_datetime(
                is_numeric[mask_numeric], unit='D', origin='1899-12-30'
            )
            
            # 2. Converte strings (DD/MM/AAAA, ISO, etc)
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            
    return df

def limpar_localidade(df):
    """
    Parte 1: Padroniza Cidades (acentos) e Estados (Siglas em Caixa Alta)
    """
    # Cidades: Remove acentos e padroniza para Capitalize
    if 'cidade' in df.columns:
        df['cidade'] = df['cidade'].str.normalize('NFKD')\
                                   .str.encode('ascii', errors='ignore')\
                                   .str.decode('utf-8')\
                                   .str.strip().str.title()

    # Estados: Converte nomes longos para siglas e coloca em CAIXA ALTA para facilitar JOIN com banco de dados
    if 'estado' in df.columns:
        # Primeiro limpa acentos e coloca em Upper para o mapeamento funcionar
        df['estado'] = df['estado'].str.normalize('NFKD')\
                                   .str.encode('ascii', errors='ignore')\
                                   .str.decode('utf-8')\
                                   .str.strip().str.upper()
        
        mapeamento_estados = {
            'SAO PAULO': 'SP',
            'MINAS GERAIS': 'MG',
            'PARANA': 'PR',
            'RIO DE JANEIRO': 'RJ'
        }
        df['estado'] = df['estado'].replace(mapeamento_estados)
        
    return df

