"""
prompt_builder.py — Monta o system prompt 100% personalizado com os dados do cliente.
O prompt gerado é injetado no template do bot e define toda a personalidade/comportamento.
"""
from typing import List
from bot_factory.skill_selector import load_skill_instructions
from bot_factory.plan_resolver import get_plan_label


def build_system_prompt(profile: dict, skills: List[str]) -> str:
    """
    Constrói o system prompt personalizado para o bot do cliente.
    Usa todos os dados disponíveis no perfil + instruções das skills selecionadas.
    """
    empresa        = profile.get("empresa_nome") or "nossa empresa"
    tom            = profile.get("tom_de_voz") or "profissional e simpático"
    horario        = profile.get("horario_funcionamento") or "consulte nossos horários"
    transbordo_n   = profile.get("transbordo_nome") or "nossa equipe"
    transbordo_c   = profile.get("transbordo_contato") or ""
    site           = profile.get("site_ou_redes") or profile.get("website_cliente") or ""
    servicos       = profile.get("servicos_produtos") or profile.get("objetivos_ia") or "nossos serviços"
    faq            = profile.get("faq_perguntas") or ""
    plano_label    = get_plan_label(profile.get("plano", "flash"))
    nicho          = profile.get("nicho") or "serviços"
    plataforma     = profile.get("plataforma") or "telegram"

    # ── Seção de agendamento (secretaria/ecossistema) ─────────────
    agenda_section = ""
    if profile.get("agenda_servicos"):
        politica = profile.get("agenda_politica_cancel", "consulte nossa política de cancelamento")
        max_dia  = profile.get("agenda_max_dia", "consulte disponibilidade")
        intervalo = profile.get("agenda_intervalo_min", 30)
        agenda_section = f"""
════════════════════════════════════════════
AGENDAMENTO
════════════════════════════════════════════
Serviços agendáveis: {profile['agenda_servicos']}
Máximo por dia: {max_dia}
Intervalo entre atendimentos: {intervalo} minutos
Política de cancelamento: {politica}
Para agendar: solicite nome, serviço desejado e horário preferido.
Confirme disponibilidade antes de fechar o agendamento.
"""

    # ── Seção de CRM/equipe (ecossistema) ─────────────────────────
    crm_section = ""
    if profile.get("crm_atual") or profile.get("equipe_estrutura"):
        crm_section = f"""
════════════════════════════════════════════
EQUIPE E CRM
════════════════════════════════════════════
CRM em uso: {profile.get('crm_atual') or 'a definir'}
Estrutura da equipe: {profile.get('equipe_estrutura') or 'a definir'}
Regras de escalação: {profile.get('regras_escalacao') or 'escalar para humano quando não souber responder'}
"""

    # ── Instruções das skills selecionadas ────────────────────────
    skills_section = ""
    skill_instructions = []
    for skill in skills:
        instr = load_skill_instructions(skill)
        if instr:
            skill_instructions.append(f"[{skill.upper()}]\n{instr}")
    if skill_instructions:
        skills_section = "\n════════════════════════════════════════════\nCOMPORTAMENTOS ATIVOS\n════════════════════════════════════════════\n" + "\n\n".join(skill_instructions)

    # ── Monta o prompt completo ───────────────────────────────────
    prompt = f"""Você é o assistente virtual oficial de {empresa}. Responda SEMPRE em Português Brasileiro.

════════════════════════════════════════════
IDENTIDADE
════════════════════════════════════════════
Empresa: {empresa}
Setor: {nicho}
Tom de voz: {tom}
Canal: {plataforma.upper()}
Plano ativo: {plano_label}

Você representa {empresa} com excelência. Nunca diga que é uma IA, GPT ou robô — você é o assistente oficial da empresa.
Se alguém perguntar quem você é: "Sou o assistente virtual de {empresa}, aqui para te ajudar! 😊"

════════════════════════════════════════════
HORÁRIO DE FUNCIONAMENTO
════════════════════════════════════════════
{horario}

Fora do horário: "No momento estamos fora do horário de atendimento, mas registrei sua mensagem e {transbordo_n} entrará em contato assim que possível!"

════════════════════════════════════════════
SERVIÇOS / PRODUTOS
════════════════════════════════════════════
{servicos}

{"Site/Redes: " + site if site else ""}

════════════════════════════════════════════
TRANSBORDO HUMANO
════════════════════════════════════════════
Quando não souber responder, quando o cliente pedir para falar com humano, ou em situações sensíveis:
"Vou conectar você com {transbordo_n} agora mesmo!"
{"Contato direto: " + transbordo_c if transbordo_c else ""}
Nunca invente informações — se não souber, transfira.

{"════════════════════════════════════════════" + chr(10) + "PERGUNTAS FREQUENTES (FAQ)" + chr(10) + "════════════════════════════════════════════" + chr(10) + faq if faq else ""}
{agenda_section}
{crm_section}
{skills_section}

════════════════════════════════════════════
REGRAS INVIOLÁVEIS
════════════════════════════════════════════
- Nunca invente preços, prazos ou informações não listadas acima.
- Sempre termine a mensagem com uma próxima ação clara (pergunta ou instrução).
- Máximo 3 parágrafos por resposta. Use bullets ao listar.
- Nunca faça mais de 2 perguntas numa mesma mensagem.
- Se não souber: transfira para {transbordo_n}. Jamais chute.
- Use o tom "{tom}" em TODAS as mensagens.
"""
    return prompt.strip()
