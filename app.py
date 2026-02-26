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
import threading
try:
    from flask import Flask, request, jsonify
except Exception:
    Flask = None
    request = None
    jsonify = None

# Config de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")
DB_NAME = os.getenv("DB_NAME", "agencia_autovenda.db")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")

stripe.api_key = STRIPE_KEY

# Modelo/cliente Gemini (inicializado mais tarde, após garantir DB e configs)
model = None

def get_config(chave: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = ? COLLATE NOCASE", (chave,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def get_system_prompt():
    sp = get_config('system_prompt')
    if sp:
        # Ensure language preference is explicit
        return sp + "\n\nResponda sempre em português (pt-BR). Use um tom profissional, claro e natural."
    # fallback padrão
    return (
        "És a Sofia, consultora profissional e simpática da agência 'Auto-Venda'. "
        "Seja concisa, use emojis e foque na conversão. Responda sempre em português (pt-BR)."
    )

def get_gemini_model_from_db():
    val = get_config('GEMINI_MODEL') or get_config('gemini_model') or GEMINI_MODEL
    return val

def init_gemini_from_model_name(model_name: str):
    global model
    if not GEMINI_API_KEY:
        logger.error("ERRO: GEMINI_API_KEY não encontrada no .env — Gemini não será inicializado.")
        return
    if genai is None:
        logger.error("google-generativeai não instalado. Instala com: pip install -U google-generativeai")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        tried = []
        candidates = []
        if model_name:
            candidates.append(model_name)
        if model_name and not model_name.startswith('models/'):
            candidates.append(f"models/{model_name}")
        base = model_name.replace('-latest', '') if model_name else ''
        if base and base not in candidates:
            candidates.append(base)
        if base and not base.startswith('models/'):
            candidates.append(f"models/{base}")

        fallbacks = [
            'models/gemini-flash-latest',
            'models/gemini-2.5-flash',
            'models/gemini-pro'
        ]
        for fb in fallbacks:
            if fb not in candidates:
                candidates.append(fb)

        for candidate in candidates:
            try:
                model = genai.GenerativeModel(candidate)
                logger.info(f"Gemini configurado. Modelo: {candidate}")
                return
            except Exception as e:
                tried.append((candidate, str(e)))

        logger.error("Falha ao localizar modelo Gemini. Tentativas: %s", tried)
    except Exception as e:
        logger.exception("Erro ao configurar Gemini: %s", e)

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
    # Garantir que a tabela de configuracoes exista (pode ser criada pelo setup_db.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')
    # Skills table: records installed skills and metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            version TEXT,
            installed_at TEXT
        )
    ''')

    # Skills usage telemetry
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT,
            user_id TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()


def start_stripe_webhook_server():
    """Start a small Flask server to receive Stripe webhooks and activate subscriptions."""
    if Flask is None:
        logger.warning("Flask not installed; Stripe webhook server not started.")
        return

    app = Flask('sofia_webhook')

    @app.route('/stripe_webhook', methods=['POST'])
    @app.route('/webhook/stripe', methods=['POST'])
    def stripe_webhook():
        payload = None
        sig_header = request.headers.get('Stripe-Signature')
        secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        try:
            # Allow bypass of Stripe signature verification in development/testing
            # controlled by DEV_SKIP_STRIPE_SIG or DEV_MODE environment variables.
            dev_skip = os.getenv('DEV_SKIP_STRIPE_SIG') == '1' or os.getenv('DEV_MODE') == '1'

            if secret and sig_header and not dev_skip:
                # production path: verify signature
                event = stripe.Webhook.construct_event(request.data, sig_header, secret)
            else:
                # development/testing path: parse JSON directly
                if dev_skip and (not secret or not sig_header):
                    logger.info('DEV_SKIP_STRIPE_SIG active: parsing webhook without signature verification')
                event = request.get_json(force=True)
        except Exception as e:
            logger.exception('Erro ao validar webhook Stripe: %s', e)
            return jsonify({'status': 'invalid'}), 400

        # Handle checkout.session.completed
        try:
            etype = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
            data_obj = None
            if isinstance(event, dict):
                data_obj = event.get('data', {}).get('object')
            else:
                data_obj = getattr(event, 'data', {}).get('object')

            if etype == 'checkout.session.completed' and data_obj:
                client_ref = data_obj.get('client_reference_id')
                if not client_ref:
                    logger.warning('Stripe webhook received without client_reference_id')
                    return jsonify({'status': 'invalid', 'reason': 'missing_client_reference_id'}), 400

                client_ref = str(client_ref)
                # activate subscription in local DB
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("UPDATE assinaturas SET status = 'ativo' WHERE user_id = ?", (client_ref,))
                    conn.commit()
                    updated = cur.rowcount
                    conn.close()

                    if updated and updated > 0:
                        logger.info('Activated subscription for user %s via Stripe webhook', client_ref)
                        # Após ativar, disparar hook de onboarding automaticamente (não bloqueante)
                        try:
                            def _run_onboarding():
                                try:
                                    out = run_skill_hook('onboarding', client_ref, '', [])
                                    logger.info('Onboarding hook run result for %s: %s', client_ref, out)
                                except Exception:
                                    logger.exception('Erro ao executar onboarding hook em background')

                            t_onb = threading.Thread(target=_run_onboarding, daemon=True)
                            t_onb.start()
                        except Exception:
                            logger.exception('Não foi possível agendar execução do onboarding hook')
                    else:
                        logger.warning('No subscription record updated for user %s', client_ref)
                        return jsonify({'status': 'invalid', 'reason': 'user_not_found'}), 400
                except Exception:
                    logger.exception('Falha ao atualizar assinatura no DB via webhook')
                    return jsonify({'status': 'invalid', 'reason': 'db_error'}), 500

        except Exception:
            logger.exception('Erro ao processar evento Stripe')

        return jsonify({'status': 'ok'})

    port = int(os.getenv('WEBHOOK_PORT', '8000'))
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    try:
        # run Flask app in blocking mode inside a thread
        app.run(host=host, port=port)
    except Exception:
        logger.exception('Falha ao iniciar servidor Flask para webhooks')

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


def load_local_skills(skills_path='skills'):
    import json
    from pathlib import Path
    skills = {}
    base = Path(skills_path)
    if not base.exists():
        return skills
    for d in base.iterdir():
        if not d.is_dir():
            continue
        meta_file = d / 'meta.json'
        skill_file = d / 'SKILL.md'
        try:
            meta = {}
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding='utf-8'))
            content = skill_file.read_text(encoding='utf-8') if skill_file.exists() else ''
            name = meta.get('name') or d.name
            skills[name] = {
                'meta': meta,
                'content': content
            }
        except Exception:
            continue
    return skills


def register_skills_in_db(skills):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for name, data in skills.items():
        meta = data.get('meta', {})
        title = meta.get('title', '')
        desc = meta.get('description', '')
        version = meta.get('version', '')
        cursor.execute("INSERT OR REPLACE INTO skills (name, title, description, version, installed_at) VALUES (?, ?, ?, ?, datetime('now'))",
                       (name, title, desc, version))
    conn.commit()
    conn.close()


def salvar_skill_usage(skill_name, user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO skills_usage (skill_name, user_id, timestamp) VALUES (?, ?, ?)",
                       (skill_name, user_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def match_skill(skills, user_text):
    """Very simple trigger matcher: counts keyword hits from meta.triggers."""
    if not user_text or not skills:
        return None
    txt = user_text.lower()
    best = (None, 0)
    for name, data in skills.items():
        triggers = data.get('meta', {}).get('triggers', []) or []
        score = 0
        for t in triggers:
            if t.lower() in txt:
                score += 1
        if score > best[1]:
            best = (name, score)
    # require at least one match
    return best[0] if best[1] > 0 else None

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
    system_prompt = get_system_prompt() + "\n\n"
    # Progressive disclosure: check for skill invocation
    skills = load_local_skills()
    invoked = match_skill(skills, user_text)
    skill_context = ''
    if invoked:
        skill_context = f"\n--- SKILL: {invoked} ---\n" + skills[invoked].get('content', '') + "\n--- END SKILL ---\n"
        # track usage
        salvar_skill_usage(invoked, user_id)
    full_prompt = system_prompt + skill_context + "Histórico recente:\n"
    for role, content in historico:
        full_prompt += f"{role}: {content}\n"
    full_prompt += f"Usuário: {user_text}\nSofia:"

    # Executar chamada bloqueante em thread para não bloquear o loop async
    reply = await asyncio.to_thread(call_gemini_sync, full_prompt)
    # If the invoked skill provides a deterministic hook (skills/<name>/run.py), execute it
    if invoked:
        try:
            hook_output = run_skill_hook(invoked, user_id, user_text, historico)
            if hook_output:
                # append hook output to the LLM reply so user gets deterministic artifact
                reply = f"{reply}\n\n--- Resultado da skill '{invoked}' ---\n{hook_output}"
        except Exception:
            pass
    return reply


def run_skill_hook(skill_name, user_id, user_text, history):
    """Dynamically import and run a skill hook if present. Returns string or None."""
    try:
        import importlib
        mod_name = f"skills.{skill_name}.run"
        mod = importlib.import_module(mod_name)
        if hasattr(mod, 'run'):
            return mod.run(user_id, user_text, history)
    except Exception:
        return None
    return None

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
    # Inicializar Gemini com o modelo persistido na tabela configuracoes (ou env)
    model_name = get_gemini_model_from_db()
    init_gemini_from_model_name(model_name)
    logger.info("System prompt ativo: %s", get_system_prompt())
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado no .env — abortando.")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("🚀 Sofia Ativa com Gemini! (Pressione Ctrl+C para parar)")
    # Start Stripe webhook server in background thread (if Flask available)
    try:
        t = threading.Thread(target=start_stripe_webhook_server, daemon=True)
        t.start()
        logger.info('Stripe webhook server thread started')
    except Exception:
        logger.exception('Não foi possível iniciar o servidor de webhooks Stripe')
    # Garantir que existe um event loop associado ao thread principal (compatibilidade com Python >=3.10+)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application.run_polling()

if __name__ == '__main__':
    main()
