import os
import warnings
import sqlite3
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Suppress deprecation warning from older google.generativeai package
warnings.filterwarnings("ignore", message="All support for the `google.generativeai` package has ended")

from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

try:
    # Prefer the stable (older) SDK for Gemini: google-generativeai
    import google.generativeai as genai
except Exception:
    genai = None

import stripe

# Config de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")
DB_NAME = os.getenv("DB_NAME", "agencia_autovenda.db")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

stripe.api_key = STRIPE_KEY

# Inicializar cliente/modelo
model = None
if GEMINI_API_KEY:
    try:
        if genai is not None:
            # configure the stable SDK
            genai.configure(api_key=GEMINI_API_KEY)
                try:
                    model = genai.GenerativeModel(GEMINI_MODEL)
                    logger.info(f"Gemini (google-generativeai) configurado. Modelo: {GEMINI_MODEL}")
                except Exception:
                    # fallback to common name
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    logger.info("Gemini configurado com fallback para gemini-1.5-flash.")
            logger.info("Gemini (google-generativeai) configurado.")
        else:
            logger.error("google-generativeai não instalado. Instala com: pip install -U google-generativeai")
    except Exception as e:
        logger.exception("Erro ao configurar Gemini: %s", e)
else:
    logger.error("ERRO: GEMINI_API_KEY não encontrada no .env")

# --- DB helpers ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_historico(user_id, role, content):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historico (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, role, content, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("Erro ao salvar histórico: %s", e)

def get_historico(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM historico WHERE user_id = ? ORDER BY timestamp ASC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def call_gemini_sync(prompt: str):
    """Chama o modelo Gemini de forma bloqueante (usado com asyncio.to_thread)."""
    try:
        if model is None:
            return "Erro: modelo Gemini não configurado."

        # Usar a API estável: model.generate_content
        resp = model.generate_content(prompt)
        # Extrair texto da resposta
        text = getattr(resp, 'text', None)
        if text:
            return text
        # fallback para candidates
        candidates = getattr(resp, 'candidates', None)
        if candidates and len(candidates) > 0:
            return getattr(candidates[0], 'content', str(resp))
        return str(resp)
    except Exception as e:
        return f"Erro ao chamar Gemini: {e}"

async def get_gemini_response(user_id, user_text):
    historico = get_historico(user_id)
    system_prompt = (
        "És a Sofia, consultora profissional e simpática da agência 'Auto-Venda'. "
        "Seja concisa, use emojis e foque na conversão.\n\n"
    )
    full_prompt = system_prompt + "Histórico recente:\n"
    for role, content in historico:
        full_prompt += f"{role}: {content}\n"
    full_prompt += f"Usuário: {user_text}\nSofia:"

    # Executar chamada bloqueante em thread para não bloquear o loop async
    reply = await asyncio.to_thread(call_gemini_sync, full_prompt)
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"Olá {user.first_name}! 🚀 Eu sou a Sofia, a tua consultora de automação.\n\n"
        "Estou aqui para ajudar a tua empresa a vender mais enquanto dormes. "
        "Queres conhecer os nossos planos de atendimento automático?"
    )
    salvar_historico(str(user.id), "assistant", welcome_text)
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = str(update.effective_user.id)
    user_text = update.message.text
    salvar_historico(user_id, "user", user_text)

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    except Exception:
        pass

    # Gerar resposta
    try:
        response_text = await get_gemini_response(user_id, user_text)
    except Exception as e:
        logger.exception("Erro ao obter resposta do Gemini: %s", e)
        response_text = "Desculpe, tive um problema técnico ao gerar a resposta. Tenta novamente mais tarde."

    # Garantir que exista texto para enviar
    if not response_text:
        response_text = "Desculpe, não consegui gerar uma resposta neste momento."

    # Registar e enviar resposta de forma resiliente
    try:
        salvar_historico(user_id, "assistant", response_text)
    except Exception:
        # já logado dentro de salvar_historico
        pass

    try:
        await update.message.reply_text(response_text)
    except Exception as e:
        logger.exception("Falha ao enviar resposta com reply_text: %s", e)
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)
        except Exception as e2:
            logger.exception("Falha ao enviar resposta com send_message: %s", e2)

def main():
    init_db()
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado no .env — abortando.")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("🚀 Sofia Ativa com Gemini! (Pressione Ctrl+C para parar)")
    # Garantir que existe um event loop associado ao thread principal (compatibilidade com Python >=3.10+)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application.run_polling()

if __name__ == '__main__':
    main()
