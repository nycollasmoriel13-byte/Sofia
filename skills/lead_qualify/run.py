import re
from typing import List, Tuple, Optional


def _extract_volume(text: str) -> Optional[int]:
    # Procura por números explícitos
    nums = re.findall(r"(\d{1,4})", text)
    if nums:
        # usa o primeiro número sensato como estimativa
        try:
            v = int(nums[0])
            return v
        except Exception:
            pass
    # procura faixas comuns (em palavras)
    text_l = text.lower()
    if "pouco" in text_l or "baixo" in text_l or "menos de 10" in text_l or "<10" in text_l:
        return 5
    if "muitos" in text_l or "muito" in text_l or "mais de 50" in text_l or ">50" in text_l:
        return 100
    if "10-50" in text_l or "entre 10 e 50" in text_l:
        return 30
    return None


def _detect_niche(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    # heurística simples: procura palavras-chave típicas
    text_l = text.lower()
    niches = [
        ("restaurante", ["restaur", "bar", "café", "delivery"]),
        ("ecommerce", ["loja", "ecommerce", "shop", "produto"]),
        ("imobiliária", ["imobili", "imóvel", "corretor"]),
        ("automotivo", ["oficina", "carro", "automotivo"]),
        ("saúde/estética", ["clínica", "estética", "consultório", "beleza"]),
        ("educação", ["escola", "curso", "educa"])
    ]
    for name, keys in niches:
        for k in keys:
            if k in text_l:
                return name
    # buscar no histórico caso não esteja no texto atual
    for _, msg in reversed(history[-6:]):
        ml = msg.lower()
        for name, keys in niches:
            for k in keys:
                if k in ml:
                    return name
    return None


def _detect_pain(text: str) -> Optional[str]:
    t = text.lower()
    if "demora" in t or "atendimento lento" in t or "tempo" in t:
        return "demora no atendimento"
    if "perda" in t or "perdemos" in t or "nao responde" in t or "não responde" in t:
        return "perda de vendas por falta de resposta"
    if "agendamento" in t or "agenda" in t:
        return "necessidade de agendamento"
    return None


def _recommendation_from_volume(v: Optional[int], pain: Optional[str]) -> Tuple[str, str]:
    # retorna (plano_recomendado, rationale)
    if v is None:
        # sem dados suficientes: pedir estimativa
        return ("Solicitar estimativa", "Pedir ao cliente uma estimativa de leads por dia (<10, 10-50, >50).")
    if v < 10:
        return ("Plano Flash", "Volume baixo — solução leve e rápida com automações pré-configuradas.")
    if v <= 50:
        # caso haja ponto de dor forte sobre agendamento
        if pain == "necessidade de agendamento":
            return ("Secretária Virtual (Plano Médio)", "Volume médio e necessidade de agendamento — automatizar agendamento e triagem.")
        return ("Plano Profissional", "Volume médio — automações híbridas com roteamento e fallback humano.")
    # v > 50
    return ("Ecossistema / Secretária Virtual (Enterprise)", "Alto volume — recomenda-se um ecossistema integrado com secretária virtual e filas.")


def run(user_id: str, user_text: str, history: List[Tuple[str, str]]) -> dict:
    """Deterministic hook for lead qualification.

    Returns structured JSON with keys:
      - status: 'ok'|'missing'|'error'
      - data: {niche, volume, pain, plan, rationale, next_steps}
      - missing: [fields]
    """
    try:
        combined = user_text + " \n " + " \n ".join([m for _, m in history[-6:]])
        niche = _detect_niche(user_text, history) or None
        volume = _extract_volume(combined)

        missing = []
        if not niche:
            missing.append('niche')
        if volume is None:
            missing.append('volume')
        if missing:
            return {"status": "missing", "missing": missing}

        pain = _detect_pain(combined) or None
        plan, rationale = _recommendation_from_volume(volume, pain)

        vol_str = str(volume) + " leads/dia" if volume is not None else None

        next_steps = []
        if volume is None:
            next_steps.append("Pedir estimativa de leads por dia: <10, 10-50, >50.")
        if plan.startswith("Plano Flash"):
            next_steps.append("Apresentar resumo do Plano Flash e coletar contato para ativação rápida.")
        if "Secretária" in plan or "Ecossistema" in plan:
            next_steps.append("Agendar demonstração técnica para integração e filas.")
        if pain == "demora no atendimento":
            next_steps.append("Sugerir templates de respostas rápidas e roteamento para humano se tempo de espera > X.")
        if not next_steps:
            next_steps.append("Confirmar interesse e agendar follow-up comercial.")

        data = {
            "niche": niche,
            "volume": volume,
            "volume_str": vol_str,
            "pain": pain,
            "plan": plan,
            "rationale": rationale,
            "next_steps": next_steps
        }
        if volume is not None and volume > 50:
            data['escalation'] = 'recomendar contato com equipe técnica para arquitetura e SLAs'

        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == '__main__':
    # Teste rápido quando executado diretamente
    sample = run('test_user', 'Tenho interesse — somos um restaurante e recebemos 30 leads por dia, temos demora no atendimento', [('user','Olá')])
    print(sample)
