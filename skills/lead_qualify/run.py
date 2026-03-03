"""
Skill: Lead Qualify — Qualificacao inteligente com tratamento de objecoes.
"""
import re
from typing import List, Tuple, Optional


NICHES = [
    ("clinica_estetica", ["estetica", "clinica", "spa", "beleza", "botox", "depilacao"]),
    ("clinica_saude", ["clinica", "consultorio", "medico", "dentista", "psicologo", "fisioterapia", "saude"]),
    ("restaurante", ["restaur", "bar", "cafe", "delivery", "lanchonete", "pizzaria", "hamburger"]),
    ("ecommerce", ["loja", "ecommerce", "shop", "produto", "venda online", "marketplace"]),
    ("imobiliaria", ["imobili", "imovel", "corretor", "aluguel", "compra de casa", "apartamento"]),
    ("automotivo", ["oficina", "mecanica", "auto pecas", "carro", "manutencao veic"]),
    ("educacao", ["escola", "curso", "educacao", "treinamento", "colegio", "universidade", "ead"]),
    ("servicos", ["servico", "consultoria", "agencia", "marketing", "contabilidade", "advocacia", "financeiro"]),
    ("varejo", ["loja fisica", "varejo", "mercado", "farmacia", "supermercado"]),
]

OBJECTIONS = {
    "preco": ["caro", "muito caro", "preco alto", "nao tenho", "orcamento", "investimento alto", "fora do meu", "nao cabe", "barato"],
    "tempo": ["nao tenho tempo", "depois", "semana que vem", "mais tarde", "agora nao", "ocupado"],
    "duvida": ["nao sei se", "nao tenho certeza", "preciso pensar", "vou pensar", "deixa eu ver", "vou analisar"],
    "concorrente": ["ja tenho", "uso outro", "tenho um bot", "ja contratei", "outra empresa", "concorrente"],
    "desconfianca": ["nao sei", "funciona mesmo", "e golpe", "confiavel", "e serio", "como funciona"],
    "meta_taxa": ["taxa meta", "taxa da meta", "taxa api", "api cara", "pagar meta", "cobrado pela meta",
                  "taxa whatsapp", "custo de mensagem", "pagar por mensagem", "cobrado por mensagem"],
}

PLATFORM_SIGNALS = {
    "whatsapp": ["whatsapp", "wpp", "zap", "whats", "wts"],
    "telegram": ["telegram", "tg", "telgram"],
}


def _detect_niche(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = (text + " " + " ".join([m for _, m in history[-8:]])).lower()
    combined = re.sub(r'[áàãâä]','a', re.sub(r'[éèê]','e', re.sub(r'[íì]','i',
        re.sub(r'[óòõô]','o', re.sub(r'[úù]','u', combined)))))
    for name, keys in NICHES:
        for k in keys:
            if k in combined:
                return name
    return None


def _extract_volume(text: str, history: List[Tuple[str, str]]) -> Optional[int]:
    combined = text + " " + " ".join([m for _, m in history[-6:]])
    nums = re.findall(r"\b(\d{1,4})\b", combined)
    for n in nums:
        v = int(n)
        if 1 <= v <= 5000:
            return v
    t = combined.lower()
    if any(w in t for w in ["poucos", "pouco", "menos de 10", "menos de dez", "<10"]):
        return 5
    if any(w in t for w in ["muitos", "muito", "mais de 50", ">50", "centenas"]):
        return 100
    if any(w in t for w in ["10 a 50", "10-50", "entre 10 e 50", "dezenas"]):
        return 30
    return None


def _detect_pain(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = (text + " " + " ".join([m for _, m in history[-6:]])).lower()
    if any(w in combined for w in ["demora", "lento", "tempo de resposta", "demorado", "esperando"]):
        return "demora_no_atendimento"
    if any(w in combined for w in ["perder", "perdemos", "nao respondo", "nao responde", "sem resposta", "mensagem perdida"]):
        return "perda_de_vendas"
    if any(w in combined for w in ["agendar", "agendamento", "marcar", "agenda", "horario"]):
        return "agendamento"
    if any(w in combined for w in ["equipe pequena", "so eu", "sozinho", "sem funcionario"]):
        return "equipe_reduzida"
    if any(w in combined for w in ["fora do horario", "madrugada", "depois das", "fim de semana"]):
        return "atendimento_fora_horario"
    return None


def _detect_objection(text: str) -> Optional[str]:
    t = text.lower()
    t = re.sub(r'[\u00e1\u00e0\u00e3\u00e2\u00e4]','a', re.sub(r'[\u00e9\u00e8\u00ea]','e', re.sub(r'[\u00ed\u00ec]','i',
        re.sub(r'[\u00f3\u00f2\u00f5\u00f4]','o', re.sub(r'[\u00fa\u00f9]','u', t)))))
    for obj_type, keywords in OBJECTIONS.items():
        for kw in keywords:
            if kw in t:
                return obj_type
    return None


def _detect_platform_preference(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = (text + " " + " ".join([m for _, m in history[-6:]])).lower()
    for platform, signals in PLATFORM_SIGNALS.items():
        for sig in signals:
            if sig in combined:
                return platform
    return None


def _plan_from_data(volume: Optional[int], pain: Optional[str], niche: Optional[str]) -> Tuple[str, str, float]:
    if volume is None:
        return ("Atendimento Flash", "Plano inicial ideal para quem esta comecando a automatizar.", 159.99)
    if volume <= 10:
        return ("Atendimento Flash", f"Volume baixo ({volume} contatos/dia) — o Flash automatiza FAQ e menu, liberando horas do seu dia.", 159.99)
    if volume <= 50 or pain in ("agendamento",):
        if pain == "agendamento":
            reason = f"Volume medio com necessidade de agendamento — a Secretaria Virtual agenda 24h/dia integrada ao seu Google Agenda."
        else:
            reason = f"Volume de {volume} contatos/dia — a Secretaria Virtual faz triagem, responde e ainda agenda automaticamente."
        return ("Secretaria Virtual", reason, 559.99)
    return ("Ecossistema Completo",
            f"Alto volume ({volume} contatos/dia) — o Ecossistema usa IA com memoria, CRM e dashboards para nao perder nenhuma venda.",
            1499.99)


OBJECTION_RESPONSES = {    "meta_taxa": (
        "Faz todo sentido querer entender isso! A taxa da API do WhatsApp e cobrada diretamente pela Meta "
        "-- nao por nos. Funciona assim: voce paga a Meta por cada conversa iniciada, geralmente entre "
        "R$ 0,03 e R$ 0,12 por conversa (dependendo do tipo e do pais). "
        "E bem acessivel -- uma loja com 50 conversas por dia gasta em media R$ 3 a R$ 6 por dia nessa taxa. "
        "Quer uma alternativa sem custo de API? Podemos fazer no Telegram, que e totalmente gratuito. "
        "Qual faz mais sentido pro seu perfil de clientes?"
    ),    "preco": (
        "Entendo a preocupacao com o custo! Posso te perguntar: hoje, quantas horas voce ou sua equipe "
        "gastam respondendo mensagens manualmente por semana? Faco a conta do ROI pra voce — normalmente "
        "o plano se paga com 3 a 5 horas de trabalho manual economizadas. "
        "E o Flash sai a R$ 5,30 por dia. Vale cada centavo comparado ao tempo perdido."
    ),
    "tempo": (
        "Sem problema nenhum! Posso deixar tudo pre-configurado aqui, "
        "e quando voce tiver 5 minutinhos e so confirmar. "
        "Quanto tempo voce tem hoje mais ou menos?"
    ),
    "duvida": (
        "Faz todo sentido querer ter certeza antes de decidir! "
        "Me conta o que ainda nao ficou claro — prometo ser direta e te dizer se faz sentido ou nao pro seu caso."
    ),
    "concorrente": (
        "Entendo! O que nos diferencia bastante e que nossa IA tem memoria de longo prazo — "
        "ela lembra do historico de cada cliente — alem de integracao nativa com financeiro. "
        "O que o servico atual nao resolve que te fez buscar outra opcao?"
    ),
    "desconfianca": (
        "E boa voce perguntar! Somos uma agencia especializada em automacao de atendimento pelo WhatsApp e Telegram. "
        "Posso te mostrar como funciona na pratica -- sem compromisso. "
        "Qual o maior gargalo no seu atendimento hoje?"
    ),
}


def run(user_id: str, user_text: str, history: List[Tuple[str, str]]) -> dict:
    try:
        niche = _detect_niche(user_text, history)
        volume = _extract_volume(user_text, history)
        pain = _detect_pain(user_text, history)
        objection = _detect_objection(user_text)
        platform_pref = _detect_platform_preference(user_text, history)

        if objection:
            return {
                "status": "objection",
                "objection_type": objection,
                "platform_preference": platform_pref,
                "suggested_response": OBJECTION_RESPONSES.get(objection, ""),
                "instruction": (
                    f"O cliente demonstrou objecao do tipo '{objection}'. "
                    f"Responda de forma empatica e natural usando esta abordagem como base: "
                    f"'{OBJECTION_RESPONSES.get(objection, '')}' -- adapte ao contexto da conversa, nao copie roboticamente."
                    + (f" Cliente parece preferir {platform_pref.title()}." if platform_pref else "")
                )
            }

        missing = []
        if not niche:
            missing.append("niche")
        if volume is None:
            missing.append("volume")

        if missing:
            next_question_map = {
                "niche": "Qual e o ramo da sua empresa? (ex: restaurante, clinica, ecommerce, imobiliaria...)",
                "volume": "Quantas mensagens ou pedidos voces recebem por dia, aproximadamente? (pode ser uma estimativa)",
            }
            next_field = missing[0]
            return {
                "status": "missing",
                "missing": missing,
                "next_question": next_question_map[next_field],
                "instruction": (
                    f"Ainda nao temos dados suficientes para qualificar. Falta: {', '.join(missing)}. "
                    f"Faca APENAS esta pergunta de forma natural: '{next_question_map[next_field]}' — "
                    "intercale com um comentario empatico sobre o que o cliente ja disse."
                )
            }

        plan, rationale, price = _plan_from_data(volume, pain, niche)
        niche_display = niche.replace("_", " ").title()
        pain_display = (pain or "nao identificado").replace("_", " ")

        return {
            "status": "ok",
            "data": {
                "niche": niche_display,
                "volume": volume,
                "volume_str": f"{volume} contatos/dia",
                "pain": pain_display,
                "plan": plan,
                "price": price,
                "rationale": rationale,
                "platform_preference": platform_pref,
            },
            "instruction": (
                f"QUALIFICACAO CONCLUIDA! Dados do lead:\n"
                f"- Nicho: {niche_display}\n"
                f"- Volume: {volume} contatos/dia\n"
                f"- Dor principal: {pain_display}\n"
                f"- Plano recomendado: {plan} (R$ {price:.2f}/mes)\n"
                f"- Justificativa: {rationale}\n"
                + (f"- Plataforma preferida detectada: {platform_pref.title()}\n" if platform_pref else "") +
                "\nApresente o plano de forma personalizada e consultiva -- mencione o nicho e o problema especifico dele. "
                "Ao final, pergunte se quer ver como funciona na pratica ou se prefere fechar ja. "
                "NAO liste os 3 planos de uma vez -- apresente apenas o recomendado com confianca."
            )
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
