import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

try:
    import google.generativeai as genai
except Exception:
    genai = None

# Configuração de Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

model = None
if GEMINI_API_KEY and genai:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini configurado com sucesso.")
    except Exception as e:
        logger.exception("Erro ao configurar Gemini: %s", e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_id = update.effective_chat.id
    logger.info("Mensagem recebida de %s: %s", chat_id, (user_text[:120] + '...') if len(user_text) > 120 else user_text)

    try:
        # mostrar "digitando"
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        except Exception:
            pass

        if not model:
            await update.message.reply_text("Erro de configuração: modelo da IA indisponível.")
            return

        # executar geração em thread para não bloquear
        resp = await asyncio.to_thread(lambda: model.generate_content(user_text))
        reply = getattr(resp, 'text', None) or (getattr(resp, 'candidates', [None])[0] and getattr(resp.candidates[0], 'content', None)) or str(resp)

        await update.message.reply_text(reply)
    except Exception as e:
        logger.exception("Erro ao processar mensagem: %s", e)
        try:
            await update.message.reply_text("Desculpe, tive um erro interno. Verifique meus logs.")
        except Exception:
            pass

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não encontrado no .env — abortando.")
        raise SystemExit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info(">>> SOFIA V2.6 ONLINE E ESCUTANDO <<<")
    application.run_polling()
