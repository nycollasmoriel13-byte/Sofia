"""
generator.py — Gera o código Python completo do bot do cliente e o salva em disco.
Usa Jinja2 para renderizar templates específicos por plano.
"""
import os
import json
import hashlib
from jinja2 import Environment, FileSystemLoader
from typing import List

FACTORY_DIR    = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR  = os.path.join(FACTORY_DIR, "templates")
CLIENTS_DIR    = os.path.join(os.path.dirname(FACTORY_DIR), "clients")


def _get_template_name(plano: str) -> str:
    plano_key = (plano or "flash").lower().strip().replace(" ", "_").replace("-", "_")
    mapping = {
        "flash": "bot_flash.py.jinja",
        "secretaria": "bot_secretaria.py.jinja",
        "secretaria_virtual": "bot_secretaria.py.jinja",
        "ecossistema": "bot_ecossistema.py.jinja",
        "ecossistema_completo": "bot_ecossistema.py.jinja",
    }
    return mapping.get(plano_key, "bot_flash.py.jinja")


def generate_bot(profile: dict, skills: List[str], system_prompt: str) -> dict:
    """
    Gera o bot.py e config.json do cliente e salva em clients/{user_id}/.
    Retorna dict com: bot_path, config_path, prompt_hash, user_id.
    """
    user_id = profile["user_id"]
    plano   = profile.get("plano", "flash")

    # Cria pasta do cliente
    client_dir = os.path.join(CLIENTS_DIR, user_id)
    os.makedirs(client_dir, exist_ok=True)

    # Carrega template Jinja2
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template_name = _get_template_name(plano)
    template = env.get_template(template_name)

    # Variáveis para o template
    groq_model = os.getenv("GROQ_MODEL_CLIENTS", "llama-3.3-70b-versatile")
    db_path    = os.path.abspath(os.getenv("DB_NAME", "agencia_autovenda.db"))

    context = {
        "user_id":        user_id,
        "empresa_nome":   profile.get("empresa_nome", "Empresa"),
        "plano":          plano,
        "plataforma":     profile.get("plataforma", "telegram"),
        "system_prompt":  system_prompt,
        "skills":         skills,
        "groq_model":     groq_model,
        "db_path":        db_path,
        # Credenciais de plataforma
        "telegram_token": profile.get("telegram_bot_token", ""),
        "telegram_username": profile.get("telegram_bot_username", ""),
        "meta_phone_id":  profile.get("meta_phone_number_id", ""),
        "meta_token":     profile.get("meta_whatsapp_token", ""),
        "meta_verify":    profile.get("meta_webhook_verify_token", ""),
        # Features do plano
        "has_agendamento":     profile.get("agenda_servicos") is not None,
        "agenda_email_google": profile.get("agenda_email_google", ""),
        # Info extra
        "transbordo_contato":  profile.get("transbordo_contato", ""),
        "factory_db_path":     db_path,
    }

    # Renderiza o bot
    bot_code = template.render(**context)

    # Salva bot.py
    bot_path = os.path.join(client_dir, "bot.py")
    with open(bot_path, "w", encoding="utf-8") as f:
        f.write(bot_code)

    # Salva config.json (metadados do bot)
    config = {
        "user_id":    user_id,
        "plano":      plano,
        "nicho":      profile.get("nicho"),
        "plataforma": profile.get("plataforma"),
        "empresa":    profile.get("empresa_nome"),
        "skills":     skills,
        "groq_model": groq_model,
        "db_path":    db_path,
        "telegram_bot_username": profile.get("telegram_bot_username", ""),
    }
    config_path = os.path.join(client_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # Hash do prompt para detectar mudanças futuras
    prompt_hash = hashlib.md5(system_prompt.encode()).hexdigest()

    return {
        "bot_path":    bot_path,
        "config_path": config_path,
        "prompt_hash": prompt_hash,
        "user_id":     user_id,
        "client_dir":  client_dir,
    }
