import sqlite3
import os

# Nome do arquivo de banco de dados local
DB_NAME = "agencia_autovenda.db"

def setup():
    print(f"🔧 A preparar o motor da Sofia (Base de Dados)...")
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("🗑️ Base de dados antiga removida.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabela de Assinaturas (Foco no Telegram)
    cursor.execute('''
        CREATE TABLE assinaturas (
            user_id TEXT PRIMARY KEY,
            nome TEXT,
            whatsapp_id TEXT,
            plano TEXT,
            status TEXT DEFAULT 'pendente',
            valor_mensal REAL,
            data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de Configurações do Sistema
    cursor.execute('''
        CREATE TABLE configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')

    # Dados Iniciais
    cursor.execute("INSERT INTO configuracoes (chave, valor) VALUES (?, ?)", 
                   ("versao_sistema", "1.0.0"))

    conn.commit()
    conn.close()
    print("✅ Base de dados criada com sucesso! Podes iniciar o app.py.")

if __name__ == "__main__":
    setup()
