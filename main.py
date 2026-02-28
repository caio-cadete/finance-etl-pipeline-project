# ... (imports anteriores)
from src.transform.transform import padronizar_emails

def main():
    df = extrair_clientes("data/raw/clientes.xlsx")
    
    # Ordem lógica: 
    # 1. Limpa o nome primeiro
    df = limpar_nomes_clientes(df)
    # 2. Usa o nome limpo para validar o e-mail
    df = padronizar_emails(df)
    
    print("✅ E-mails padronizados com sucesso!")
    print(df[['nome_cliente', 'email_padrao']].head())