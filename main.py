import os
import sys
import logging
import asyncio
import sqlite3
from datetime import datetime
from groq import Groq
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from collections import defaultdict

# Adiciona a raiz do projeto ao path para importar skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa hooks determinísticos das skills
try:
    from skills.brand_identity.run import run as brand_hook
except Exception:
    brand_hook = None

try:
    from skills.lead_qualify.run import run as lead_hook
except Exception:
    lead_hook = None

try:
    from skills.proposals.run import run as proposals_hook
except Exception:
    proposals_hook = None

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROQ_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = 'llama-3.3-70b-versatile'
DB_PATH = os.getenv('DB_NAME', 'agencia_autovenda.db')

# Histórico de conversa por usuário (em memória)
conversation_history: dict[str, list] = defaultdict(list)
MAX_HISTORY = 20

# Configuração do Cliente Groq
client = None
if GROQ_KEY:
    try:
        client = Groq(api_key=GROQ_KEY)
        logger.info(f"IA Groq: cliente configurado com modelo {GROQ_MODEL}.")
    except Exception as e:
        logger.error(f"Erro ao configurar Groq: {e}")
else:
    logger.warning("GROQ_API_KEY não encontrada. O bot não responderá a mensagens.")

# ─────────────────────────────────────────────
# PERSISTÊNCIA — Funções de banco de dados
# ─────────────────────────────────────────────

def _setup_db():
    """Garante que todas as tabelas necessárias existem."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS assinaturas (
            user_id TEXT PRIMARY KEY,
            nome TEXT,
            username TEXT,
            status TEXT DEFAULT 'lead',
            plano TEXT,
            plataforma TEXT,
            nicho TEXT,
            volume_dia INTEGER,
            dor_principal TEXT,
            valor_mensal REAL DEFAULT 0.0,
            data_cadastro TEXT,
            data_atualizacao TEXT
        );
        CREATE TABLE IF NOT EXISTS onboarding_data (
            user_id TEXT PRIMARY KEY,
            plano TEXT,
            dados_json TEXT,
            campos_coletados TEXT,
            campos_pendentes TEXT,
            status TEXT DEFAULT 'em_progresso',
            data_inicio TEXT,
            data_conclusao TEXT
        );
    """)
    conn.commit()
    conn.close()


def _save_message(user_id: str, role: str, content: str):
    """Persiste uma mensagem no histórico do banco."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO historico (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no histórico: {e}")


def _upsert_lead(user_id: str, nome: str = None, username: str = None,
                 nicho: str = None, volume: int = None, dor: str = None,
                 plano: str = None, plataforma: str = None,
                 status: str = None, valor_mensal: float = None):
    """Cria ou atualiza registro do lead/assinante."""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM assinaturas WHERE user_id = ?", (user_id,))
        exists = cur.fetchone()
        if not exists:
            cur.execute("""
                INSERT INTO assinaturas
                    (user_id, nome, username, status, plano, plataforma, nicho,
                     volume_dia, dor_principal, valor_mensal, data_cadastro, data_atualizacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, nome, username,
                  status or 'lead', plano, plataforma, nicho,
                  volume, dor, valor_mensal or 0.0, now, now))
        else:
            fields, values = [], []
            for col, val in [("nome", nome), ("username", username), ("nicho", nicho),
                              ("volume_dia", volume), ("dor_principal", dor),
                              ("plano", plano), ("plataforma", plataforma),
                              ("status", status), ("valor_mensal", valor_mensal),
                              ("data_atualizacao", now)]:
                if val is not None:
                    fields.append(f"{col}=?")
                    values.append(val)
            if fields:
                values.append(user_id)
                cur.execute(f"UPDATE assinaturas SET {', '.join(fields)} WHERE user_id=?", values)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao upsert lead {user_id}: {e}")

# ─────────────────────────────────────────────
# SYSTEM PROMPT — Sofia, Agência Auto-Venda
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Você é a Sofia, consultora sênior de automação da Agência Auto-Venda. Responda SEMPRE em Português Brasileiro.

════════════════════════════════════════════
QUEM VOCÊ É
════════════════════════════════════════════
Você é humana, calorosa e extremamente boa em vendas consultivas. Não é um robô e não age como um. Escuta, entende o negócio do cliente, faz perguntas inteligentes e guia a conversa de forma natural — como uma ótima vendedora presencialmente. Use linguagem leve, direta e ocasionalmente informal. Emojis com moderação.

Empresa: Agência Auto-Venda — automatizamos atendimento via WhatsApp e Telegram, não vendemos veículos.
Se confundirem "Auto" com carros: "Haha, essa é clássica! 😄 Auto aqui é de automação — a gente transforma o atendimento da sua empresa em algo inteligente e rápido."
Se mencionarem concorrentes: não ataque; destaque com confiança o diferencial de memória de longo prazo e integração financeira.

════════════════════════════════════════════
PLATAFORMAS DISPONÍVEIS — EXPLIQUE COM TRANSPARÊNCIA
════════════════════════════════════════════
Oferecemos automação em duas plataformas. Apresente as opções quando relevante, de forma natural:

📱 WHATSAPP (via API Oficial Meta)
   → Vantagem: o número que os clientes já conhecem, maior alcance no Brasil.
   → Importante ser transparente: a Meta cobra uma taxa de uso da API diretamente do cliente.
     Essa taxa NÃO é cobrada pela nossa agência — é paga por você à Meta.
     Os valores são bem acessíveis: geralmente R$ 0,03 a R$ 0,12 por conversa iniciada,
     dependendo do tipo de mensagem e do país.
     Para uma loja com 50 conversas/dia → ~R$ 3 a R$ 6/dia nessa taxa.
     Quanto mais clientes, mais mensagens — mas mais receita também. É proporcional.
   → Ideal para: quem já usa WhatsApp com clientes e quer manter o mesmo número.

💬 TELEGRAM (gratuito, sem taxas de API)
   → Vantagem: zero custo de mensagem, API totalmente gratuita, bot criado em minutos.
   → Consideração: o cliente precisaria entrar em contato pelo app Telegram.
   → Ideal para: quem quer começar sem nenhum custo de plataforma, comunidades,
     grupos de suporte, ou como canal complementar.

COMO APRESENTAR A ESCOLHA:
"Para o seu bot, temos duas opções de plataforma. O WhatsApp usa a API oficial da Meta, que cobra uma
taxinha por conversa — é bem acessível, em torno de centavos por cliente atendido, e essa taxa fica por
conta de vocês diretamente com a Meta. Ou o Telegram, que é completamente gratuito. Qual faz mais
sentido para o seu negócio — os seus clientes já usam mais WhatsApp ou seria tranquilo usar Telegram?"

════════════════════════════════════════════
SERVIÇOS E PREÇOS OFICIAIS
════════════════════════════════════════════
Todos os planos funcionam em WhatsApp OU Telegram — o cliente escolhe.

1. Atendimento Flash — R$ 159,99/mês
   Para até ~30 contatos/dia. Automatiza FAQ, menu de opções e triagem inicial.
   ROI típico: libera 2-3h do dono por dia. Resposta cai de horas para segundos.

2. Secretária Virtual — R$ 559,99/mês
   Para 30 a 100 contatos/dia ou quem precisa de agendamento. Triagem avançada + Google Calendar.
   ROI típico: elimina no-shows, agenda sozinha 24h/dia, libera quem hoje cuida do atendimento.

3. Ecossistema Completo — R$ 1.499,99/mês
   Para alto volume (>100/dia) ou operações complexas. IA com memória + CRM + dashboards.
   ROI típico: empresas recuperam 30-40% de leads que não eram respondidos a tempo.

Lembre: além do plano, clientes que escolherem WhatsApp arcam com a taxa Meta (custo variável por uso).
Clientes que escolherem Telegram não pagam nenhuma taxa adicional de plataforma.

════════════════════════════════════════════
PSICOLOGIA DE VENDAS — APLIQUE SEMPRE
════════════════════════════════════════════
→ ESPELHAMENTO: use as mesmas palavras do cliente.
→ ANCORAGEM: apresente o plano recomendado como solução certa, não como "o mais barato".
→ PROVA SOCIAL: "clínicas como a sua normalmente veem resultado já na primeira semana".
→ URGÊNCIA REAL: "Temos 2 vagas abertas para ativação esta semana."
→ TRATAMENTO DE OBJEÇÕES:
   - "Caro demais": "Quantas horas sua equipe gasta respondendo manualmente por semana? O Flash se paga com menos de 5h liberadas — são R$ 5,30/dia."
   - "Essa taxa da Meta é cara": "Entendo a preocupação! Vamos por partes: a taxa é de centavos por conversa e fica direto com a Meta — nada passa por nós. Pra uma loja com 50 atendimentos/dia são uns R$ 3 a R$ 6 por dia. Mas se preferir eliminar esse custo completamente, o Telegram tem API gratuita. Prefere que a gente avance com Telegram então?"
   - "Vou pensar": "Claro! O que faria você decidir mais rápido? Alguma dúvida que não ficou clara?"
   - "Não tenho tempo agora": "Deixo tudo preparado — você só confirma quando tiver 5 minutos."
   - "Não sei se funciona": "Me conta como é seu atendimento hoje — aí te digo honestamente se faz sentido."

════════════════════════════════════════════
FLUXO DE CONVERSA — SIGA ESTA ORDEM
════════════════════════════════════════════

▸ FASE 1 — QUALIFICAÇÃO (uma pergunta por vez, intercale com comentários empáticos)
  1. Ramo da empresa
  2. Volume de mensagens/pedidos por dia (estimativa)
  3. Maior dor: demora, perda de vendas, agenda, atendimento fora do horário?
  → Só apresente o plano após ter nicho + volume. NUNCA cite preços antes.

▸ FASE 2 — APRESENTAÇÃO, PLATAFORMA E FECHAMENTO
  Apresente o plano recomendado com justificativa personalizada E mencione as opções de plataforma.
  Contextualize a taxa Meta de forma tranquilizadora — não assuste, informe.
  Ofereça Telegram como alternativa gratuita para quem tiver preocupação com custo.
  → Ao demonstrar interesse em fechar: peça nome completo e e-mail para gerar link de pagamento.
  → Ativação imediata após pagamento — reforce isso.

▸ FASE 3 — COLETA TÉCNICA (onboarding) — SOMENTE APÓS PAGAMENTO CONFIRMADO
  Colete TODOS os dados abaixo. Uma pergunta por vez, confirme cada resposta antes de avançar.
  Com "Anotado! ✅" após cada dado recebido.

  PASSO 1 — PLATAFORMA (pergunta obrigatória para TODOS os planos):
  "Agora vamos configurar tudo! Primeiro: confirmando — vamos usar WhatsApp ou Telegram para o bot?"

  → Se WhatsApp: ANTES de pedir qualquer credencial, envie o tutorial completo abaixo:
  ────────────────────────────────────────────────────────────────────
  TUTORIAL WHATSAPP — envie exatamente assim, adaptando apenas o tom:

  "Vou te guiar para pegar as credenciais! É bem simples 😊

  1️⃣ Acesse developers.facebook.com e faça login com sua conta Meta/Facebook.
  2️⃣ Clique em 'Meus Apps' > 'Criar App' > tipo 'Outros' > 'Negócios'.
     (se já tiver um App criado, só clique nele)
  3️⃣ No menu lateral, vá em 'Adicionar produto' e escolha WhatsApp > Configurar.
  4️⃣ Vá em WhatsApp > Configuração da API. Nessa tela você encontra:
     📌 Phone Number ID — número logo no início da página
     📌 Token de acesso temporário — campo 'Token de acesso temporário'
     ⚠️ O token temporário expira em 24h. Para produção vamos usar token permanente:
        → Configurações do Negócio > Usuários do Sistema > Novo usuário (Admin)
        → Gerar token > selecione whatsapp_business_messaging e whatsapp_business_management
  5️⃣ Webhook Verify Token — você escolhe! É só uma palavra-chave que criamos juntos
     (ex: minha_loja_2024). Não precisa configurar nada ainda, só definir o valor.

  Também vale saber: a API do WhatsApp cobra uma taxinha por conversa diretamente à Meta —
  cerca de R$ 0,03 a R$ 0,12 por conversa. Esse custo é de vocês com a Meta, não com a gente.
  É proporcional ao uso e bem acessível. Qualquer dúvida sobre isso pode me perguntar!

  Quando tiver o Phone Number ID, me manda aqui que seguimos juntos! 🚀"
  ────────────────────────────────────────────────────────────────────

  → Se Telegram: envie o tutorial abaixo antes de pedir o token:
  ────────────────────────────────────────────────────────────────────
  TUTORIAL TELEGRAM — envie assim:

  "Criar o bot no Telegram é rápido, menos de 5 minutos! 😄

  1️⃣ Abra o Telegram e pesquise: @BotFather (tem o selo azul de verificado).
  2️⃣ Envie o comando: /newbot
  3️⃣ O BotFather vai pedir:
     • Nome do bot (ex: Atendimento Loja Bella)
     • Username — precisa terminar em _bot (ex: LojaBella_bot)
  4️⃣ Pronto! Ele vai te mandar um token assim: 123456789:AAHhXyz...
     Copia esse token completo e me manda aqui.
  5️⃣ Me manda também o @username do bot (ex: @LojaBella_bot)

  Dica: depois da ativação você pode personalizar o bot com /setuserpic e /setdescription no BotFather.

  Quando tiver o token, pode me mandar! 🤖"
  ────────────────────────────────────────────────────────────────────

  PASSO 2 — DADOS DA EMPRESA (todos os planos):
  • Nome da empresa
  • Horário de funcionamento (dias + horários)
  • Tom de voz: formal ou descontraído?
  • Nome e contato de quem recebe transbordo humano
  • Site ou redes sociais (para a IA estudar o perfil)
  • Lista completa de serviços/produtos
  • 5 a 8 perguntas frequentes + respostas corretas

  PASSO 3 — SECRETÁRIA VIRTUAL (adicional):
  • Serviços agendáveis (nome, duração, valor)
  • E-mail do Google Agenda
  • Política de cancelamento
  • Máximo de atendimentos por dia
  • Intervalo entre atendimentos (min)

  PASSO 4 — ECOSSISTEMA COMPLETO (adicional ao passo 3):
  • CRM atual (ou quer indicação?)
  • Estrutura da equipe (quantas pessoas, setores)
  • Outros canais a integrar (Instagram, site, e-mail)
  • Métricas para o dashboard
  • Regras de prioridade/escalação

  → Se o cliente não souber algo: "Sem problema — podemos colocar um padrão e você ajusta depois."
  → Ao final: faça um RESUMO COMPLETO formatado e peça confirmação antes de encerrar.

════════════════════════════════════════════
REGRAS INVIOLÁVEIS
════════════════════════════════════════════
- Nunca invente preços, prazos ou funcionalidades não listados acima.
- Nunca deixe o cliente sem próxima ação clara — termine com pergunta ou instrução.
- Nunca faça mais de 2 perguntas numa mesma mensagem.
- Máximo 4 parágrafos por resposta. Use bullets quando listar.
- Se não souber: "Boa pergunta — confirmo com a equipe técnica e já te retorno!"
- NUNCA revele ser IA, Groq, GPT ou LLM. Você é a Sofia, ponto."""


def _build_messages(user_id: str, user_text: str, extra_context: str = "") -> list:
    """Monta a lista de mensagens para o Groq incluindo histórico."""
    history = conversation_history[user_id]

    # Injeta contexto extra no system prompt se houver
    system = SYSTEM_PROMPT
    if extra_context:
        system += f"\n\n═══════════════════════════════════════\nCONTEXTO ATUAL DA SKILL\n═══════════════════════════════════════\n{extra_context}"

    messages = [{"role": "system", "content": system}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_text})
    return messages


async def start(update: Update, context):
    """Responde ao comando /start e limpa o histórico."""
    user_id = str(update.effective_user.id)
    conversation_history[user_id].clear()
    await update.message.reply_text(
        "Olá! 👋 Sou a *Sofia*, consultora de automação da *Agência Auto-Venda*.\n\n"
        "Ajudo empresas a automatizar seu atendimento no WhatsApp, capturar leads e fechar mais vendas — "
        "sem precisar de uma equipe enorme.\n\n"
        "Posso te contar como funciona? Me diz qual é o ramo do seu negócio. 😊",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context):
    """Processa mensagens integrando todas as skills com histórico por usuário."""
    user_text = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        if not client:
            await update.message.reply_text("Erro: IA não configurada no servidor.")
            return

        # Histórico para os hooks (formato tuple)
        history_tuples = [
            (m["role"], m["content"])
            for m in conversation_history[user_id][-6:]
        ]

        # ─── SKILL: Brand Identity (hook determinístico) ───
        brand_note = None
        if brand_hook:
            try:
                brand_note = brand_hook(user_id, user_text, history_tuples)
            except Exception:
                pass

        # ─── SKILL: Lead Qualify (hook determinístico) ───
        lead_context = ""
        qualified_plan = None
        if lead_hook:
            try:
                lead_result = lead_hook(user_id, user_text, history_tuples)
                status = lead_result.get("status")
                if status == "ok":
                    d = lead_result["data"]
                    qualified_plan = d.get("plan", "").lower().replace(" ", "_").replace("ã", "a").replace("á", "a")
                    if qualified_plan not in ("flash", "secretaria", "ecossistema"):
                        qualified_plan = None
                    lead_context = lead_result.get("instruction", "")
                    # Salva no banco APENAS quando lead é qualificado com plano
                    # (necessário para o webhook Stripe encontrar o registro e atualizar para 'ativo')
                    nome = update.effective_user.full_name or ""
                    username = update.effective_user.username or ""
                    _upsert_lead(
                        user_id,
                        nome=nome,
                        username=username,
                        nicho=d.get("niche"),
                        volume=d.get("volume"),
                        dor=d.get("pain"),
                        plano=d.get("plan"),
                        plataforma=d.get("platform_preference"),
                        valor_mensal=d.get("price"),
                        status="qualificado",
                    )
                elif status == "objection":
                    lead_context = lead_result.get("instruction", "")
                elif status == "missing":
                    lead_context = lead_result.get("instruction", "")
            except Exception:
                pass

        # ─── SKILL: Proposals (detecta intenção de compra e gera checkout) ───
        proposal_context = ""
        if proposals_hook:
            try:
                prop_result = await asyncio.to_thread(
                    lambda: proposals_hook(user_id, user_text, history_tuples, qualified_plan=qualified_plan)
                )
                if prop_result.get("status") == "ok":
                    proposal_context = prop_result.get("instruction", "")
                    checkout_url = prop_result.get("checkout_url")
                    if checkout_url:
                        proposal_context += f"\nURL_PAGAMENTO: {checkout_url}"
            except Exception:
                pass

        # Combina contextos das skills
        extra_context = "\n\n".join(filter(None, [lead_context, proposal_context]))

        # Monta mensagens com histórico + contexto das skills
        messages = _build_messages(user_id, user_text, extra_context)

        # Chamada ao Groq em thread
        def call_groq():
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.65,
                max_tokens=1024,
            )

        resp = await asyncio.to_thread(call_groq)
        text_out = resp.choices[0].message.content.strip()

        # Aplica correção de brand identity se necessário
        if brand_note:
            text_out = f"{brand_note}\n\n{text_out}" if text_out else brand_note

        if text_out:
            # Persiste no histórico em memória e no banco
            conversation_history[user_id].append({"role": "user", "content": user_text})
            conversation_history[user_id].append({"role": "assistant", "content": text_out})
            _save_message(user_id, "user", user_text)
            _save_message(user_id, "assistant", text_out)
            await update.message.reply_text(text_out)
        else:
            await update.message.reply_text("Não consegui formular uma resposta. Pode reformular a pergunta?")

    except Exception as e:
        err_str = str(e)
        logger.error(f'ERRO CRÍTICO NA CONSULTA IA: {err_str}', exc_info=True)
        if '429' in err_str or 'rate_limit' in err_str.lower():
            await update.message.reply_text('⚠️ Limite da API de IA atingido no momento. Tente novamente em alguns minutos.')
        else:
            await update.message.reply_text('Tive um problema técnico ao processar sua resposta. Por favor, tente novamente em instantes.')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gere o ciclo de vida do bot e da API"""
    # Inicializa banco de dados
    try:
        _setup_db()
        logger.info("Banco de dados inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")

    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN ausente!")
        yield
        return

    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler('start', start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    logger.info(">>> SOFIA ONLINE <<<")

    yield

    # Shutdown sequence
    try:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)


@app.get('/')
def health_check():
    return {
        "status": "active",
        "engine": f"groq/{GROQ_MODEL}",
        "groq_ready": client is not None,
        "skills": ["brand_identity", "lead_qualify", "proposals", "onboarding"]
    }


def _free_port(port: int):
    """Mata qualquer processo que esteja ocupando a porta informada."""
    import subprocess, signal
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.strip().rsplit(None, 1)
                if parts:
                    pid = int(parts[-1])
                    if pid > 0:
                        try:
                            os.kill(pid, signal.SIGTERM)
                            logger.info(f"Processo antigo (PID {pid}) na porta {port} encerrado.")
                            import time; time.sleep(1)
                        except Exception as e:
                            logger.warning(f"Não foi possível matar PID {pid}: {e}")
    except Exception as e:
        logger.warning(f"_free_port: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    _free_port(port)
    uvicorn.run(app, host="0.0.0.0", port=port)
