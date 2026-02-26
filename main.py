import os
import logging
import asyncio
import warnings
import google.generativeai as generativeai
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Silencia avisos de depreciação/forward incompatíveis nos logs
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Configuração do Cliente Gemini (biblioteca clássica google-generativeai)
model = None
if GEMINI_KEY:
    try:
        generativeai.configure(api_key=GEMINI_KEY)
        # Use GenerativeModel API (generate_content)
        model = generativeai.GenerativeModel('gemini-1.5-flash')
        logger.info("IA Gemini: google-generativeai configurada com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao configurar google-generativeai: {e}")
else:
    logger.warning("GEMINI_API_KEY não encontrada. O bot não responderá a mensagens.")


async def start(update: Update, context):
    """Responde ao comando /start"""
    await update.message.reply_text('Olá! Sou a Sofia, a sua assistente da Agência Auto-Venda. Como posso ajudar?')


async def handle_message(update: Update, context):
    """Processa mensagens utilizando google-generativeai (síncrono via thread)"""
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        if not model:
            await update.message.reply_text("Erro: IA não configurada no servidor.")
            return

        # Prompt de personalidade
        prompt_sys = "Tu és a Sofia, uma assistente virtual profissional da Agência Auto-Venda. Responde de forma simpática e prestativa em Português."
        full_prompt = f"{prompt_sys}\n\nCliente: {user_text}"

        # Chamada síncrona executada em thread para não bloquear o loop
        resp = await asyncio.to_thread(lambda: model.generate_content(full_prompt))

        # Extrair texto de diferentes formatos de resposta
        text_out = None
        if isinstance(resp, dict):
            text_out = resp.get('content') or (resp.get('candidates') and resp['candidates'][0].get('content'))
            if not text_out and 'output' in resp:
                try:
                    text_out = resp['output'][0]['content']
                except Exception:
                    text_out = None
        else:
            text_out = getattr(resp, 'text', None) or str(resp)

        if text_out:
            await update.message.reply_text(text_out)
            else:
                await update.message.reply_text("A IA não retornou texto. Tente reformular a pergunta.")
            
    except Exception as e:
        logger.error(f'ERRO CRÍTICO NA CONSULTA IA: {str(e)}', exc_info=True)
        await update.message.reply_text('Tive um problema técnico ao processar sua resposta. Por favor, tente novamente em instantes.')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gere o ciclo de vida do bot e da API"""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN ausente!")
        yield
        return

    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler('start', start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await telegram_app.initialize()
    await telegram_app.start()

    # run_polling is the modern, supported method for v20+ and returns when stopped
    polling_task = asyncio.create_task(telegram_app.run_polling())
    logger.info(">>> SOFIA ONLINE <<<")

    yield

    # Shutdown sequence
    try:
        await telegram_app.stop()
        await telegram_app.shutdown()
    except Exception:
        pass
    polling_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get('/')
def health_check():
    return {
        "status": "active", 
        "engine": "google-generativeai (classic)",
        "gemini_ready": client is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
