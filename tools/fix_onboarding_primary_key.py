import sqlite3

DB = 'agencia_autovenda.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check existing schema
cur.execute("PRAGMA table_info(onboarding_data)")
cols = [r[1] for r in cur.fetchall()]
print('Current columns:', cols)

# Create new table with user_id as PRIMARY KEY
cur.execute('''
CREATE TABLE IF NOT EXISTS onboarding_data_new (
    user_id TEXT PRIMARY KEY,
    whatsapp_contato TEXT,
    website_cliente TEXT,
    objetivos_ia TEXT,
    data_coleta TEXT,
    status_configuracao TEXT DEFAULT 'pendente'
)
''')

# Copy data from old table to new, mapping existing columns if present
select_cols = []
# prefer new column names but fall back to old ones
select_cols.append("user_id")
select_cols.append("COALESCE(whatsapp_contato, whatsapp, '') as whatsapp_contato")
select_cols.append("COALESCE(website_cliente, website, '') as website_cliente")
select_cols.append("COALESCE(objetivos_ia, topics, '') as objetivos_ia")
select_cols.append("COALESCE(data_coleta, created_at, '') as data_coleta")
select_clause = ", ".join(select_cols)

try:
    cur.execute(f"INSERT OR REPLACE INTO onboarding_data_new ({', '.join([ 'user_id','whatsapp_contato','website_cliente','objetivos_ia','data_coleta','status_configuracao'])}) SELECT {select_clause}, COALESCE(status_configuracao, 'pendente') FROM onboarding_data")
    print('Copied rows into onboarding_data_new')
except Exception as e:
    print('Copy failed:', e)

# Drop old and rename
cur.execute('DROP TABLE onboarding_data')
cur.execute('ALTER TABLE onboarding_data_new RENAME TO onboarding_data')
conn.commit()
conn.close()
print('Recreated onboarding_data with user_id PRIMARY KEY')
