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
    import os
    import logging
    import asyncio
    import sqlite3
    import google.generativeai as genai
    from dotenv import load_dotenv
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    from fastapi import FastAPI, Request

    # 1. Configuração de Logs
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DB_NAME = "agencia_autovenda.db"

    if not GEMINI_API_KEY:
        logger.error("❌ Erro: GEMINI_API_KEY não encontrada no .env")
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

    app = FastAPI()


    async def get_gemini_response(user_input: str) -> str:
        try:
            prompt = (
                f"Você é a Sofia, uma consultora de automação profissional da Agência Auto-Venda. "
                f"Seja prestativa e educada. Pergunta do cliente: {user_input}"
            )
            response = model.generate_content(prompt)
            # Algumas versões retornam um objeto com 'text', outras usam 'candidates'
            if hasattr(response, 'text'):
                return response.text
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                return response.candidates[0].content
            return str(response)
        except Exception as e:
            logger.exception(f"Erro ao chamar Gemini: {e}")
            return "Desculpe, tive um soluço técnico aqui no meu cérebro de IA. Pode repetir?"


    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        welcome_text = (
            "Olá! Eu sou a Sofia, sua assistente da Auto-Venda. 🚀\n\n"
            "Estou aqui para ajudar você a automatizar seu negócio. Como posso ajudar hoje?"
        )
        await update.message.reply_text(welcome_text)


    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        except Exception:
            # Não crítico — apenas tenta mostrar typing
            pass

        response_text = await get_gemini_response(user_text)
        await update.message.reply_text(response_text)


    telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))


    @app.on_event("startup")
    async def startup_event():
        logger.info("🤖 Iniciando polling do Telegram...")
        asyncio.create_task(telegram_app.initialize())
        asyncio.create_task(telegram_app.start())
        asyncio.create_task(telegram_app.run_polling())


    @app.get("/")
    async def root():
        return {"status": "Sofia está online!", "provider": "Google Gemini"}


    @app.post("/webhook/stripe")
    async def stripe_webhook(request: Request):
        payload = await request.json()
        # Lógica de confirmação de pagamento aqui
        logger.info("Stripe webhook recebido: %s", payload.get('type'))
        return {"status": "success"}
