"""
plan_resolver.py — Mapeia o plano do cliente para features e limites permitidos.
"""

# Features disponíveis por plano (hierárquico — ecossistema inclui tudo)
PLAN_FEATURES = {
    "flash": {
        "max_skills_nicho": 1,
        "agendamento": False,
        "crm": False,
        "multi_atendente": False,
        "dashboard_cliente": False,
        "relatorios": False,
        "memoria_longo_prazo": False,
        "integracao_google_agenda": False,
        "max_mensagens_dia": 30,
        "skills_base": True,
        "descricao": "Atendimento Flash — FAQ, menu e triagem 24h",
    },
    "secretaria": {
        "max_skills_nicho": 3,
        "agendamento": True,
        "crm": False,
        "multi_atendente": False,
        "dashboard_cliente": False,
        "relatorios": False,
        "memoria_longo_prazo": True,
        "integracao_google_agenda": True,
        "max_mensagens_dia": 100,
        "skills_base": True,
        "descricao": "Secretária Virtual — agendamento, triagem e Google Agenda",
    },
    "secretaria_virtual": None,  # alias → resolvido abaixo
    "ecossistema": {
        "max_skills_nicho": 999,
        "agendamento": True,
        "crm": True,
        "multi_atendente": True,
        "dashboard_cliente": True,
        "relatorios": True,
        "memoria_longo_prazo": True,
        "integracao_google_agenda": True,
        "max_mensagens_dia": 9999,
        "skills_base": True,
        "descricao": "Ecossistema Completo — IA com memória, CRM e dashboards",
    },
    "ecossistema_completo": None,  # alias → resolvido abaixo
}

# Resolve aliases
PLAN_FEATURES["secretaria_virtual"] = PLAN_FEATURES["secretaria"]
PLAN_FEATURES["ecossistema_completo"] = PLAN_FEATURES["ecossistema"]


def resolve(plano: str) -> dict:
    """Retorna as features para o plano dado. Usa 'flash' como fallback."""
    key = (plano or "flash").lower().strip().replace(" ", "_").replace("-", "_")
    features = PLAN_FEATURES.get(key)
    if features is None:
        features = PLAN_FEATURES["flash"]
    return features


def get_plan_label(plano: str) -> str:
    """Retorna nome humano do plano."""
    f = resolve(plano)
    return f.get("descricao", plano)


def plan_allows(plano: str, feature: str) -> bool:
    """Verifica se uma feature está disponível no plano."""
    return bool(resolve(plano).get(feature, False))
