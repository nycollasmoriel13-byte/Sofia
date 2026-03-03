import httpx
import asyncio
import sqlite3
import json
import uuid
import os
from dotenv import load_dotenv

# Tenta carregar o .env
load_dotenv()

# Configurações
URLS_PARA_TESTAR = ["http://localhost:8000/webhook/stripe", "http://localhost:5000/webhook/stripe"]
DB_PATH = "agencia_autovenda.db"

def garantir_usuario_no_db(user_id):
    """Garante que o ID de teste existe no SQLite local para evitar erro de integridade."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS assinaturas 
                          (user_id TEXT PRIMARY KEY, nome TEXT, plano TEXT, status TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO assinaturas (user_id, nome, plano, status) VALUES (?, ?, ?, ?)", 
                       (user_id, "Utilizador Teste", "pro", "pendente"))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Erro ao preparar DB: {e}")
        return False

async def enviar_webhook(url, payload, description):
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": "t=1700000000,v1=bypass" # Assinatura simulada para bypass
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"\n🚀 Testando {description} em {url}...")
            response = await client.post(url, json=payload, headers=headers, timeout=5)
            
            print(f"📥 Status: {response.status_code}")
            print(f"📝 Resposta: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ SUCESSO com {description}!")
                return True
        except Exception as e:
            print(f"❌ Falha de conexão: {e}")
    return False

async def executar_testes():
    user_id = "USER_TESTE_123"
    garantir_usuario_no_db(user_id)
    
    # Tentativa 1: Formato padrão com client_reference_id (mais comum no Checkout)
    payload_v1 = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{uuid.uuid4().hex[:10]}",
                "client_reference_id": user_id,
                "payment_status": "paid",
                "status": "complete"
            }
        }
    }

    # Tentativa 2: Formato com metadata (comum quando passamos dados extras)
    payload_v2 = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{uuid.uuid4().hex[:10]}",
                "metadata": {"user_id": user_id},
                "payment_status": "paid",
                "status": "complete"
            }
        }
    }

    for url in URLS_PARA_TESTAR:
        if await enviar_webhook(url, payload_v1, "Payload V1 (client_reference_id)"):
            break
        if await enviar_webhook(url, payload_v2, "Payload V2 (metadata)"):
            break

if __name__ == "__main__":
    print("--- INSTRUÇÕES PARA O TERMINAL DO APP.PY ---")
    print("Se estiver usando PowerShell, pare o app.py e rode:")
    print("$env:DEV_SKIP_STRIPE_SIG=\"1\"; python app.py")
    print("--------------------------------------------")
    asyncio.run(executar_testes())
