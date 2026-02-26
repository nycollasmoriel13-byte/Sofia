import sqlite3
from pprint import pprint

DB_NAME = 'agencia_autovenda.db'
USER_ID = '123456789'

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

print('--- assinaturas row ---')
for row in cur.execute('SELECT * FROM assinaturas WHERE user_id = ?', (USER_ID,)):
    pprint(row)

print('\n--- onboarding_data rows ---')
for row in cur.execute('SELECT * FROM onboarding_data WHERE user_id = ?', (USER_ID,)):
    pprint(row)

conn.close()
