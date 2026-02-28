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
    Normaliza colunas de data tratando dois casos críticos: 
    1. Números seriais do Excel (ex: 45259)
    2. Strings de texto (ex: 18/10/2024) via Regex para evitar perdas do pd.to_datetime.
    """
    for col in colunas_data:
        if col in df.columns:
            # --- PASSO 1: Identificação de Números Seriais (Padrão Excel) ---
            # Tenta converter para numérico; o que for string (ex: "18/10") vira NaN (coerce)
            serie_numerica = pd.to_numeric(df[col], errors='coerce')
            mask_serial = serie_numerica.notna()
            
            # Se houver números, converte usando a base de data do Excel (30/12/1899)
            if mask_serial.any():
                df.loc[mask_serial, col] = pd.to_datetime(
                    serie_numerica[mask_serial], unit='D', origin='1899-12-30'
                ).dt.strftime('%Y-%m-%d')

            # --- PASSO 2: Tratamento de Strings via Regex (Determinístico) ---
            def formatar_string_data(val):
                # Limpeza inicial: remove nulos e strings vazias que podem quebrar a lógica
                if pd.isna(val) or str(val).lower() in ['nan', 'none', 'nat', '']:
                    return None
                
                val_str = str(val).strip()
                
                # Procura o padrão brasileiro DD/MM/AAAA. Usamos Regex para garantir
                # que o dado não "suma" se houver lixo (ex: horas 00:00:00) na string.
                match = re.search(r'(\d{2})/(\d{2})/(\d{4})', val_str)
                if match:
                    dia, mes, ano = match.groups()
                    return f"{ano}-{mes}-{dia}" # Inverte para o padrão ISO (YYYY-MM-DD)
                
                # Caso o dado já esteja em formato ISO, apenas limpa espaços extras
                match_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', val_str)
                if match_iso:
                    return match_iso.group(0)
                
                # Se o formato for irreconhecível, retornamos None para manter a integridade
                return None

            # --- PASSO 3: Aplicação seletiva ---
            # Aplicamos a função de string apenas nas linhas que NÃO eram números seriais
            # Isso evita que o Regex tente processar objetos datetime já convertidos no Passo 1
            mask_restante = ~mask_serial
            df.loc[mask_restante, col] = df.loc[mask_restante, col].apply(formatar_string_data)

    return df


def limpar_localidade(df):
    """
    Parte 1: Padroniza Cidades (acentos) e Estados (Siglas em Caixa Alta)
    Parte 2: Corrige inconsistências geográficas (Ex: BH no RJ)
    """
    # --- PADRONIZAÇÃO DE STRINGS ---
    if 'cidade' in df.columns:
        df['cidade'] = df['cidade'].str.normalize('NFKD')\
                                   .str.encode('ascii', errors='ignore')\
                                   .str.decode('utf-8')\
                                   .str.strip().str.title()

    if 'estado' in df.columns:
        df['estado'] = df['estado'].str.normalize('NFKD')\
                                   .str.encode('ascii', errors='ignore')\
                                   .str.decode('utf-8')\
                                   .str.strip().str.upper()
        
        # Mapeia nomes por extenso para siglas
        mapeamento_estados = {
            'SAO PAULO': 'SP',
            'MINAS GERAIS': 'MG',
            'PARANA': 'PR',
            'RIO DE JANEIRO': 'RJ'
        }
        df['estado'] = df['estado'].replace(mapeamento_estados)

    # --- CORREÇÃO DE INCONSISTÊNCIAS (A "Verdade" pela Cidade) ---
    if 'cidade' in df.columns and 'estado' in df.columns:
        # Dicionário que define qual UF cada cidade DEVE pertencer
        correcao_geografica = {
            'Belo Horizonte': 'MG',
            'Sao Paulo': 'SP',
            'Rio De Janeiro': 'RJ',
            'Curitiba': 'PR'
        }

        # Iteramos sobre o dicionário para corrigir estados errados
        for cidade_correta, uf_correta in correcao_geografica.items():
            mask = df['cidade'] == cidade_correta
            df.loc[mask, 'estado'] = uf_correta

    return df

