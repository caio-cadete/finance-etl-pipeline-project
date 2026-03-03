import pandas as pd


def limpar_nomes_clientes(df):
    """
    Padroniza a coluna 'nome_cliente' removendo sufixos jurídicos e excesso de espaços.
    A alteração é feita diretamente na coluna original para manter o padrão de auditoria.
    """
    if 'nome_cliente' in df.columns:
        padroes = r'\b(LTDA|LTDA\.|LIMITADA|S\.A|S/A)\b'
        
        # Operação encadeada direta na coluna
        df['nome_cliente'] = (
            df['nome_cliente']
            .str.upper()
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
    if all(col in df.columns for col in ['cliente_id', 'nome_cliente']):
        # 1. Criamos o "slug" do nome (ex: "Beta Tech" -> "betatech")
        # Aproveitamos o nome_cliente que já limpamos antes (sem o LTDA)
        nome_slug = (
            df['nome_cliente']
            .str.lower()
            .str.replace(r'\s+', '', regex=True) # Remove espaços
            .str.normalize('NFKD')               # Remove acentos
            .str.encode('ascii', errors='ignore')
            .str.decode('utf-8')
        )

        # 2. Reconstrói o e-mail para garantir 100% de consistência
        df['email'] = "contato" + df['cliente_id'].astype(str) + "@" + nome_slug + ".com"
        
    return df

def limpar_status_cliente(df):
    """
    Parte 1: Padroniza status (Ativo, ATIVO, cancelado -> Ativo, Cancelado)
    """
    if 'status_cliente' in df.columns:
        df['status_cliente'] = df['status_cliente'].str.strip().str.capitalize()
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

def remover_duplicados_id(df):
    """
    Remove registros duplicados baseados na coluna 'cliente_id'.
    Mantém o último registro (keep='last') pois geralmente contém a 
    informação mais recente ou a data de desativação preenchida.
    """
    if 'cliente_id' in df.columns:
        # Remove duplicados mantendo a primeira ocorrência
        df = df.drop_duplicates(subset=['cliente_id'], keep='last')
            
    return df

def anular_ids_duplicados(df):
    """
    Versão para TESTE: Não remove a linha, apenas anula o campo 'cliente_id'
    se ele for repetido, permitindo a auditoria visual no CSV de saída.
    """
    if 'cliente_id' in df.columns:
        # Usamos 'Int64' (com I maiúsculo) para aceitar o <NA> sem virar float (1.0)
        df['cliente_id'] = pd.to_numeric(df['cliente_id'], errors='coerce').astype('Int64')
        
        mask_duplicado = df['cliente_id'].duplicated(keep='first')
        df.loc[mask_duplicado, 'cliente_id'] = pd.NA
        
    return df

def aplicar_regras_negocio_status(df):
    """
    Sincroniza o status do cliente com base na presença de uma data de desativação.
    
    Esta função atua como uma camada de 'Data Quality' para garantir que não existam 
    inconsistências lógicas (ex: cliente Ativo com data de saída ou vice-versa).
    """
    
    if 'data_desativacao' in df.columns and 'status_cliente' in df.columns:
        
        # Identifica registros que possuem data de encerramento (Not Null)
        tem_data = df['data_desativacao'].notna()
        
        # REGRA 1: Existência de data de desativação implica obrigatoriamente em status 'Cancelado'.
        # Isso sobrescreve qualquer erro de preenchimento manual vindo da origem (Excel).
        df.loc[tem_data, 'status_cliente'] = 'Cancelado'
        
        # REGRA 2: Ausência de data (Null/NaN) define o cliente como 'Ativo'.
        # Garante que o status 'Cancelado' não exista sem uma data de referência para o Churn.
        df.loc[~tem_data, 'status_cliente'] = 'Ativo'
        
    return df

def tratar_segmentacao_clientes(df):
    """
    1. Transforma o conteúdo original (os 10 nomes) em 'grupo_economico'.
    2. Cria uma nova coluna 'nome_cliente' com IDs únicos (4.000 registros).
    """
    # ESTA É A LINHA MÁGICA: Transforma o df em uma cópia real e independente
    df = df.copy() 
    
    # Criamos uma cópia do conteúdo original para a nova coluna de Grupo
    # Usamos .loc para dizer explicitamente onde gravar os dados
    if 'nome_cliente' in df.columns:
        df.loc[:, 'grupo_economico'] = df['nome_cliente']
    
    # Agora sobrescrevemos a 'nome_cliente' com a identidade única por ID
    if 'cliente_id' in df.columns:
        df.loc[:, 'nome_cliente'] = 'Cliente ' + df['cliente_id'].astype(str)
        
    return df

def corrigir_datas_futuras(df):
    if 'data_desativacao' in df.columns:
        # 1. Converte e já anula o que for erro (ano 4748) ou futuro
        # Usamos o 'coerce' para não travar o código
        datas = pd.to_datetime(df['data_desativacao'], errors='coerce')
        
        # 2. Define o limite (Hoje)
        hoje = pd.Timestamp.now()
        
        # 3. Se a data for maior que hoje, vira nulo (NaT)
        df.loc[datas > hoje, 'data_desativacao'] = pd.NA
        
        # 4. Remove o horário transformando em String (YYYY-MM-DD)
        # O .dt.date é o jeito mais simples de sumir com o 00:00:00
        df['data_desativacao'] = pd.to_datetime(df['data_desativacao']).dt.date
            
    return df