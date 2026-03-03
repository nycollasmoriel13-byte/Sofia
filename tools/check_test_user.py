import sqlite3

DB = "agencia_autovenda.db"
USER_ID = "USER_TESTE_123"

def main():
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT user_id, status, nome, plano FROM assinaturas WHERE user_id = ?", (USER_ID,))
        row = c.fetchone()
        print(row)
    except Exception as e:
        print("ERROR:", e)
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == '__main__':
    main()
