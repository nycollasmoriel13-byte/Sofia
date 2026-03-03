"""
Skill: Onboarding - Coleta completa de dados tecnicos + plataforma + chaves de API.
Suporta WhatsApp (Meta API) e Telegram. Plataforma e coletada primeiro e determina
quais credenciais de API serao solicitadas.
"""
import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Optional, List, Tuple

DB_NAME = os.getenv('DB_NAME', 'agencia_autovenda.db')

# ── Campos de descoberta de plataforma ──────────────────────────────────────
FIELDS_PLATAFORMA = ["plataforma"]

# ── Credenciais por plataforma ───────────────────────────────────────────────
FIELDS_API_WHATSAPP = [
    "meta_phone_number_id",
    "meta_whatsapp_token",
    "meta_webhook_verify_token",
]
FIELDS_API_TELEGRAM = [
    "telegram_bot_token",
    "telegram_bot_username",
]

# ── Dados comuns a todos os planos ───────────────────────────────────────────
FIELDS_COMMON_CORE = [
    "empresa_nome",
    "horario_funcionamento",
    "tom_de_voz",
    "transbordo_nome",
    "transbordo_contato",
    "site_ou_redes",
    "servicos_produtos",
    "faq_perguntas",
]

# ── Dados adicionais por plano ───────────────────────────────────────────────
FIELDS_SECRETARIA_EXTRA = [
    "agenda_servicos",
    "agenda_email_google",
    "agenda_politica_cancel",
    "agenda_max_dia",
    "agenda_intervalo_min",
]
FIELDS_ECOSSISTEMA_EXTRA = FIELDS_SECRETARIA_EXTRA + [
    "crm_atual",
    "equipe_estrutura",
    "redes_integrar",
    "metricas_dashboard",
    "regras_escalacao",
]


def _build_fields(plano: str, plataforma: str) -> list:
    api_fields = FIELDS_API_WHATSAPP if plataforma == "whatsapp" else FIELDS_API_TELEGRAM
    base = FIELDS_PLATAFORMA + api_fields + FIELDS_COMMON_CORE
    p = plano.lower().replace(" ", "_").replace("-", "_")
    if p in ("secretaria", "secretaria_virtual"):
        return base + FIELDS_SECRETARIA_EXTRA
    if p in ("ecossistema", "ecossistema_completo"):
        return base + FIELDS_ECOSSISTEMA_EXTRA
    return base  # flash


# ── Guias completos de configuracao de plataforma ───────────────────────────
GUIDE_WPP_SETUP = """
Vou te guiar passo a passo para pegar as credenciais do WhatsApp. e bem simples, prometo!

PASSO 1 — Acesse o Meta for Developers
   Abra: https://developers.facebook.com
   Faca login com sua conta do Facebook/Meta.

PASSO 2 — Crie ou acesse seu App
   Clique em "Meus Apps" (canto superior direito).
   Se ainda nao tiver um App: clique em "Criar App" > escolha o tipo "Outros" > "Negocios".
   Se ja tiver um App de negocio, clique nele.

PASSO 3 — Adicione o produto WhatsApp
   Dentro do seu App, no menu lateral procure "Adicionar produto".
   Encontre "WhatsApp" e clique em "Configurar".

PASSO 4 — Acesse a API Setup
   No menu lateral va em "WhatsApp" > "Configuracao da API".
   Nessa pagina voce vai encontrar 2 das 3 informacoes que preciso:

   [ Phone Number ID ]
   Aparece logo no inicio da pagina, abaixo de "Numero de telefone".
   Copie esse numero e me manda.

   [ Access Token temporario ]
   Logo abaixo do Phone Number ID, no campo "Token de acesso temporario".
   ATENCAO: esse token expira em 24h. Para producao, vamos precisar de um token permanente
   (eu te oriento no proximo passo como gerar).

PASSO 5 (opcional mas recomendado) — Token Permanente
   Va em: Configuracoes do Negocio > Usuarios do Sistema > "Adicionar".
   Crie um usuario com funcao "Admin".
   Clique em "Gerar novo token" > selecione seu App.
   Marque as permissoes: whatsapp_business_messaging e whatsapp_business_management.
   Copie o token gerado — esse nao expira.

PASSO 6 — Webhook Verify Token
   Esse voce mesmo cria! E so uma senha/palavra-chave qualquer que usamos para verificar
   que as mensagens sao autenticas. Pode ser algo como: minha_loja_2024
   Anote essa palavra pois vamos precisar dela.

Pronto! Quando tiver o Phone Number ID, pode me mandar que seguimos do passo 4 em diante juntos."""

GUIDE_TELEGRAM_SETUP = """
Criar um bot no Telegram e muito rapido — menos de 5 minutos! Siga:

PASSO 1 — Abra o Telegram e busque @BotFather
   No campo de busca do Telegram, pesquise: BotFather
   Abra a conversa com o bot oficial (tem o selo azul de verificado).

PASSO 2 — Crie seu bot
   Envie o comando: /newbot
   O BotFather vai perguntar:
   > "Como vamos chamar seu bot?" — coloque o nome completo (ex: Atendimento Loja Bella)
   > "Agora escolha um username" — precisa terminar em _bot (ex: LojaBella_bot)

PASSO 3 — Copie o Token
   Apos confirmar o username, o BotFather vai enviar uma mensagem com o token.
   Ele tem este formato: 123456789:AAHhXyzAbcDef...
   Copie esse token completo e me manda aqui.

PASSO 4 — Pronto!
   O username do bot e o @LojaBella_bot (com @) — me manda esse tambem.

Dica: voce pode personalizar o bot no BotFather depois: /setdescription, /setuserpic, /setabouttext."""


FIELD_QUESTIONS = {
    # Plataforma
    "plataforma": (
        "Primeiro, preciso saber: qual plataforma voce quer usar para o bot? "
        "WhatsApp ou Telegram?\n\n"
        "  *WhatsApp* — chega a todos diretamente, mas usa a API oficial da Meta, "
        "que cobra por mensagem enviada (taxa acessivel, paga por voce diretamente a Meta). "
        "O numero que os clientes ja conhecem fica ativo.\n\n"
        "  *Telegram* — gratuito, sem taxas de API, otimo para bots de suporte e comunidades. "
        "Seu cliente precisaria entrar em contato pelo Telegram.\n\n"
        "Qual das duas faz mais sentido para o seu negocio?"
    ),
    # WhatsApp Meta API
    "meta_phone_number_id": (
        "Ja vou te enviar o passo a passo completo para pegar as credenciais! "
        "Quando tiver o *Phone Number ID* em maos, me manda aqui."
    ),
    "meta_whatsapp_token": (
        "Otimo! Agora preciso do *Access Token* do WhatsApp Business. "
        "Ele aparece na mesma pagina do Phone Number ID, no campo 'Token de acesso temporario'. "
        "Se ja gerou um token permanente pelo Sistema de Usuarios, pode mandar esse tambem. "
        "Qual a opcao que voce tem disponivel agora?"
    ),
    "meta_webhook_verify_token": (
        "Ultimo item das credenciais Meta! Preciso de um *Webhook Verify Token*. "
        "Voce mesmo cria esse — e so uma palavra ou frase sem espacos que usamos como "
        "senha de verificacao das mensagens. "
        "Exemplo: minha_loja_2024 ou bella_estetica_wpp "
        "Escolha uma e me manda!"
    ),
    # Telegram
    "telegram_bot_token": (
        "Ja vou te enviar o passo a passo para criar o bot no Telegram! "
        "Quando tiver o *token* do BotFather, me manda aqui."
    ),
    "telegram_bot_username": (
        "E qual e o *username* do bot que o BotFather gerou? "
        "(formato: @NomeDaLoja_bot — com o @ na frente)"
    ),
    # Dados da empresa
    "empresa_nome": "Qual e o nome da sua empresa (como ela aparece para os clientes)?",
    "horario_funcionamento": (
        "Quais sao os horarios de funcionamento? "
        "(dias e horarios, ex: seg-sex 8h as 18h, sab 9h as 13h)"
    ),
    "tom_de_voz": (
        "Como prefere que o bot fale com seus clientes: "
        "mais formal e profissional, ou descontraido e simpatico?"
    ),
    "transbordo_nome": (
        "Quando o bot nao souber responder, para quem direcionamos? "
        "Qual o nome da pessoa ou setor responsavel pelo atendimento humano?"
    ),
    "transbordo_contato": (
        "Qual o contato dessa pessoa para transbordo? "
        "(WhatsApp com DDD, e-mail ou nome de usuario no Telegram)"
    ),
    "site_ou_redes": (
        "Tem site ou rede social que posso usar para entender melhor "
        "os produtos e o tom da empresa? (pode mandar o link)"
    ),
    "servicos_produtos": (
        "Lista todos os servicos ou produtos que voce oferece! "
        "Pode mandar um por um ou tudo de uma vez."
    ),
    "faq_perguntas": (
        "Quais sao as 5 a 8 perguntas mais frequentes dos seus clientes? "
        "Me conta a pergunta e a resposta ideal para cada uma. "
        "Isso e fundamental para o bot responder certinho."
    ),
    # Secretaria Virtual
    "agenda_servicos": (
        "Quais servicos podem ser agendados? Para cada um me diz: "
        "nome, duracao e valor (ex: Consulta — 1h — R$ 150)."
    ),
    "agenda_email_google": (
        "Qual e o e-mail do Google Agenda para integrar? "
        "(precisa ser Gmail ou G Suite)"
    ),
    "agenda_politica_cancel": (
        "Qual e a politica de cancelamento ou remarcacao? "
        "(ex: pode cancelar ate 2h antes sem custo)"
    ),
    "agenda_max_dia": "Qual o numero maximo de atendimentos por dia?",
    "agenda_intervalo_min": (
        "Qual o intervalo entre atendimentos? "
        "(em minutos, ex: 15, 30 ou 60 min)"
    ),
    # Ecossistema Completo
    "crm_atual": (
        "Voces usam algum CRM hoje? "
        "(HubSpot, RD Station, Pipedrive, planilha, nenhum...)"
    ),
    "equipe_estrutura": (
        "Como e a equipe de atendimento? "
        "Quantas pessoas e se tem setores ou departamentos."
    ),
    "redes_integrar": (
        "Alem da plataforma principal, quais outros canais quer integrar? "
        "(Instagram, Facebook, site, e-mail...)"
    ),
    "metricas_dashboard": (
        "Quais metricas sao mais importantes pra voce acompanhar? "
        "(ex: leads por dia, conversao, tempo de resposta)"
    ),
    "regras_escalacao": (
        "Tem regras de prioridade ou escalacao? "
        "(ex: cliente VIP vai direto pro gerente, reclamacoes para fulano)"
    ),
}


def setup_tables():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_data (
            user_id TEXT PRIMARY KEY, plano TEXT, dados_json TEXT,
            campos_coletados TEXT, campos_pendentes TEXT,
            status TEXT DEFAULT 'em_progresso',
            data_inicio TEXT, data_conclusao TEXT
        )
    """)
    conn.commit()
    conn.close()


def _get_subscription(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT status, plano FROM assinaturas WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return {"status": row[0], "plano": row[1] or "flash"} if row else None
    except Exception:
        return None


def _load_onboarding(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "SELECT plano, dados_json, campos_coletados, campos_pendentes, status "
            "FROM onboarding_data WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "plano": row[0],
                "dados": json.loads(row[1] or "{}"),
                "coletados": json.loads(row[2] or "[]"),
                "pendentes": json.loads(row[3] or "[]"),
                "status": row[4],
            }
        return None
    except Exception:
        return None


def _save_onboarding(user_id, plano, dados, coletados, pendentes, status):
    setup_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO onboarding_data
            (user_id, plano, dados_json, campos_coletados, campos_pendentes, status, data_inicio, data_conclusao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            plano=excluded.plano,
            dados_json=excluded.dados_json,
            campos_coletados=excluded.campos_coletados,
            campos_pendentes=excluded.campos_pendentes,
            status=excluded.status,
            data_conclusao=CASE WHEN excluded.status='completo' THEN ? ELSE data_conclusao END
    """, (
        user_id, plano,
        json.dumps(dados, ensure_ascii=False),
        json.dumps(coletados),
        json.dumps(pendentes),
        status, now, now, now,
    ))
    conn.commit()
    conn.close()


def _detect_platform(text: str) -> Optional[str]:
    t = text.lower()
    if any(w in t for w in ["whatsapp", "wpp", "zap", "whats", "wts"]):
        return "whatsapp"
    if any(w in t for w in ["telegram", "tg", "telgram"]):
        return "telegram"
    return None


def _extract_value(field: str, text: str) -> Optional[str]:
    t = text.strip()
    if not t:
        return None
    if field == "plataforma":
        return _detect_platform(t)
    if field in ("meta_phone_number_id",):
        m = re.search(r"\b(\d{10,20})\b", t)
        return m.group(1) if m else (t if len(t) > 5 else None)
    if field in ("meta_whatsapp_token", "meta_webhook_verify_token", "telegram_bot_token"):
        # tokens nao tem formato fixo, aceita qualquer string com comprimento minimo
        return t if len(t) >= 8 else None
    if field == "telegram_bot_username":
        m = re.search(r"@?([\w]+_bot)\b", t, re.IGNORECASE)
        return "@" + m.group(1) if m else (t if len(t) >= 4 else None)
    if field in ("transbordo_contato",):
        # aceita telefone, e-mail ou username telegram
        phone = re.search(r"(\+?\d[\d\s\-()]{7,20}\d)", t)
        if phone:
            return re.sub(r"[\s\-()]+", "", phone.group(1))
        email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", t)
        if email:
            return email.group(0)
        return t if len(t) >= 4 else None
    if field == "agenda_email_google":
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", t)
        return m.group(0).lower() if m else None
    if field == "site_ou_redes":
        m = re.search(r"(https?://[^\s]+|[\w\-]+\.(com|com\.br|net|org|io|tech)(/[^\s]*)?)", t, re.IGNORECASE)
        return m.group(0) if m else (t if len(t) > 5 else None)
    if field in ("agenda_max_dia", "agenda_intervalo_min"):
        m = re.search(r"\b(\d+)\b", t)
        return str(int(m.group(1))) if m else (t if t else None)
    return t if len(t) >= 4 else None


def run(user_id: str, message_text: str, history: List[Tuple[str, str]] = None) -> dict:
    history = history or []
    setup_tables()

    sub = _get_subscription(user_id)
    if not sub or sub["status"] != "ativo":
        return {"status": "bloqueado", "message": "Aguardando confirmacao de pagamento."}

    plano_raw = (sub.get("plano") or "flash").lower().replace(" ", "_").replace("-", "_")
    progress = _load_onboarding(user_id)

    if not progress:
        # Inicio: coleta apenas a plataforma primeiro
        dados, coletados = {}, []
        pendentes = ["plataforma"]
    else:
        dados = progress["dados"]
        coletados = progress["coletados"]
        pendentes = progress["pendentes"]

        # Quando plataforma acabou de ser coletada, expande a lista de pendentes
        if not pendentes and "plataforma" in coletados:
            plataforma = dados.get("plataforma", "whatsapp")
            required = _build_fields(plano_raw, plataforma)
            pendentes = [f for f in required if f not in coletados]

    # Tenta extrair o campo pendente atual da mensagem
    if pendentes:
        current_field = pendentes[0]
        extracted = _extract_value(current_field, message_text)
        if extracted:
            dados[current_field] = extracted
            coletados.append(current_field)
            pendentes = pendentes[1:]

            # Se acabou de coletar a plataforma, expande os pendentes agora
            if current_field == "plataforma":
                plataforma = extracted
                required = _build_fields(plano_raw, plataforma)
                pendentes = [f for f in required if f not in coletados]

    status = "completo" if not pendentes else "em_progresso"
    _save_onboarding(user_id, plano_raw, dados, coletados, pendentes, status)

    if status == "completo":
        plataforma = dados.get("plataforma", "whatsapp")
        resumo = "\n".join([f"  - {k}: {v}" for k, v in dados.items()])
        return {
            "status": "completo",
            "plano": plano_raw,
            "plataforma": plataforma,
            "dados": dados,
            "resumo": resumo,
            "instruction": (
                "ONBOARDING 100% COMPLETO! Todos os dados tecnicos foram registrados. "
                "Faca um resumo formatado e bonito de tudo que foi coletado, "
                "agradeca calorosamente, e informe que a equipe tecnica ja vai iniciar "
                "a configuracao e que em breve ele recebera confirmacao de ativacao. "
                "Sea entusiasmada — isso e motivo de comemorar! Mencione a plataforma escolhida "
                f"({plataforma.title()}) na mensagem de conclusao. Emoji de confete obrigatorio."
            ),
        }

    next_field = pendentes[0]
    next_q = FIELD_QUESTIONS.get(next_field, f"Pode me informar: {next_field.replace('_', ' ')}?")
    plataforma = dados.get("plataforma", "")
    required_total = len(_build_fields(plano_raw, plataforma)) if plataforma else len(FIELDS_PLATAFORMA)
    pct = int(len(coletados) / max(required_total, 1) * 100)
    last_saved = coletados[-1] if coletados else None
    last_val = dados.get(last_saved, "") if last_saved else ""

    # Guia de API a injetar quando for coletar a primeira credencial de cada plataforma
    api_guide = ""
    if next_field == "meta_phone_number_id":
        api_guide = (
            "INSTRUCAO ESPECIAL -- O cliente vai precisar do passo a passo para pegar as credenciais da Meta. "
            "Envie a mensagem abaixo EXATAMENTE assim (pode adaptar o tom mas mantenha todos os passos), "
            "ANTES de pedir o Phone Number ID:\n\n"
            "--- INICIO DO GUIA ---\n"
            + GUIDE_WPP_SETUP +
            "\n--- FIM DO GUIA ---\n\n"
            "Apos enviar o guia, informe sobre a taxa Meta: "
            "'Ah, e importante saber: a API do WhatsApp cobra uma taxinha por conversa diretamente pela Meta -- "
            "nao pela nossa agencia. Geralmente R$ 0,03 a R$ 0,12 por conversa. "
            "Bem acessivel e proporcional ao retorno. Qualquer duvida sobre isso e so me perguntar!' "
            "Depois, pergunte: 'Quando tiver o Phone Number ID em maos, me manda aqui!'"
        )
    elif next_field == "telegram_bot_token":
        api_guide = (
            "INSTRUCAO ESPECIAL -- O cliente precisa criar o bot no Telegram. "
            "Envie o guia abaixo antes de pedir o token:\n\n"
            "--- INICIO DO GUIA ---\n"
            + GUIDE_TELEGRAM_SETUP +
            "\n--- FIM DO GUIA ---\n\n"
            "Apos enviar o guia, diga: 'Telegram e bem mais simples mesmo! "
            "Quando tiver o token em maos, e so me mandar aqui.'"
        )
    elif next_field == "meta_whatsapp_token":
        api_guide = (
            "Lembre ao cliente onde encontrar o Access Token: "
            "'Na mesma pagina da API Setup do Meta for Developers, logo abaixo do Phone Number ID, "
            "voce encontra o Token de acesso temporario. "
            "Se quiser um token que nao expira, va em Configuracoes do Negocio > Usuarios do Sistema, "
            "crie um usuario admin, gere um token com permissoes whatsapp_business_messaging e "
            "whatsapp_business_management.' "
            "Pergunte qual opcao o cliente tem disponivel agora."
        )

    return {
        "status": "em_progresso",
        "plano": plano_raw,
        "plataforma": plataforma,
        "campos_coletados": len(coletados),
        "campos_total": required_total,
        "progresso_pct": pct,
        "ultimo_campo": last_saved,
        "ultimo_valor": last_val,
        "proximo_campo": next_field,
        "proxima_pergunta": next_q,
        "api_guide": api_guide or None,
        "dados": dados,
        "instruction": (
            f"ONBOARDING EM PROGRESSO -- {pct}% ({len(coletados)}/{required_total} campos).\n"
            + (f"Dado registrado: '{last_saved}' = '{last_val}'.\n" if last_saved else "Inicio da coleta.\n")
            + (api_guide + "\n" if api_guide else "")
            + f"Proxima pergunta/acao:\n'{next_q}'\n"
            + "Confirme o dado anterior com um 'Anotado!' antes. "
            + "Uma acao por mensagem. Nunca seja robotica."
        ),
    }