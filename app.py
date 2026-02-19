import os
import logging
import os
import sqlite3
import stripe
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import openai

load_dotenv()

# --- CONFIGURAÇÕES ---
STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
DB_NAME = "agencia_autovenda.db"

# Preços do .env
PRICES = {
    "Atendimento Flash": os.getenv("STRIPE_PRICE_ATENDIMENTO"),
    "Secretária Virtual": os.getenv("STRIPE_PRICE_SECRETARIA"),
    "Ecossistema Completo": os.getenv("STRIPE_PRICE_ECO")
}

app = FastAPI()

# --- BANCO DE DADOS ---
def save_message(user_id, role, content, name="Cliente"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO assinaturas (user_id, nome, whatsapp_id, status) VALUES (?, ?, ?, ?)", 
              (user_id, name, str(user_id), 'lead'))
    c.execute("INSERT INTO historico (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

# --- LÓGICA DE PAGAMENTO ---
def create_checkout(user_id, plan_name):
    price_id = PRICES.get(plan_name)
    if not price_id:
        return None
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=os.getenv("SUCCESS_URL"),
            cancel_url=os.getenv("CANCEL_URL"),
            client_reference_id=str(user_id)
        )
        return session.url
    except Exception as e:
        print(f"Erro Stripe: {e}")
        return None

# --- BOT TELEGRAM ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    user = update.effective_user
    save_message(user.id, "system", "Início de conversa", user.first_name)
    welcome_text = (
        f"Olá {user.first_name}! 🤖 Eu sou a Sofia, consultora da Auto-Venda.\n\n"
        "Ajudo empresas a automatizarem o atendimento e vendas. Nossos planos são:\n"
        "1. Atendimento Flash (R$ 159,99)\n"
        "2. Secretária Virtual (R$ 559,99)\n"
        "3. Ecossistema Completo (R$ 1.499,99)\n\n"
        "Como posso ajudar o seu negócio hoje?"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context):
    user = update.effective_user
    text = update.message.text
    save_message(user.id, "user", text, user.first_name)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é Sofia, vendedora da agência Auto-Venda. Seja profissional e persuasiva. Se o cliente escolher um plano, diga que vai gerar o link."},
                {"role": "user", "content": text}
            ]
        )
        reply = response.choices[0].message.content

        if "Flash" in reply or "Secretária" in reply or "Ecossistema" in reply:
            plano = "Atendimento Flash" if "Flash" in reply else "Secretária Virtual" if "Secretária" in reply else "Ecossistema Completo"
            link = create_checkout(user.id, plano)
            if link:
                reply += f"\n\n🚀 *Aqui está seu link para assinar o {plano}:*\n{link}"

        await update.message.reply_text(reply, parse_mode="Markdown")
        save_message(user.id, "assistant", reply)

    except Exception as e:
        await update.message.reply_text("Estou pensando muito... pode repetir?")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def startup_event():
    import asyncio as _asyncio
    _asyncio.create_task(telegram_app.initialize())
    _asyncio.create_task(telegram_app.start())
    _asyncio.create_task(telegram_app.updater.start_polling())

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    data = await request.json()
    if data.get('type') == 'checkout.session.completed':
        session = data['data']['object']
        user_id = session.get('client_reference_id')
        print(f"Pagamento confirmado para: {user_id}")
    return {"status": "success"}

@app.get("/")
def read_root():
    return {"status": "Sofia Online", "ip": os.getenv("VPS_IP", "Check .env")} 
