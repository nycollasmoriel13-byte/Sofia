"""
Skill: Proposals — Deteccao de plano, criacao de checkout Stripe, ROI, urgencia.
"""
import os
import re
from typing import Optional, Tuple, List

import stripe
from dotenv import load_dotenv
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

PLANS = {
    "flash": {
        "name": "Atendimento Flash",
        "price": 159.99,
        "price_id": os.getenv("STRIPE_PRICE_FLASH", ""),
        "description": "Bot de FAQ e menu 24h, resposta imediata, configuracao rapida",
        "roi": "Economize 2-3h/dia de atendimento manual — R$ 159,99/mes ou ~R$ 5,30/dia",
        "ideal_for": "negocios com ate 30 mensagens/dia que querem parar de responder manualmente",
    },
    "secretaria": {
        "name": "Secretaria Virtual",
        "price": 559.99,
        "price_id": os.getenv("STRIPE_PRICE_SECRETARIA", ""),
        "description": "IA com agendamento, triagem de clientes e integracao Google Agenda",
        "roi": "Agenda sozinha, sem voce tocar no celular — equivale a contratar uma secretaria por 10% do salario",
        "ideal_for": "negocios com 30-100 mensagens/dia e necessidade de agendamento ou triagem",
    },
    "ecossistema": {
        "name": "Ecossistema Completo",
        "price": 1499.99,
        "price_id": os.getenv("STRIPE_PRICE_ECOSSISTEMA", ""),
        "description": "IA com memoria, CRM integrado, multi-atendente e dashboards de conversao",
        "roi": "Media de R$ 8.000-15.000 em vendas recuperadas/mes para clientes com +100 leads/dia",
        "ideal_for": "negocios com alto volume, equipe de vendas ou multiplos atendentes",
    },
}

CLOSING_SIGNALS = ["sim", "quero", "combinado", "fechar", "assinar", "contratar", "pode ser", "bora", "ok",
                   "confirmo", "aceito", "vamos", "pode mandar", "manda o link", "me manda", "quero contratar",
                   "vou pegar", "fecha", "pode fechar", "fecha ai", "vou assinar"]

INTEREST_SIGNALS = ["qual o link", "como pago", "como contrato", "como assino", "ativar", "quero ver",
                    "quero comecar", "como começa", "como funciona o pagamento"]


def _detect_plan(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = (text + " " + " ".join([m for _, m in history[-10:]])).lower()
    combined = re.sub(r'[áàãâä]','a', re.sub(r'[éèê]','e', re.sub(r'[íì]','i',
        re.sub(r'[óòõô]','o', re.sub(r'[úù]','u', combined)))))
    if any(k in combined for k in ["ecossistema", "completo", "premium", "crm", "multi", "avancado"]):
        return "ecossistema"
    if any(k in combined for k in ["secretaria", "agenda", "agendamento", "triagem", "intermediario"]):
        return "secretaria"
    if any(k in combined for k in ["flash", "basico", "simples", "starter", "faq", "inicial"]):
        return "flash"
    return None


def _detect_closing(text: str) -> bool:
    t = text.lower()
    t = re.sub(r'[áàãâä]','a', re.sub(r'[éèê]','e', re.sub(r'[íì]','i',
        re.sub(r'[óòõô]','o', re.sub(r'[úù]','u', t)))))
    return any(sig in t for sig in CLOSING_SIGNALS)


def _detect_interest(text: str) -> bool:
    t = text.lower()
    return any(sig in t for sig in INTEREST_SIGNALS)


def _extract_email(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = text + " " + " ".join([m for _, m in history[-10:]])
    m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", combined)
    return m.group(0) if m else None


def _extract_name(text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    combined = text + " " + " ".join([m for _, m in history[-8:]])
    patterns = [
        r"(?:meu nome|me chamo|sou o|sou a)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        r"(?:nome[:\s]+)([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, combined)
        if m:
            return m.group(1).strip()
    return None


def create_stripe_checkout(plan_slug: str, email: str, name: str) -> Optional[str]:
    try:
        plan = PLANS.get(plan_slug)
        if not plan or not plan["price_id"]:
            return None
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": plan["price_id"], "quantity": 1}],
            mode="subscription",
            customer_email=email or None,
            metadata={"client_name": name or "", "plan": plan_slug},
            success_url=os.getenv("SUCCESS_URL", "https://agencia.com/sucesso"),
            cancel_url=os.getenv("CANCEL_URL", "https://agencia.com/cancelado"),
        )
        return session.url
    except Exception as e:
        print(f"[proposals] Stripe error: {e}")
        return None


def run(user_id: str, user_text: str, history: List[Tuple[str, str]], qualified_plan: Optional[str] = None) -> dict:
    try:
        plan_slug = qualified_plan or _detect_plan(user_text, history)
        is_closing = _detect_closing(user_text)
        is_interest = _detect_interest(user_text)
        email = _extract_email(user_text, history)
        name = _extract_name(user_text, history)

        if not plan_slug:
            return {"status": "no_plan"}

        plan = PLANS[plan_slug]
        result = {
            "status": "ok",
            "plan": plan_slug,
            "plan_name": plan["name"],
            "price": plan["price"],
            "roi": plan["roi"],
            "is_closing": is_closing,
            "is_interest": is_interest,
            "has_email": bool(email),
            "email": email,
            "name": name,
            "checkout_url": None,
            "instruction": "",
        }

        if is_closing or is_interest:
            if email:
                url = create_stripe_checkout(plan_slug, email, name or "")
                if url:
                    result["checkout_url"] = url
                    result["instruction"] = (
                        f"FECHAMENTO DETECTADO! Cliente quer o plano {plan['name']} (R$ {plan['price']:.2f}/mes).\n"
                        f"Link de pagamento gerado: {url}\n"
                        f"Instrucao: Envie o link de forma animada, parabenize a decisao, e diga que a ativacao "
                        f"ocorre em ate 24h apos o pagamento. Mencione que voce vai acompanhar pessoalmente."
                    )
                else:
                    result["instruction"] = (
                        f"Cliente quer fechar o plano {plan['name']} mas o link Stripe nao foi gerado. "
                        "Peca o e-mail para enviar manualmente a proposta."
                    )
            else:
                result["instruction"] = (
                    f"Cliente demonstrou interesse em fechar o plano {plan['name']} (R$ {plan['price']:.2f}/mes)! "
                    f"URGENTE: peca o e-mail para gerar o link de pagamento. Faca isso AGORA sem perder o momentum. "
                    f"Diga algo como: 'Otimo! So preciso do seu melhor e-mail para gerar o link de ativacao.'"
                )
        else:
            result["instruction"] = (
                f"Plano detectado: {plan['name']} (R$ {plan['price']:.2f}/mes).\n"
                f"ROI: {plan['roi']}\n"
                f"Ideal para: {plan['ideal_for']}\n"
                f"Nota de plataforma: {plan['platform_note']}\n"
                "Se ainda nao fez a proposta formal, apresente o plano com o ROI especifico, "
                "mencione a opcao de plataforma (WhatsApp com taxa Meta ou Telegram gratuito), "
                "explique a taxa Meta de forma tranquilizadora (centavos por conversa, pago por eles diretamente a Meta), "
                "mencione urgencia (vagas limitadas para ativacao esta semana) "
                "e termine com uma pergunta de fechamento direta: "
                "'Posso gerar o link de ativacao pra voce?'"
            )

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
