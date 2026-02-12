import os
import sqlite3
import json
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, Request
import httpx
import uvicorn
from openai import AsyncOpenAI
from typing import Optional, List
from dotenv import load_dotenv
import stripe
import threading
from telegram import Update
from telegram import Bot as TgBot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_LIB_AVAILABLE = True

# Carrega variáveis de ambiente
load_dotenv()

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autovenda")

# Configurações Iniciais
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "sua_api_key_aqui")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "sua_instancia")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_test_...") # Chave do Stripe

# Configuração da OpenAI
client_ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Cérebro Auto-Venda - Assinaturas Stripe")

# --- DATABASE SETUP ---
DB_NAME = "agencia_autovenda.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela atualizada para Recorrência (Assinaturas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assinaturas (
            user_id TEXT PRIMARY KEY,
            nome TEXT,
            status TEXT DEFAULT 'lead',
            plano TEXT,
            valor_mensal REAL,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def salvar_historico(user_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historico (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def atualizar_assinante(user_id: str, nome: str = None, plano: str = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM assinaturas WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO assinaturas (user_id, status) VALUES (?, 'lead')", (user_id,))
    
    if nome:
        cursor.execute("UPDATE assinaturas SET nome = ? WHERE user_id = ?", (nome, user_id))
    if plano:
        precos = {"Atendimento Flash": 159.99, "Secretária Virtual": 559.99, "Ecossistema Completo": 1499.99}
        valor = precos.get(plano, 0.0)
        cursor.execute("UPDATE assinaturas SET plano = ?, valor_mensal = ? WHERE user_id = ?", (plano, valor, user_id))
    
    conn.commit()
    conn.close()

def obter_historico(user_id: str) -> List[dict]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM historico WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

init_db()

# --- Stripe Price / Product mapping (set these in your env, do NOT hardcode keys)
STRIPE_PLANS = {
    "Atendimento Flash": os.getenv("STRIPE_PRICE_ATENDIMENTO", "price_placeholder_atendimento"),
    "Secretária Virtual": os.getenv("STRIPE_PRICE_SECRETARIA", "price_placeholder_secretaria"),
    "Ecossistema Completo": os.getenv("STRIPE_PRICE_ECO", "price_placeholder_ecossistema"),
}

# --- INTEGRAÇÃO STRIPE ---

# Prefer explicit STRIPE_SECRET_KEY if provided
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    stripe.api_key = STRIPE_API_KEY


async def criar_checkout_stripe(user_id: str, plano: str):
    """
    Cria uma sessão de Checkout do Stripe usando os Price IDs configurados em `STRIPE_PLANS`.
    Retorna a URL da sessão. Em caso de falha retorna um link fallback.
    """
    price_id = STRIPE_PLANS.get(plano)
    if not price_id:
        logger.error("Nenhum Price ID configurado para o plano: %s", plano)
        raise ValueError("Plano desconhecido")

    try:
        session = stripe.checkout.Session.create(
            success_url=os.getenv("SUCCESS_URL", "https://example.com/success?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=os.getenv("CANCEL_URL", "https://example.com/cancel"),
            mode="subscription",
            client_reference_id=user_id,
            line_items=[{"price": price_id, "quantity": 1}],
        )
        # session.url is only available for some Stripe SDK versions; build safe access
        return getattr(session, 'url', session.get('url') if isinstance(session, dict) else None) or session.id and f"https://checkout.stripe.com/pay/{session.id}"
    except Exception:
        logger.exception("Erro criando sessão de Checkout Stripe para %s / %s", user_id, plano)
        # Fallback link for development
        return f"https://checkout.stripe.com/pay/{price_id}?client_reference_id={user_id}"


def registrar_assinatura_sync(user_id: str, nome: str, plano: str):
    """Helper sync to update DB and create a checkout session URL synchronously if needed.
    Use `registrar_assinatura` async wrapper from async contexts.
    """
    # Update DB with lead info
    atualizar_assinante(user_id, nome=nome, plano=plano)
    # Can't call async stripe.create from sync easily; return planned price id so caller can create session
    price_id = STRIPE_PLANS.get(plano)
    return price_id


async def registrar_assinatura(user_id: str, nome: str, plano: str):
    """Register interest and create a Stripe Checkout Session returning the URL.
    Updates the assinaturas table and creates a Checkout Session.
    """
    atualizar_assinante(user_id, nome=nome, plano=plano)
    # Create and return checkout URL
    link = await criar_checkout_stripe(user_id, plano)
    return link


@app.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    """
    Recebe confirmação de assinatura do Stripe com verificação opcional de assinatura.
    Configure `STRIPE_WEBHOOK_SECRET` no .env para habilitar verificação.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    skip_verify = os.getenv("STRIPE_SKIP_SIGNATURE_VERIFY", "0") == "1"

    event = None
    if webhook_secret and not skip_verify:
        if not sig_header:
            logger.error("Missing Stripe signature header")
            return {"status": "missing signature"}, 400
        try:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
        except Exception as e:
            logger.exception("Falha ao validar assinatura Stripe: %s", e)
            return {"status": "invalid signature"}, 400
    else:
        try:
            event = await request.json()
            logger.warning("Stripe signature verification skipped (development)")
        except Exception:
            logger.exception("Falha ao ler payload Stripe")
            return {"status": "bad payload"}, 400

    # Normalize event object when stripe.Webhook.construct_event() returns an object
    event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
    data_obj = None
    if isinstance(event, dict):
        data_obj = event.get('data', {}).get('object', {})
    else:
        data_obj = getattr(event, 'data', {}).get('object', {}) if event else {}

    # Handle checkout session completed
    try:
        if event_type == 'checkout.session.completed' or data_obj.get('status') == 'complete' or data_obj.get('payment_status') in ('paid', 'paid'):
            session = data_obj
            user_id = session.get('client_reference_id')
            subscription_id = session.get('subscription') or session.get('subscriptions')
            customer_id = session.get('customer')

            if user_id:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO assinaturas (user_id, status, stripe_customer_id, stripe_subscription_id) VALUES (?, ?, ?, ?)",
                               (user_id, 'ativo', customer_id, subscription_id))
                cursor.execute("UPDATE assinaturas SET status = 'ativo', stripe_customer_id = ?, stripe_subscription_id = ? WHERE user_id = ?",
                               (customer_id, subscription_id, user_id))
                conn.commit()
                conn.close()

                mensagem_boas_vendas = (
                    "🎉 Assinatura Ativada com Sucesso!\n\n"
                    "Seja bem-vindo à Auto-Venda. Seu sistema já está sendo configurado. "
                    f"Para começar, preencha o seu perfil técnico aqui: https://autovenda.com/setup?id={user_id}"
                )
                try:
                    await enviar_mensagem_telegram(user_id, mensagem_boas_vendas)
                except Exception:
                    logger.exception("Falha ao enviar mensagem de boas-vindas para %s", user_id)

    except Exception:
        logger.exception("Erro processando evento Stripe")

    return {"status": "ok"}

# --- IA E FERRAMENTAS ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "assinar_plano",
            "description": "Registra o interesse do cliente em assinar um plano mensal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string"},
                    "plano": {"type": "string", "enum": ["Atendimento Flash", "Secretária Virtual", "Ecossistema Completo"]}
                },
                "required": ["nome", "plano"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are Sofia, a professional, respectful, and tech-savvy female AI consultant. You represent 'Auto-Venda'. You are helpful, have a great personality, and your goal is to convert leads into subscribers using the Stripe plans provided.

PLANOS DISPONÍVEIS:
1. Atendimento Flash: R$ 159,99/mês. FAQ e menus básicos.
2. Secretária Virtual: R$ 559,99/mês. Agendamentos e captura de leads.
3. Ecossistema Completo: R$ 1.499,99/mês. IA avançada e CRM.

REGRAS DE VENDA:
- O pagamento é feito via cartão de crédito (assinatura mensal recorrente).
- Não há taxa de adesão ou sinal de 50%. O cliente assina e o serviço começa a ser configurado.
- Prazo de entrega da configuração inicial: entre 5 a 20 dias, dependendo do plano.
- Quando o cliente decidir o plano, peça o nome dele e use a function-calling tool 'assinar_plano'.
"""

async def processar_com_ia(user_id: str, mensagem_usuario: str):
    historico = obter_historico(user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + historico + [{"role": "user", "content": mensagem_usuario}]

    try:
        response = await client_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
    except Exception:
        logger.exception("Erro ao chamar OpenAI para %s", user_id)
        raise

    # Log full response for debugging
    try:
        logger.info("OpenAI response for %s: %s", user_id, repr(response))
    except Exception:
        logger.exception("Falha ao logar resposta OpenAI")

    # Normalize message extraction depending on SDK shape
    try:
        response_message = None
        if hasattr(response, 'choices') and len(response.choices) > 0:
            response_message = response.choices[0].message
        elif isinstance(response, dict) and 'choices' in response and len(response['choices']) > 0:
            response_message = response['choices'][0].get('message')

        # Try to detect tool calls in different shapes
        tool_calls = None
        if response_message is not None:
            tool_calls = getattr(response_message, 'tool_calls', None) or (response_message.get('tool_calls') if isinstance(response_message, dict) else None)

        if tool_calls:
            for tool_call in tool_calls:
                # support object or dict shapes
                func_name = getattr(tool_call.function, 'name', None) if hasattr(tool_call, 'function') else (tool_call.get('function', {}).get('name') if isinstance(tool_call, dict) else None)
                if func_name == "assinar_plano":
                    # extract arguments
                    args_raw = None
                    if hasattr(tool_call.function, 'arguments'):
                        args_raw = tool_call.function.arguments
                    elif isinstance(tool_call, dict):
                        args_raw = tool_call.get('function', {}).get('arguments')

                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                    except Exception:
                        args = {}

                    nome, plano = args.get("nome"), args.get("plano")
                    # Centralize registration + checkout creation
                    try:
                        link = await registrar_assinatura(user_id, nome, plano)
                    except Exception:
                        logger.exception("Erro registrando assinatura para %s %s", user_id, plano)
                        link = await criar_checkout_stripe(user_id, plano)

                    resposta = (
                        f"Excelente escolha, {nome}! O plano {plano} vai transformar seu atendimento. 🚀\n\n"
                        f"Para ativar sua assinatura mensal, utilize o link seguro do Stripe abaixo:\n{link}\n\n"
                        "Assim que confirmar, daremos início à instalação!"
                    )
                    salvar_historico(user_id, "user", mensagem_usuario)
                    salvar_historico(user_id, "assistant", resposta)
                    return resposta

        # fallback to normal content
        resposta_texto = None
        if hasattr(response_message, 'content'):
            resposta_texto = response_message.content
        elif isinstance(response_message, dict):
            resposta_texto = response_message.get('content')

        if resposta_texto is None:
            resposta_texto = "Desculpe, não entendi. Pode reformular?"

        salvar_historico(user_id, "user", mensagem_usuario)
        salvar_historico(user_id, "assistant", resposta_texto)
        return resposta_texto
    except Exception:
        logger.exception("Erro processando resposta do modelo para %s", user_id)
        raise


@app.post("/webhook/telegram")
async def webhook_telegram(request: Request):
    data = await request.json()
    logger.info("Incoming Telegram update: %s", data)
    try:
        message = data.get('message') or data.get('edited_message')
        if not message:
            return {"ok": True}

        chat = message.get('chat', {})
        chat_id = chat.get('id')
        text = message.get('text') or message.get('caption')
        if text and chat_id:
            # handle /start command locally
            if text.strip().startswith('/start'):
                welcome = (
                    "Olá! Eu sou o bot da Auto-Venda. Aqui estão nossos planos:\n\n"
                    "1. Atendimento Flash — R$ 159,99/mês\n"
                    "2. Secretária Virtual — R$ 559,99/mês\n"
                    "3. Ecossistema Completo — R$ 1.499,99/mês\n\n"
                    "Envie uma mensagem dizendo qual plano deseja e seu nome (ex: 'Quero o Ecossistema Completo. Meu nome é João') e eu vou gerar o link de pagamento para você."
                )
                try:
                    await enviar_mensagem_telegram(str(chat_id), welcome)
                except Exception:
                    logger.exception("Falha ao enviar /start para %s", chat_id)
                return {"ok": True}

            res = await processar_com_ia(str(chat_id), text)
            try:
                await enviar_mensagem_telegram(str(chat_id), res)
            except Exception:
                logger.exception("Falha ao enviar resposta para %s", chat_id)
    except Exception:
        logger.exception("Erro no endpoint /webhook/telegram")
    return {"ok": True}


async def enviar_mensagem_telegram(user_id: str, message: str):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set; cannot send message")
        return

    if not TELEGRAM_LIB_AVAILABLE:
        logger.error("python-telegram-bot not installed; please install requirements")
        return

    bot = TgBot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=user_id, text=message)
    except Exception:
        logger.exception("Erro ao enviar mensagem via python-telegram-bot para %s", user_id)
        raise


# --- Start a python-telegram-bot Application in background (polling) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_APP = None

def start_telegram_application():
    """Start the python-telegram-bot Application in a background thread (polling).
    This provides stable command and message handlers.
    """
    global TELEGRAM_APP
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set; telegram application will not start")
        return

    try:
        TELEGRAM_APP = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            welcome = (
                "Olá! Eu sou o bot da Auto-Venda. Aqui estão nossos planos:\n\n"
                "1. Atendimento Flash — R$ 159,99/mês\n"
                "2. Secretária Virtual — R$ 559,99/mês\n"
                "3. Ecossistema Completo — R$ 1.499,99/mês\n\n"
                "Envie uma mensagem dizendo qual plano deseja e seu nome (ex: 'Quero o Ecossistema Completo. Meu nome é João') e eu vou gerar o link de pagamento para você."
            )
            await context.bot.send_message(chat_id=chat_id, text=welcome)

        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            text = update.message.text if update.message else None
            if not text:
                return
            user_id = str(update.effective_user.id)
            try:
                resposta = await processar_com_ia(user_id, text)
            except Exception:
                logger.exception("Erro ao processar mensagem IA para %s", user_id)
                resposta = "Desculpe, ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=resposta)

        TELEGRAM_APP.add_handler(CommandHandler('start', start_command))
        TELEGRAM_APP.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

        def _run():
            TELEGRAM_APP.run_polling()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        logger.info("Telegram Application started (polling mode) in background thread")
    except Exception:
        logger.exception("Failed to start Telegram Application")


@app.on_event("startup")
async def _startup():
    # Ensure DB initialized and start bot
    init_db()
    start_telegram_application()

# `main.py` will run the ASGI app using uvicorn. Do not run uvicorn here.
