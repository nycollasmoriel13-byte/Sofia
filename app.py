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
    from telegram import Update, constants
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    from fastapi import FastAPI, Request

    # 1. Configuração de Logs detalhada
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # 2. Carregar variáveis
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DB_NAME = "agencia_autovenda.db"

    # Inicialização do Banco de Dados
    def init_db():
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    nome TEXT,
                    data_contato TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("✅ Banco de dados inicializado.")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco: {e}")

    init_db()

    # Configuração Robusta do Gemini
    if not GEMINI_API_KEY:
        logger.error("❌ CRÍTICO: GEMINI_API_KEY não encontrada no .env do servidor!")
        model = None
    else:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("✅ Gemini configurado com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro ao configurar Gemini: {e}")
            model = None

    # 3. Inicializar FastAPI
    app = FastAPI()

    # 4. Lógica da IA com Tratamento de Erro Refinado
    async def get_gemini_response(user_input, user_name="Cliente"):
        if not model:
            return "Erro de configuração: Chave API ausente ou inválida."
    
        try:
            prompt = (
                f"Você é a Sofia, uma consultora de automação profissional da Agência Auto-Venda. "
                f"Seu objetivo é ajudar o cliente chamado {user_name}. "
                f"Seja prestativa, use emojis moderadamente e foque em soluções de automação. "
                f"Pergunta: {user_input}"
            )
        
            # Uso do to_thread para não bloquear o loop de eventos
            response = await asyncio.to_thread(lambda: model.generate_content(prompt))
        
            if response and getattr(response, 'text', None):
                return response.text
            else:
                return "Recebi uma resposta vazia da inteligência artificial."
            
        except Exception as e:
            # Loga o erro real no console do servidor (importante para o PM2 logs)
            logger.error(f"🚨 ERRO GEMINI: {str(e)}")
            if "API_KEY_INVALID" in str(e) or "invalid" in str(e).lower():
                return "Erro: A chave da API do Gemini parece ser inválida."
            return "Tive um problema técnico ao processar sua resposta. Por favor, tente novamente em instantes."

    # 5. Handlers do Telegram
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"Comando /start recebido de {user.first_name}")
    
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO leads (user_id, username, nome) VALUES (?, ?, ?)", 
                           (user.id, user.username, user.first_name))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar lead: {e}")

        welcome_text = (
            f"Olá, {user.first_name}! Eu sou a Sofia, sua assistente da Auto-Venda. 🚀\n\n"
            "Estou aqui para transformar a produtividade do seu negócio com automações inteligentes.\n"
            "Como posso te ajudar hoje?"
        )
        await update.message.reply_text(welcome_text)

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_text = update.message.text
        user_name = update.effective_user.first_name
    
        # Feedback visual de "digitando"
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        except Exception:
            pass
    
        response_text = await get_gemini_response(user_text, user_name)
        await update.message.reply_text(response_text)

    # 6. Configuração do Bot do Telegram
    telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # 7. Eventos de Inicialização do Servidor
    @app.on_event("startup")
    async def startup_event():
        logger.info("🤖 Sofia Bot iniciando polling...")
        await telegram_app.initialize()
        await telegram_app.start()
        asyncio.create_task(telegram_app.run_polling())

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("👋 Sofia Bot desligando...")
        await telegram_app.stop()
        await telegram_app.shutdown()

    @app.get("/")
    async def root():
        return {"status": "online", "agent": "Sofia", "engine": "Gemini 1.5 Flash", "model_ready": model is not None}

    @app.post("/webhook/stripe")
    async def stripe_webhook(request: Request):
        return {"status": "received"}
