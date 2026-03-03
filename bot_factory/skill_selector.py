"""
skill_selector.py — Seleciona as skills certas da biblioteca com base em nicho + plano + aprendizado.
"""
import os
import json
from typing import List
from bot_factory.plan_resolver import resolve
from bot_factory.db_factory import get_skill_score, record_skill_usage

# Mapeamento nicho → skills disponíveis (name = pasta dentro de skills_library/)
NICHE_SKILLS = {
    "clinica_estetica": [
        "agendamento_estetica",
        "cardapio_servicos",
        "follow_up_pos_atendimento",
        "qualificacao_paciente",
    ],
    "clinica_saude": [
        "triagem_sintomas",
        "agendamento_saude",
        "lembretes_retorno",
        "plano_saude_info",
    ],
    "restaurante": [
        "cardapio_digital",
        "pedido_delivery",
        "reserva_mesa",
        "promocoes_diarias",
    ],
    "ecommerce": [
        "catalogo_produtos",
        "rastreio_pedido",
        "recuperacao_carrinho",
        "politica_troca",
    ],
    "imobiliaria": [
        "busca_imovel",
        "agendamento_visita",
        "qualificacao_comprador",
        "simulacao_financiamento",
    ],
    "educacao": [
        "info_cursos",
        "matricula_guiada",
        "suporte_aluno",
        "calendario_letivo",
    ],
    "automotivo": [
        "orcamento_servico",
        "agendamento_mecanica",
        "status_veiculo",
        "historico_manutencao",
    ],
    "servicos": [
        "briefing_projeto",
        "agendamento_consultoria",
        "proposta_automatica",
        "followup_orcamento",
    ],
    "varejo": [
        "consulta_estoque",
        "promocoes",
        "fidelidade_pontos",
        "horario_loja",
    ],
}

# Skills base — disponíveis para TODOS os planos/nichos
BASE_SKILLS = [
    "faq_responder",
    "horario_funcionamento",
    "captura_lead",
    "transbordo_humano",
]


def select_skills(nicho: str, plano: str) -> List[str]:
    """
    Retorna lista ordenada de skills selecionadas para o cliente.
    - Sempre inclui as skills base.
    - Adiciona skills do nicho até o limite do plano, priorizando pelo score de aprendizado.
    """
    features = resolve(plano)
    max_nicho = features.get("max_skills_nicho", 1)
    has_agenda = features.get("agendamento", False)

    # Skills base (sempre incluídas)
    selected = list(BASE_SKILLS)

    # Candidate skills do nicho
    nicho_key = nicho.lower().replace(" ", "_") if nicho else "servicos"
    candidates = NICHE_SKILLS.get(nicho_key, NICHE_SKILLS.get("servicos", []))

    # Filtra skill de agendamento se o plano não suporta
    if not has_agenda:
        candidates = [s for s in candidates if "agendamento" not in s]

    # Ordena por score de aprendizado (maior = melhor)
    scored = [(s, get_skill_score(nicho_key, s)) for s in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Aplica limite do plano
    top_skills = [s for s, _ in scored[:max_nicho]]
    selected.extend(top_skills)

    # Registra uso no learning
    for skill in top_skills:
        record_skill_usage(nicho_key, skill)

    return selected


def get_skill_meta(skill_name: str) -> dict:
    """Lê o meta.json de uma skill da biblioteca."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Tenta na pasta base primeiro, depois nas subpastas de nicho
    paths_to_try = [
        os.path.join(base_dir, "skills_library", "_base", skill_name, "meta.json"),
    ]
    for nicho_folder in NICHE_SKILLS:
        paths_to_try.append(
            os.path.join(base_dir, "skills_library", nicho_folder, skill_name, "meta.json")
        )

    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"name": skill_name, "title": skill_name, "description": ""}


def load_skill_instructions(skill_name: str) -> str:
    """
    Carrega as instruções de prompt de uma skill (arquivo instructions.txt ou do meta.json).
    Usado pelo prompt_builder para injetar comportamentos no system prompt.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    all_folders = ["_base"] + list(NICHE_SKILLS.keys())
    for folder in all_folders:
        instr_path = os.path.join(base_dir, "skills_library", folder, skill_name, "instructions.txt")
        if os.path.exists(instr_path):
            with open(instr_path, "r", encoding="utf-8") as f:
                return f.read().strip()
    # Fallback: usa description do meta.json
    meta = get_skill_meta(skill_name)
    return meta.get("prompt_instruction", meta.get("description", ""))
