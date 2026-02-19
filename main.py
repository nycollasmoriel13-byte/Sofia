import os
import logging
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Importação da biblioteca Google GenAI
try:
    from google import genai
    client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
    logger.info("IA Gemini configurada.")
except Exception as e:
    client = None
    logger.error(f"Erro IA: {e}")

# --- LOGICA DO TELEGRAM ---
async def start(update: Update, context):
    await update.message.reply_text('Olá! Sou a Sofia. Estou online e pronta para ajudar!')

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        loop = asyncio.get_event_loop()
        # Chamada para o Gemini
        if not client:
            await update.message.reply_text("IA não configurada no servidor.")
            return
        response = await loop.run_in_executor(None, lambda: client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Você é a Sofia da Agência Auto-Venda. Responda: {update.message.text}"
        ))
        text = getattr(response, 'text', None) or str(response)
        await update.message.reply_text(text if text else "Sem resposta da IA.")
    except Exception as e:
        logger.exception('Erro ao processar mensagem: %s', e)
        await update.message.reply_text("Tive um problema técnico. Tente novamente.")

# --- INICIALIZAÇÃO CONTROLADA ---
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN AUSENTE!")
        return

    global telegram_app
    try:
        telegram_app = Application.builder().token(TOKEN).build()
        telegram_app.add_handler(CommandHandler('start', start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await telegram_app.initialize()
        await telegram_app.start()

        # Iniciar polling em background sem travar o Uvicorn
        asyncio.create_task(telegram_app.updater.start_polling(drop_pending_updates=True))

        logger.info(">>> SOFIA OPERACIONAL <<<")
    except Exception as e:
        logger.exception('FALHA NO BOOT: %s', e)


@app.get("/")
def read_root():
    return {"status": "online", "bot": "Sofia"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import os
import uvicorn
if __name__ == "__main__":
    # Default port changed from 5000 to 8000 for Sofia
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

import os
import logging
import asyncio
import threading
try:
    # Prefer the new google.genai client when available
    import google.genai as genai
    import os
    import logging
    import asyncio
    from fastapi import FastAPI
    from dotenv import load_dotenv
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    # Configuração de Logs
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    load_dotenv()

    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GEMINI_KEY = os.getenv('GEMINI_API_KEY')

    # Importação da biblioteca Google GenAI
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
        logger.info("IA Gemini configurada.")
    except Exception as e:
        client = None
        logger.error(f"Erro IA: {e}")

    # --- LOGICA DO TELEGRAM ---
    async def start(update: Update, context):
        await update.message.reply_text('Olá! Sou a Sofia. Estou online e pronta para ajudar!')

    async def handle_message(update: Update, context):
        if not update.message or not update.message.text: return
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            loop = asyncio.get_event_loop()
            # Chamada para o Gemini
            response = await loop.run_in_executor(None, lambda: client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=f"Você é a Sofia da Agência Auto-Venda. Responda: {update.message.text}"
            ))
            await update.message.reply_text(response.text if response.text else "Sem resposta da IA.")
        except Exception as e:
            logger.error(f'Erro: {e}')
            await update.message.reply_text("Tive um problema técnico. Tente novamente.")

    # --- INICIALIZAÇÃO CONTROLADA ---
    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        if not TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN AUSENTE!")
            return

        global telegram_app
        try:
            # Build da aplicação
            telegram_app = Application.builder().token(TOKEN).build()
        
            # Handlers
            telegram_app.add_handler(CommandHandler('start', start))
            telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
            # Sequência síncrona de boot
            await telegram_app.initialize()
            await telegram_app.start()
        
            # Iniciar polling em background sem travar o Uvicorn
            asyncio.create_task(telegram_app.updater.start_polling(drop_pending_updates=True))
        
            logger.info(">>> SOFIA OPERACIONAL <<<")
        except Exception as e:
            logger.error(f"FALHA NO BOOT: {e}")

    @app.get("/")
    def read_root():
        return {"status": "online", "bot": "Sofia"}

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
        "gemini_ready": GEMINI_KEY is not None
    }

if __name__ == "__main__":
    # Default port changed from 5000 to 8000 for Sofia
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
