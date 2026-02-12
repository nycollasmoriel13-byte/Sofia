import sqlite3

DB_NAME = 'agencia_autovenda.db'

def print_table(table):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        rows = cur.execute(f"SELECT * FROM {table}").fetchall()
        print(f"\n== {table} ({len(rows)} rows) ==")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Could not read {table}: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    print_table('assinaturas')
    print_table('historico')
