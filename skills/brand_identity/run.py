from typing import List, Tuple, Optional
import re


def _mentions_vehicle(text: str) -> bool:
    t = text.lower()
    # detect common vehicle-related words combined with 'auto'
    vehicle_terms = ['carro', 'carros', 'veículo', 'veiculos', 'veículo', 'carroceria']
    if 'auto' in t:
        # if 'auto' appears near vehicle term
        for v in vehicle_terms:
            if v in t:
                return True
        # also if user explicitly asks to buy/ven(d)er
        if any(w in t for w in ['comprar', 'vender', 'venda', 'preço do carro', 'preço carro']):
            return True
    return False


def _mentions_competitor(text: str) -> bool:
    t = text.lower()
    keywords = ['concorr', 'outra agência', 'outras agências', 'competidor', 'agência concorrente', 'agencia concorrente']
    return any(k in t for k in keywords)


def run(user_id: str, user_text: str, history: List[Tuple[str, str]]) -> Optional[str]:
    """Deterministic guard hook: returns a short correction or emphasis string when brand rules apply.

    Returns a short Portuguese string to be appended to the LLM reply, or None.
    """
    try:
        combined = user_text + '\n' + '\n'.join([m for _, m in history[-6:]])

        # 1) Vehicle confusion
        if _mentions_vehicle(combined):
            return "Auto vem de Automático! Eu automatizo processos, não vendo veículos. 🚫🚗"

        # 2) Competitor mention -> emphasize differential
        if _mentions_competitor(combined):
            return "Nossa IA tem memória de longo prazo e integração nativa com o seu financeiro."

        # 3) Ensure persona name reminder (non-intrusive)
        # If user explicitly asks 'quem é você' or similar, ensure name Sofia appears
        if any(p in combined.lower() for p in ['quem é você', 'quem e você', 'como se chama', 'qual é seu nome', 'qual o seu nome']):
            return "Meu nome é Sofia — sou sua consultora de automação. 🤝"

        return None
    except Exception:
        return None


if __name__ == '__main__':
    print(run('u1', 'Vocês vendem carros? Quero comprar um carro.', []))
    print(run('u1', 'O que acha da concorrência? as outras agências são melhores?', []))
    print(run('u1', 'Quem é você?', []))
