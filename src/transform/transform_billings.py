import pandas as pd
import re

def limpar_valor_monetario(df, col_valor='valor_cobranca'):
    """
    Transforma strings sujas (52,93 ou 55.43) em float64 com 2 casas decimais.
    """
    df = df.copy()
    
    def converter(x):
        if pd.isna(x) or x == '': return 0.0
        # Converte para string e remove espaços
        s = str(x).strip()
        # Se tiver vírgula e ponto (ex: 1.250,50), remove o ponto e troca a vírgula
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        # Se tiver apenas vírgula (ex: 52,93), troca por ponto
        elif ',' in s:
            s = s.replace(',', '.')
            
        try:
            return round(float(s), 2)
        except ValueError:
            return 0.0

    df[col_valor] = df[col_valor].apply(converter)
    return df

def normalizar_status_cobranca(df):
    """Agrupa variações de status para um padrão único."""
    mapeamento = {
        'aberta': 'Em Aberto',
        'em aberto': 'Em Aberto',
        'atrasada': 'Atrasada',
        'paga': 'Paga',
        'pago': 'Paga'
    }
    df['status_cobranca'] = df['status_cobranca'].str.lower().str.strip().map(mapeamento).fillna('Indefinido')
    return df

def normalizar_tipo_cobranca(df):
    """Agrupa variações de tipo de cobrança."""
    mapeamento = {
        'mensal': 'Mensalidade',
        'mensalidade': 'Mensalidade',
        'setup': 'Setup',
        'upsell': 'Upsell'
    }
    df['tipo_cobranca'] = df['tipo_cobranca'].str.lower().str.strip().map(mapeamento).fillna('Outros')
    return df

def limpar_forma_pagamento(df):
    """Padroniza a forma de pagamento (remover acentos e espaços)."""
    df['forma_pagamento'] = df['forma_pagamento'].str.lower().str.strip().replace({
        'cartao': 'Cartão',
        'pix': 'Pix',
        'boleto': 'Boleto'
    })
    return df