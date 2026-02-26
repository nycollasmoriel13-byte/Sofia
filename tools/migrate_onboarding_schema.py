import sqlite3

DB = 'agencia_autovenda.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check if table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='onboarding_data'")
if not cur.fetchone():
    print('onboarding_data table does not exist; nothing to migrate.')
    conn.close()
    exit(0)

# Get columns
cols = [r[1] for r in cur.execute("PRAGMA table_info(onboarding_data)")]
print('Existing columns:', cols)
needed = {
    'whatsapp_contato': "TEXT",
    'website_cliente': "TEXT",
    'objetivos_ia': "TEXT",
    'data_coleta': "TEXT",
    'status_configuracao': "TEXT DEFAULT 'pendente'"
}
for col, coltype in needed.items():
    if col not in cols:
        try:
            cur.execute(f"ALTER TABLE onboarding_data ADD COLUMN {col} {coltype}")
            print(f'Added column {col}')
        except Exception as e:
            print('Failed to add', col, e)

conn.commit()
conn.close()
print('Migration complete.')
