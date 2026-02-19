import os
import logging
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')

client = None
if GOOGLE_API_KEY:
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        logger.info('Google GenAI client inicializado')
    except Exception as e:
        logger.error(f'Erro inicializando client google-genai: {e}')
else:
    logger.error('GEMINI/GOOGLE API KEY não encontrada nas variáveis de ambiente')

# Use nomes simples conforme a nova SDK
MODEL_NAME = 'gemini-1.5-flash'
FALLBACK_MODEL = 'gemini-1.5-pro'

SYSTEM_INSTRUCTION = (
    "Você é a Sofia, uma assistente virtual inteligente, amigável e prestativa. "
    "Responda de forma concisa, educada e use emojis ocasionalmente para ser empática."
)

async def get_gemini_response(prompt: str):
    if not client:
        return "Erro: cliente de IA não configurado."

    def call_generate(model: str, contents: str):
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=1000,
                temperature=0.7
            )
        )

    try:
        response = await asyncio.to_thread(call_generate, MODEL_NAME, prompt)
        return getattr(response, 'text', None)
    except Exception as e:
        logger.warning(f"Erro com modelo {MODEL_NAME}: {e}")
        try:
            response = await asyncio.to_thread(call_generate, FALLBACK_MODEL, prompt)
            return getattr(response, 'text', None)
        except Exception as e2:
            logger.error(f"Erro fatal em todos os modelos: {e2}")
            return "Desculpe, estou passando por instabilidades. Tente novamente mais tarde."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Eu sou a Sofia V2.6. Como posso te ajudar hoje?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    user_text = update.message.text
    reply = await get_gemini_response(user_text)
    await update.message.reply_text(reply)

def main():
    logger.info(">>> INICIANDO SOFIA V2.6 (GOOGLE-GENAI SDK) <<<")

    # Diagnostic: list models available
    if client:
        try:
            logger.info('Modelos disponíveis:')
            for m in client.models.list():
                logger.info(f' - {m.name}')
        except Exception as e:
            logger.error(f'Não foi possível listar modelos: {e}')

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info('Iniciando polling...')
    app.run_polling()

if __name__ == '__main__':
    main()
