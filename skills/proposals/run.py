import re
import os
import sqlite3
import stripe
from dotenv import load_dotenv
from typing import List, Tuple, Optional, Union

load_dotenv()

PLANS = {
    'flash': {'title': 'Atendimento Flash', 'price': 159.99, 'slug': 'flash'},
    'secretaria': {'title': 'Secretária Virtual', 'price': 559.99, 'slug': 'secretaria_virtual'},
    'ecossistema': {'title': 'Ecossistema Completo', 'price': 1499.99, 'slug': 'ecossistema_completo'},
}


def _detect_plan(text: str) -> Optional[dict]:
    t = text.lower()
    if 'flash' in t or 'atendimento flash' in t:
        return PLANS['flash']
    if 'secret' in t or 'secretária' in t or 'secretaria' in t:
        return PLANS['secretaria']
    if 'ecossistema' in t or 'ecossist' in t:
        return PLANS['ecossistema']
    if '159' in t or '159,99' in t:
        return PLANS['flash']
    if '559' in t or '559,99' in t:
        return PLANS['secretaria']
    if '1499' in t or '1.499' in t or '1499,99' in t:
        return PLANS['ecossistema']
    return None


def _extract_email(text: str) -> Optional[str]:
    m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return m.group(0) if m else None


def _extract_name(text: str) -> Optional[str]:
    m = re.search(r"nome[:\s-]*([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"meu nome é\s+([A-ZÀ-Ÿ][\w\s]+)", text, re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    m3 = re.search(r"([A-ZÀ-Ÿ][a-zà-ÿ]+\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)", text)
    if m3:
        return m3.group(1).strip()
    return None


def create_stripe_checkout(user_id: str, plan_name: str, email: str) -> dict:
    """Cria uma sessão de checkout Stripe (subscription) e atualiza a tabela `assinaturas` como 'aguardando_pagamento'.

    Retorna dict: {'url': session.url, 'status': 'success'} ou {'error': ..., 'status': 'failed'}
    """
    try:
        load_dotenv()
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

        price_map = {
            "Flash": os.getenv("STRIPE_PRICE_ATENDIMENTO"),
            "Secretaria": os.getenv("STRIPE_PRICE_SECRETARIA"),
            "Eco": os.getenv("STRIPE_PRICE_ECO")
        }

        price_id = price_map.get(plan_name)
        if not price_id:
            return {"error": "Plano inválido", "status": "failed"}

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            customer_email=email,
            client_reference_id=user_id,
            success_url=os.getenv('SUCCESS_URL', ''),
            cancel_url=os.getenv('CANCEL_URL', ''),
        )

        # Atualiza o status no banco local para 'aguardando_pagamento'
        try:
            conn = sqlite3.connect(os.getenv('DB_NAME', 'agencia_autovenda.db'))
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE assinaturas SET status = 'aguardando_pagamento', plano = ? WHERE user_id = ?",
                (plan_name, user_id)
            )
            conn.commit()
            conn.close()
        except Exception:
            # não bloquear a resposta se a atualização do DB falhar
            pass

        sess_url = getattr(session, 'url', None) or (session.get('url') if isinstance(session, dict) else None)
        return {"url": sess_url, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _build_payment_payload(plan: dict, name: str, email: str) -> dict:
    amount_cents = int(round(plan['price'] * 100))
    return {
        'plan': plan['slug'],
        'title': plan['title'],
        'amount_cents': amount_cents,
        'currency': 'brl',
        'customer_email': email,
        'customer_name': name,
    }


def run(user_id: str, user_text: str, history: List[Tuple[str, str]]) -> Optional[dict]:
    """Deterministic hook for proposals: returns structured JSON.

    Returns dict with:
      - status: 'ok'|'missing'|'failed'
      - plan: {title, price}
      - missing: [fields]
      - payment: {'url', 'status'} when available
      - error: message when failed
    """
    try:
        combined = user_text + "\n" + "\n".join([m for _, m in history[-6:]])
        plan = _detect_plan(combined)
        if not plan:
            return None

        name = _extract_name(combined)
        email = _extract_email(combined)

        missing = []
        if not name:
            missing.append('name')
        if not email:
            missing.append('email')
        if missing:
            return {"status": "missing", "missing": missing}

        payload = _build_payment_payload(plan, name, email)

        plan_key = 'Flash' if plan['slug'] == 'flash' else ('Secretaria' if 'secretaria' in plan['slug'] else 'Eco')
        stripe_result = create_stripe_checkout(user_id, plan_key, email)

        if stripe_result.get('status') == 'success':
            return {
                "status": "ok",
                "plan": {"title": payload['title'], "price": plan['price']},
                "payment": stripe_result,
                "payload": payload
            }

        # fallback structured response when Stripe failed
        return {
            "status": "failed",
            "plan": {"title": payload['title'], "price": plan['price']},
            "payment": stripe_result,
            "payload": payload
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == '__main__':
    # Testes rápidos
    print(run('u1', 'Quero contratar Secretária Virtual', []))
    print('---')
    print(run('u1', 'Quero contratar Secretária Virtual. Nome: João Silva, Email: joao@example.com', []))
