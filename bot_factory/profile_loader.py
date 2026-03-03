"""
profile_loader.py — Lê todos os dados do cliente no DB e monta um perfil rico.
"""
import sqlite3
import json
import os
from typing import Optional

DB_PATH = os.getenv("DB_NAME", "agencia_autovenda.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def load_client_profile(user_id: str) -> dict:
    """
    Retorna um dicionário completo com TODOS os dados do cliente disponíveis no DB.
    Cruza assinaturas + onboarding_data + historico (resumido).
    """
    profile = {
        "user_id": user_id,
        "plano": None,
        "nicho": None,
        "plataforma": None,
        "nome_cliente": None,
        "valor_mensal": 0.0,
        # Dados de onboarding
        "empresa_nome": None,
        "horario_funcionamento": None,
        "tom_de_voz": "profissional e simpático",
        "transbordo_nome": None,
        "transbordo_contato": None,
        "site_ou_redes": None,
        "servicos_produtos": None,
        "faq_perguntas": None,
        # Secretaria
        "agenda_servicos": None,
        "agenda_email_google": None,
        "agenda_politica_cancel": None,
        "agenda_max_dia": None,
        "agenda_intervalo_min": None,
        # Ecossistema
        "crm_atual": None,
        "equipe_estrutura": None,
        "redes_integrar": None,
        "metricas_dashboard": None,
        "regras_escalacao": None,
        # Credenciais de plataforma
        "telegram_bot_token": None,
        "telegram_bot_username": None,
        "meta_phone_number_id": None,
        "meta_whatsapp_token": None,
        "meta_webhook_verify_token": None,
        # Extras do onboarding novo schema
        "whatsapp_contato": None,
        "website_cliente": None,
        "objetivos_ia": None,
        "status_configuracao": None,
    }

    conn = _conn()
    cur = conn.cursor()

    # ── Dados de assinaturas ──────────────────────────────────────
    cur.execute("SELECT * FROM assinaturas WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        d = dict(row)
        profile["plano"]         = d.get("plano") or d.get("plan")
        profile["nicho"]         = d.get("nicho")
        profile["plataforma"]    = d.get("plataforma")
        profile["nome_cliente"]  = d.get("nome")
        profile["valor_mensal"]  = d.get("valor_mensal", 0.0)

    # ── Dados de onboarding_data ──────────────────────────────────
    cur.execute("SELECT * FROM onboarding_data WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        d = dict(row)
        # Tenta ler dados_json (schema antigo rico)
        dados_json = d.get("dados_json")
        if dados_json:
            try:
                dados = json.loads(dados_json)
                for key in profile:
                    if key in dados and dados[key]:
                        profile[key] = dados[key]
            except Exception:
                pass

        # Schema atual do DB (campos diretos)
        for key in ["whatsapp_contato", "website_cliente", "objetivos_ia", "status_configuracao"]:
            if d.get(key):
                profile[key] = d[key]

        # Plataforma pode estar no onboarding também
        if d.get("plataforma") and not profile["plataforma"]:
            profile["plataforma"] = d["plataforma"]
        if d.get("plano") and not profile["plano"]:
            profile["plano"] = d["plano"]

    # ── Empresa nome — fallback para nome do cliente ──────────────
    if not profile["empresa_nome"]:
        profile["empresa_nome"] = profile["nome_cliente"] or f"Empresa do Cliente {user_id[:6]}"

    # ── Infere nicho pelo objetivos_ia se não veio de assinaturas ─
    if not profile["nicho"] and profile["objetivos_ia"]:
        profile["nicho"] = _infer_niche(profile["objetivos_ia"])

    # ── Plataforma default ─────────────────────────────────────────
    if not profile["plataforma"]:
        profile["plataforma"] = "telegram"

    # ── Plano default ─────────────────────────────────────────────
    if not profile["plano"]:
        profile["plano"] = "flash"

    conn.close()
    return profile


def _infer_niche(text: str) -> str:
    """Inferência rápida de nicho por palavras-chave."""
    t = text.lower()
    mapping = [
        ("clinica_estetica", ["estetica", "beleza", "spa", "depilacao", "botox"]),
        ("clinica_saude",    ["saude", "medico", "clinica", "dentista", "fisio", "psicologo"]),
        ("restaurante",      ["restaur", "comida", "delivery", "lanche", "pizza", "bar"]),
        ("ecommerce",        ["loja", "produto", "venda online", "ecommerce", "shop"]),
        ("imobiliaria",      ["imovel", "imobili", "aluguel", "corretor", "apartamento"]),
        ("educacao",         ["escola", "curso", "educacao", "treinamento", "aula"]),
        ("automotivo",       ["auto", "carro", "mecanica", "oficina", "veiculo"]),
        ("servicos",         ["servico", "consultoria", "agencia", "marketing", "contabil"]),
        ("varejo",           ["varejo", "loja fisica", "mercado", "farmacia"]),
    ]
    for nicho, keywords in mapping:
        if any(k in t for k in keywords):
            return nicho
    return "servicos"  # fallback genérico
