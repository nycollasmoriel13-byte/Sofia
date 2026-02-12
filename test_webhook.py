import httpx
import asyncio
import json

# Este script simula o que a Evolution API enviaria para o seu bot
# Útil para testar se a IA está respondendo corretamente sem precisar usar o celular

WEBHOOK_URL = "http://localhost:5000/webhook/telegram"

async def simular_mensagem(texto: str, chat_id: str = "123456789"):
    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": chat_id, "is_bot": False, "first_name": "Cliente Teste"},
            "chat": {"id": chat_id, "type": "private"},
            "date": 0,
            "text": texto
        }
    }

    print(f"🚀 Enviando simulação: '{texto}'")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(WEBHOOK_URL, json=payload)
            print(f"✅ Status do Bot: {response.status_code}")
            try:
                print(f"📩 Resposta: {response.json()}")
            except Exception:
                print("📩 Sem corpo JSON na resposta")
        except Exception as e:
            print(f"❌ Erro ao conectar no Bot: {e}. Certifique-se que o app está rodando na porta 5000.")

if __name__ == "__main__":
    # Teste 1: Cliente perguntando o preço
    asyncio.run(simular_mensagem("Olá, quanto custa a automação de vocês?"))
    
    # Descomente para testes adicionais
    # asyncio.run(simular_mensagem("Gostei do plano Secretária Virtual, meu nome é João"))
