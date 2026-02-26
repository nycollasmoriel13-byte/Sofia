import sqlite3
import os
import sys

# Nome do arquivo de banco de dados local
DB_NAME = "agencia_autovenda.db"

def setup():
    """
    Prepara o ambiente de banco de dados local para a Sofia.
    Atualiza para gemini-1.5-flash-latest para evitar o erro 404 da v1beta.
    """
    print(f"🔧 Iniciando configuração do banco de dados local: {DB_NAME}")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Limpeza de tabelas
        cursor.execute("DROP TABLE IF EXISTS assinaturas")
        cursor.execute("DROP TABLE IF EXISTS historico")
        cursor.execute("DROP TABLE IF EXISTS configuracoes")

        # 2. Criação das tabelas
        cursor.execute('''CREATE TABLE assinaturas (user_id TEXT PRIMARY KEY, nome TEXT, plano TEXT, status TEXT DEFAULT 'lead', valor_mensal REAL, data_inicio TEXT)''')
        cursor.execute('''CREATE TABLE historico (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, role TEXT, content TEXT, timestamp TEXT)''')
        cursor.execute('''CREATE TABLE configuracoes (chave TEXT PRIMARY KEY, valor TEXT)''')
        
        # Gravação do modelo escolhido: gemini-3-flash
        # Troque para 'models/gemini-3-flash' se a sua SDK/API exigir o prefixo 'models/'
        cursor.execute("INSERT INTO configuracoes (chave, valor) VALUES (?, ?)", 
                   ("gemini_model", "gemini-3-flash"))

        system_prompt = (
            "Você é a Sofia, IA da agência 'Auto-Venda'. "
            "Você vende automação de vendas (chatbots), NÃO vende carros. "
            "Planos: Atendimento Flash (R$ 159,99), Secretária Virtual (R$ 559,99), Ecossistema Completo (R$ 1.499,99)."
        )
        
        cursor.execute("INSERT INTO configuracoes (chave, valor) VALUES (?, ?)", 
                       ("system_prompt", system_prompt))

        conn.commit()
        conn.close()
        print("✅ Banco de dados atualizado!")
        print("🚀 Modelo definido como: gemini-3-flash")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    setup()
