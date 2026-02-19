import sqlite3
import os
import sys

DB_NAME = "agencia_autovenda.db"

def setup():
    if "--yes" not in sys.argv:
        confirm = input("Isso apagará todos os dados do banco atual. Continuar? (s/n): ")
        if confirm.lower() != 's':
            return

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"✅ Banco antigo {DB_NAME} removido.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabela de Assinaturas/Leads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assinaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            nome TEXT,
            whatsapp_id TEXT,
            plano TEXT,
            status TEXT DEFAULT 'lead',
            valor_mensal REAL,
            data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de Histórico de Mensagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("🚀 Banco de dados configurado com sucesso para o Telegram!")

if __name__ == "__main__":
    setup()
