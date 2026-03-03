# Brand Identity Skill
import re

VEHICLE_WORDS = ['carro', 'veiculo', 'comprar carro', 'seminovo', 'concessionaria', 'automovel', 'moto', 'caminhao', 'pecas auto']
COMPETITORS = ['manychat', 'chatfuel', 'botmaker', 'take blip', 'blip', 'zenvia', 'respond.io', 'wati', 'zappy', 'botconversa', 'leadster', 'octadesk']

CORRECTION_RESPONSES = {
    'vehicle': ('Haha, essa confusao e super comum -- mas a gente nao vende carros! Auto aqui vem de automacao. Qual negocio voce quer automatizar?'),
    'competitor': ('Entendo que voce conhece outras opcoes! Nossa IA tem memoria de longo prazo e integracao financeira -- algo raro. O que o servico atual nao resolve pra voce?'),
}

def run(user_id, user_text, history):
    t = user_text.lower()
    for word in VEHICLE_WORDS:
        if word in t:
            return CORRECTION_RESPONSES['vehicle']
    for comp in COMPETITORS:
        if comp in t:
            return CORRECTION_RESPONSES['competitor']
    return None
