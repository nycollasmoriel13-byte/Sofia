import sqlite3
DB = 'agencia_autovenda.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, user_id, role, content, timestamp FROM historico ORDER BY id DESC LIMIT 20")
rows = cur.fetchall()
if not rows:
    print('No history found')
else:
    for r in reversed(rows):
        print(f"[{r[0]}] {r[4]} | {r[2]} ({r[1]}): {r[3]}")
conn.close()
