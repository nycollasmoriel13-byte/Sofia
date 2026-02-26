import sqlite3

DB = 'agencia_autovenda.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('DB file:', DB)
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print('Tables:', tables)

cur.execute("PRAGMA table_info('assinaturas');")
print("assinaturas columns:", cur.fetchall())
cur.execute("PRAGMA table_info('historico');")
print("historico columns:", cur.fetchall())

conn.close()
