import os
import sqlite3
import json
import os
import sqlite3
import stripe
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

# Configurações
STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_API_KEY
VPS_IP = "67.205.183.59"
BASE_URL = f"http://{VPS_IP}:8000"

app = FastAPI()

# Inicialização do Bot (padrão Handlers)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Olá! Eu sou a Sofia, sua assistente da Agência Auto-Venda. Como posso ajudar seu negócio hoje?")

async def handle_message(update: Update, context):
    # Lógica da IA aqui (conforme prompts anteriores)
    user_text = update.message.text
    await update.message.reply_text(f"Sofia processando: {user_text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def startup_event():
    # Inicia o bot em background no FastAPI
    import asyncio
    asyncio.create_task(telegram_app.initialize())
    asyncio.create_task(telegram_app.start())
    asyncio.create_task(telegram_app.updater.start_polling())

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    # Verificação de webhook simplificada para o exemplo
    return {"status": "success"}

@app.get("/")
def read_root():
    return {"message": "Sofia API Online", "ip": VPS_IP}
