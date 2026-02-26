import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Allow overriding the DB name via .env
DB_NAME = os.getenv("DB_NAME", "agencia_autovenda.db")


def remove_server_artifacts():
    """Remove ficheiros de configuração de servidor locais se existirem (não perigoso).
    Esta função apenas remove ficheiros conhecidos que podem ter sido deixados por deploys
    (ex.: arquivos de exemplo nginx). É segura: verifica existência antes de apagar.
    """
    candidates = [
        os.path.join('deploy', 'nginx', 'sofia'),
        'sofia.pid',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    # don't recursively delete directories here
                    print(f"Nota: diretório de deploy encontrado (não removido): {path}")
                else:
                    os.remove(path)
                    print(f"✅ Artefacto de servidor removido: {path}")
            except Exception as e:
                print(f"Aviso: não foi possível remover {path}: {e}")


def setup():
    clean_server = '--clean-server' in sys.argv

    if "--yes" not in sys.argv:
        confirm = input("Isso apagará todos os dados do banco atual. Continuar? (s/n): ")
        if confirm.lower() != 's':
            return

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"✅ Banco antigo {DB_NAME} removido.")

    if clean_server:
        remove_server_artifacts()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Ativar chaves estrangeiras e configurações recomendadas
    cursor.execute('PRAGMA foreign_keys = ON;')
    cursor.execute('PRAGMA journal_mode = WAL;')

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

    # Índices úteis
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_historico_user ON historico(user_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assinaturas_user ON assinaturas(user_id);')

    conn.commit()

    # VACUUM para otimizar o ficheiro novo
    try:
        cursor.execute('VACUUM;')
    except Exception:
        pass

    conn.close()
    print(f"🚀 Banco de dados '{DB_NAME}' configurado com sucesso para o ambiente local em {datetime.now().isoformat()}.")


if __name__ == "__main__":
    setup()
