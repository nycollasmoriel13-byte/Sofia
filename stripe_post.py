import httpx
import asyncio
import sqlite3

WEBHOOK_URL = "http://localhost:5000/webhook/stripe"
DB_NAME = "agencia_autovenda.db"

def pegar_ultimo_lead():
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, nome FROM assinaturas ORDER BY data_inicio DESC LIMIT 1")
	lead = cursor.fetchone()
	conn.close()
	return lead

async def post_stripe():
	lead = pegar_ultimo_lead()
	if not lead:
		print("❌ Nenhum lead encontrado no banco. Converse com o bot primeiro e escolha um plano!")
		return

	user_id, nome = lead
	print(f"💳 Simulando pagamento no Stripe para o cliente: {nome} (ID: {user_id})")

	payload = {
		"client_reference_id": str(user_id),
		"status": "active",
		"type": "checkout.session.completed"
	}

	async with httpx.AsyncClient() as client:
		try:
			r = await client.post(WEBHOOK_URL, json=payload, timeout=10.0)
			print(f"✅ Webhook respondeu com status: {r.status_code}")
			print(r.text)
		except Exception as e:
			print(f"❌ Erro ao conectar no servidor local: {e}. Certifique-se que o app.py está rodando.")

if __name__ == "__main__":
	asyncio.run(post_stripe())
