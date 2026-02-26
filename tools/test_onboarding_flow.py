import sqlite3
import json
import httpx
import asyncio
import os
from datetime import datetime

# --- RESOLUÇÃO DE CAMINHOS ---
# Garante que o script encontra o .db na raiz, independentemente de onde é executado
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, "agencia_autovenda.db")

# Pode ser sobrescrito por env var para testes em diferentes portas/rotas
WEBHOOK_STRIPE_URL = os.getenv('WEBHOOK_STRIPE_URL', 'http://localhost:5000/webhook/stripe')


def simular_assinatura_ativa(user_id):
    """Prepara o banco de dados para o teste de onboarding."""
    print(f"📂 Verificando banco de dados em: {DB_NAME}")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Criar tabelas necessárias caso não existam (Schema unificado)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assinaturas (
                user_id TEXT PRIMARY KEY, 
                nome TEXT, 
                plano TEXT, 
                status TEXT, 
                valor_mensal REAL, 
                data_inicio TEXT
            )
        ''')
        
        # Criar a tabela de onboarding se ainda não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS onboarding_data (
                user_id TEXT PRIMARY KEY,
                whatsapp_contato TEXT,
                website_cliente TEXT,
                objetivos_ia TEXT,
                status_configuracao TEXT DEFAULT 'pendente',
                data_coleta TEXT
            )
        ''')
        
        # Insere o lead como 'pendente' para o Stripe poder ativar
        cursor.execute('''
            INSERT OR REPLACE INTO assinaturas (user_id, nome, plano, status, valor_mensal, data_inicio)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 'Cliente Teste Onboarding', 'Ecossistema Completo', 'pendente', 1499.99, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print(f"✅ Lead {user_id} preparado como 'pendente' no banco local.")
    except Exception as e:
        print(f"❌ Erro ao manipular o SQLite: {e}")


async def disparar_webhook_stripe(user_id):
    """Envia o payload simulado do Stripe para o servidor local."""
    # Nota: client_reference_id deve ser o mesmo user_id do banco
    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(user_id),
                "status": "complete",
                "payment_status": "paid"
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"📡 Disparando Webhook para: {WEBHOOK_STRIPE_URL}...")
            response = await client.post(WEBHOOK_STRIPE_URL, json=payload, timeout=10.0)
            
            print(f"💳 Resposta do Servidor: {response.status_code}")
            try:
                print(f"📄 Conteúdo: {response.json()}")
            except:
                print(f"📄 Conteúdo: {response.text}")
                
            if response.status_code == 200:
                print("✨ Sucesso! O utilizador deve estar ATIVO agora.")
            else:
                print("⚠️ O servidor recebeu, mas retornou um erro. Verifique os logs do app.py.")
                
        except Exception as e:
            print(f"❌ Falha de conexão: O app.py está a correr? Erro: {e}")


async def main():
    # Este ID deve ser o teu ID real do Telegram para testares o bot logo a seguir
    user_id_teste = "123456789" 
    
    print("\n" + "="*40)
    print("🚀 INICIANDO SIMULAÇÃO DE FLUXO DE VENDA")
    print("="*40)
    
    # 1. Setup do Banco
    simular_assinatura_ativa(user_id_teste)
    
    # 2. Simulação do Gatilho de Pagamento
    await disparar_webhook_stripe(user_id_teste)
    
    print("\n🔍 VERIFICAÇÃO FINAL:")
    print(f"1. Abre o teu Dashboard (streamlit run dashboard.py)")
    print(f"2. Confirma se o utilizador {user_id_teste} aparece como 'ativo'.")
    print(f"3. Envia uma mensagem no Telegram para ver se o onboarding começa.")
    print("="*40)


if __name__ == "__main__":
    asyncio.run(main())
