import sqlite3
import os
import sys

DB_NAME = os.getenv("DB_NAME", "agencia_autovenda.db")

# Non-interactive script to recreate schema for Telegram launch.
# WARNING: this will DROP the tables and lose existing data.

CONFIRM = "--yes" in sys.argv or "-y" in sys.argv

print(f"This will DROP and recreate tables in '{DB_NAME}'.")
if not CONFIRM:
    resp = input("Type 'yes' to continue: ")
    if resp.strip().lower() != 'yes':
        print("Aborting.")
        sys.exit(0)

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

print("Dropping old tables if they exist...")
cur.execute("DROP TABLE IF EXISTS historico")
cur.execute("DROP TABLE IF EXISTS assinaturas")

print("Creating new tables (with user_id column)...")
cur.execute('''
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS assinaturas (
    user_id TEXT PRIMARY KEY,
    nome TEXT,
    status TEXT DEFAULT 'lead',
    plano TEXT,
    valor_mensal REAL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()
print("Database schema recreated successfully.")
