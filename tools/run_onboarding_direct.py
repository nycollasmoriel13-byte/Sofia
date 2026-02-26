import sqlite3
from pprint import pprint

# Import the onboarding hook
import sys
from pathlib import Path
# ensure repo root is on sys.path so `skills` package is importable
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from skills.onboarding import run as onb

USER_ID = '123456789'

# 1. Ensure assinaturas row exists and set to ativo
conn = sqlite3.connect('agencia_autovenda.db')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS assinaturas (user_id TEXT PRIMARY KEY, nome TEXT, plano TEXT, status TEXT, valor_mensal REAL, data_inicio TEXT)')
cur.execute('INSERT OR REPLACE INTO assinaturas (user_id, nome, plano, status, valor_mensal, data_inicio) VALUES (?, ?, ?, ?, ?, datetime("now"))', (USER_ID, 'Cliente Teste Onboarding', 'Ecossistema Completo', 'ativo', 1499.99))
conn.commit()
conn.close()
print('✅ Assinatura marcada como ativo para', USER_ID)

# 2. Call the onboarding hook with a sample message containing whatsapp, site and objetivos
message = "Meu WhatsApp é +55 (11) 91234-5678. Site: https://meusite.com. Objetivos: aumentar leads, automatizar agendamentos, melhorar atendimento."
res = onb.run(USER_ID, message, [])
print('\n--- Resultado do hook ---')
pprint(res)

# 3. Dump DB rows for verificacao
conn = sqlite3.connect('agencia_autovenda.db')
cur = conn.cursor()
print('\n--- assinaturas ---')
for row in cur.execute('SELECT user_id, nome, status, plano FROM assinaturas WHERE user_id = ?', (USER_ID,)):
    pprint(row)

print('\n--- onboarding_data ---')
for row in cur.execute('SELECT user_id, whatsapp_contato, website_cliente, objetivos_ia, data_coleta FROM onboarding_data WHERE user_id = ?', (USER_ID,)):
    pprint(row)
conn.close()
