import httpx
import asyncio
import sqlite3

WEBHOOK_URL = "http://localhost:5000/webhook/telegram"
DB_NAME = "agencia_autovenda.db"

async def simular_conversa(texto: str, chat_id: str = "123456789"):
    payload = {
        "update_id": int(asyncio.get_event_loop().time()),
        "message": {
            "message_id": 1,
            "from": {"id": chat_id, "is_bot": False, "first_name": "Cliente"},
            "chat": {"id": chat_id, "type": "private"},
            "date": int(asyncio.get_event_loop().time()),
            "text": texto
        }
    }

    print(f"\n💬 Cliente enviou: '{texto}'")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(WEBHOOK_URL, json=payload, timeout=30.0)
            print(f"🤖 Resposta do Bot: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro: {e}")

def verificar_banco(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nome, plano, status, valor_mensal FROM assinaturas WHERE user_id = ?", (user_id,))
    lead = cursor.fetchone()
    conn.close()
    
    if lead:
        print("\n📊 --- Dados Gravados no Banco ---")
        print(f"👤 Nome: {lead[0]}")
        print(f"📦 Plano: {lead[1]}")
        print(f"🚦 Status: {lead[2]}")
        print(f"💰 Valor: R$ {lead[3]}")
    else:
        print("\n⚠️ Nenhum lead gravado ainda.")

async def main():
    numero_teste = "123456789"
    
    # Passo 1: Simular interesse e fechamento
    await simular_conversa("Gostei muito do Ecossistema Completo. Meu nome é Ricardo e quero assinar!", numero_teste)
    
    # Aguarda o processamento da IA
    await asyncio.sleep(2)
    
    # Passo 2: Verificar se a Function Calling da OpenAI funcionou e salvou no SQL
    verificar_banco(numero_teste)

if __name__ == "__main__":
    asyncio.run(main())
