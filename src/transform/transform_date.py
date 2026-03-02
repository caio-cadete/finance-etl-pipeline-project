import pandas as pd
import re


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
