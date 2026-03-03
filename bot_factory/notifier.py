"""
notifier.py — Envia mensagem ao cliente via Telegram quando o bot ficar pronto.

Correções aplicadas:
- Sem parse_mode em mensagens de erro (evita crash por chars especiais em user_ids, stacktraces, etc.)
- Rate-limit: 1 notificação de erro igual por (user_id, chave) a cada 1 hora — sem spam
- Fallback automático sem Markdown se Telegram rejeitar a mensagem
"""
import os
import re
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SOFIA_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "8496188581:AAHhCiolHCHFbPz_XwW3rzeK4Fac6FIA7G8")
TELEGRAM_API = f"https://api.telegram.org/bot{SOFIA_TOKEN}/sendMessage"

# Cache de rate-limit: {(user_id, chave): datetime_ultimo_envio}
_last_notified: dict = {}
RATE_LIMIT_HOURS = 1


def _should_notify(user_id: str, key: str) -> bool:
    """Retorna True somente se passou 1h desde a última notificação igual."""
    cache_key = (user_id, key)
    last = _last_notified.get(cache_key)
    if last and datetime.now() - last < timedelta(hours=RATE_LIMIT_HOURS):
        return False
    _last_notified[cache_key] = datetime.now()
    return True


def _send(chat_id: str, text: str, parse_mode: str = None) -> bool:
    """Envia mensagem; se Telegram rejeitar por entity, reenvia sem parse_mode."""
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if resp.ok:
            return True
        logger.warning(f"[Notifier] Falha ({chat_id}): {resp.text}")
        # Fallback: tenta sem Markdown se falhou por parse de entidade
        if parse_mode and ("parse entities" in resp.text.lower() or "can't parse" in resp.text.lower()):
            resp2 = requests.post(TELEGRAM_API, json={"chat_id": chat_id, "text": text}, timeout=10)
            return resp2.ok
    except Exception as e:
        logger.error(f"[Notifier] Exceção ({chat_id}): {e}")
    return False


def notify_client(user_id: str, profile: dict, bot_username: str = None, error: str = None):
    """
    Notifica o cliente sobre status do bot.
    Erros: sem Markdown (evita crash com chars especiais), com rate-limit.
    """
    empresa = profile.get("empresa_nome", "sua empresa")

    if error:
        rate_key = f"error:{error[:50]}"
        if not _should_notify(user_id, rate_key):
            return
        # Sem parse_mode — mensagem de erro pode conter qualquer caractere
        text = (
            f"Atencao, {empresa}\n\n"
            f"Houve um problema na configuracao do seu bot:\n{error}\n\n"
            f"Nossa equipe foi notificada e entrara em contato. "
            f"Para suporte imediato, responda aqui."
        )
        ok = _send(user_id, text)
    else:
        if not _should_notify(user_id, "success"):
            return
        bot_mention = f"@{bot_username}" if bot_username else "seu bot"
        text = (
            f"Seu bot esta ativo! {empresa}\n\n"
            f"Bot: {bot_mention}\n"
            f"Plano: {(profile.get('plano') or '').title()}\n\n"
            f"Seus clientes ja podem usar o assistente virtual. Qualquer duvida, e so chamar!"
        )
        ok = _send(user_id, text)

    if ok:
        logger.info(f"[Notifier] {user_id} notificado ({'erro' if error else 'sucesso'}).")


def notify_owner(message: str):
    """
    Notifica o dono da agência sobre eventos do factory.
    Rate-limit de 1h por mensagem distinta para evitar spam.
    Caracteres especiais do Markdown são removidos automaticamente.
    """
    owner_id = os.getenv("OWNER_TELEGRAM_ID")
    if not owner_id:
        return

    rate_key = f"owner:{message[:60]}"
    if not _should_notify("__owner__", rate_key):
        return

    # Strip de qualquer Markdown / chars especiais do Telegram
    clean = re.sub(r"[_*`\[\]()~>#+=|{}.!\-]", " ", message)
    text = f"Bot Factory\n\n{clean}"
    _send(owner_id, text)

