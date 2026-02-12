# Spec — Auto-Venda (Especificação Técnica)

## Resumo

Documento técnico consolidado para implementação do MVP "Auto-Venda".
Contém: arquitetura, modelos de dados, endpoints Flask, orquestrador, integração de pagamentos, painel Streamlit, lista de arquivos a criar e modificar, e principais funções em Python.

## Objetivo

Fornecer um roadmap técnico e especificação de código para implementar o backend mínimo viável: capturar leads via WhatsApp/Telegram, conversar com LLM, gerar link de pagamento (50% entrada), confirmar via webhook e coletar briefing.

---

## Arquitetura (resumo)

- Canais (WhatsApp/Telegram) → Webhook receiver (Flask) → Orquestrador (serviço Python)
- Orquestrador → LLM (conversação + detecção de intenção)
- Orquestrador → Payment Provider (Stripe) para gerar links
- Webhook de pagamentos → atualiza DB e dispara envio de briefing
- DB central (SQLite para dev, PostgreSQL para produção)
- Painel administrativo (Streamlit)

---

## Modelos de Dados (arquivo sugerido: `models.py`)

Exemplo SQLAlchemy (pronto para SQLite/Postgres):

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    phone = Column(String(64), index=True, unique=False)
    channel = Column(String(32))  # 'whatsapp' or 'telegram'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    projects = relationship('Project', back_populates='client')

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    service_package = Column(String(100))
    price = Column(Float)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(50), default='lead')
    started_at = Column(DateTime)
    deadline = Column(DateTime)
    brief = Column(Text)
    proposal_pdf = Column(String(300))
    metadata = Column(Text)
    client = relationship('Client', back_populates='projects')

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    provider = Column(String(50))
    provider_payment_id = Column(String(200))
    amount = Column(Float)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MessageLog(Base):
    __tablename__ = 'message_logs'
    id = Column(Integer, primary_key=True)
    client_phone = Column(String(64), index=True)
    channel = Column(String(32))
    incoming = Column(Text)
    outgoing = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

---

## Endpoints principais (arquivo sugerido: `app.py`)

- `/webhook/telegram` — POST: recebe updates do Telegram (mapear para formato comum)
- `/webhook/whatsapp` — POST: recebe eventos WhatsApp (Meta/Twilio/WPPConnect)
- `/webhook/payment/stripe` — POST: webhook Stripe (verificar assinatura)
- `/health` — GET: health-check

Esqueleto de handler (pseudocódigo):

```python
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    update = request.json
    normalized = normalize_event('telegram', update)
    orchestrator.handle_event(normalized)
    return jsonify({'ok': True})

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    payload = request.json
    normalized = normalize_event('whatsapp', payload)
    orchestrator.handle_event(normalized)
    return '', 200

@app.route('/webhook/payment/stripe', methods=['POST'])
def stripe_webhook():
    # verificar assinatura
    event = verify_and_parse_stripe(request)
    payment_handler.handle_stripe_event(event)
    return '', 200
```

---

## Orquestrador (arquivo sugerido: `orchestrator.py`)

Principais responsabilidades:

- Normalizar eventos e manter sessão por contato
- Enviar mensagens/estado ao LLM
- Detectar intenção (heurística + fallback LLM)
- Ao aceitar compra: gerar payment link e enviar ao usuário
- Aguardar confirmação via webhook e criar `Project`

Funções principais (assinaturas):

```python
def normalize_event(channel: str, raw_event: dict) -> dict:
    """Retorna dicionário padrão: {phone, chat_id, text, attachments, raw} """

class Orchestrator:
    def __init__(self, session_store, llm_client, db):
        ...

    def handle_event(self, event: dict):
        # obter/abrir sessão, registrar mensagem, chamar LLM
        # detectar intenção e responder
        ...

    def detect_intent(self, text: str) -> str:
        # heurística simples + fallback LLM
        ...

    def send_payment_link(self, client, package_id, amount):
        # chama payment.create_stripe_payment_link -> envia mensagem
        ...
```

---

## Integração de Pagamentos (arquivo sugerido: `payment.py`)

Recomendações:

- Usar `stripe` SDK oficial
- Gerar `Checkout Session` ou `Payment Link` com metadados (client_phone, package, project tentative id)
- Proteger webhook usando `Stripe-Signature`

Exemplo:

```python
import stripe
stripe.api_key = os.getenv('STRIPE_SECRET')

def create_stripe_payment_link(amount_brl: float, description: str, metadata: dict) -> str:
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data':{
                'currency':'brl',
                'product_data':{'name':description},
                'unit_amount':int(amount_brl*100)
            },
            'quantity':1
        }],
        mode='payment',
        success_url=os.getenv('SUCCESS_URL'),
        cancel_url=os.getenv('CANCEL_URL'),
        metadata=metadata
    )
    return session.url

def verify_and_parse_stripe(request):
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET')
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    return event
```

---

## Geração de Proposta PDF (arquivo sugerido: `utils/pdf.py`)

Função mínima com `reportlab`:

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def make_proposal_pdf(path, client_name, proposal_text):
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont('Helvetica', 14)
    c.drawString(50, 800, f'Proposta - {client_name}')
    c.setFont('Helvetica', 10)
    c.drawString(50, 780, proposal_text)
    c.save()
```

---

## Painel Administrativo (arquivo sugerido: `dashboard.py` — Streamlit)

Elementos essenciais:

- Tela principais: Novos Leads, Projetos Ativos, Financeiro, Cliente Detalhes
- Conexão com DB via SQLAlchemy

Exemplo mínimo de execução:

```python
import streamlit as st
from models import SessionLocal

st.title('Auto-Venda — Painel')
with SessionLocal() as db:
    st.write('Novos leads')
    # query e exibição
```

---

## Sessões e estado (cache)

- Em desenvolvimento: usar SQLite + tabela `sessions` ou `message_logs` para manter contexto.
- Em produção: Redis para sessão/TTL e contexto curto.

Assinatura/estrutura de sessão sugerida:

{ 'phone': str, 'chat_id': str, 'context': [ {role, text, ts} ], 'last_intent': str }

---

## Segurança

- Não commitar chaves secretas; usar variáveis de ambiente (`STRIPE_SECRET`, `STRIPE_ENDPOINT_SECRET`, `OPENAI_API_KEY`)
- Verificar assinatura de webhooks (Stripe)
- Rate-limiting para endpoints públicos

---

## Arquivos a criar (prioridade alta)

- `app.py` — Flask app e endpoints
- `models.py` — SQLAlchemy models
- `db.py` — engine, SessionLocal, alembic config (opcional)
- `orchestrator.py` — lógica de orquestração e sessão
- `llm_client.py` — wrapper para OpenAI/Anthropic
- `payment.py` — integração Stripe
- `webhooks.py` — handlers e verificação de assinatura
- `utils/pdf.py` — geração de propostas
- `dashboard.py` — Streamlit painel
- `requirements.txt` — dependências

## Arquivos a modificar

- `scripts/filter_public_prices.py` — (opcional) integrar export para DB ou formatos que o painel consuma
- `chatbot_prices*.csv` — (opcional) carregar tabela de preços para seed (script de migração)

---

## Requisitos (sugestão `requirements.txt`)

- flask
- sqlalchemy
- psycopg2-binary (produção)
- stripe
- requests
- reportlab
- streamlit
- redis (opcional)
- python-dotenv

---

## Fluxos principais (resumo de funções)

1. Recebe evento (WhatsApp/Telegram) → `normalize_event()`
2. `Orchestrator.handle_event()` → abre/atualiza sessão; chama `llm_client.call()` com `system` prompt + contexto
3. `Orchestrator.detect_intent()` decide: `buy`, `question`, `support`, `unknown`
4. Se `buy` e usuário aceitar: `payment.create_stripe_payment_link()` com metadata (phone, package)
5. Usuário paga → Stripe webhook `checkout.session.completed` → `payment_handler` atualiza `Payment`, cria `Project` e envia formulário de briefing (URL)
6. Cliente preenche briefing → atualiza `Project.brief`; painel mostra projeto ativo e inicia contador

---

## Próximos passos sugeridos (implementação)

1. Criar `models.py` + configurar `db.py` (engine + SessionLocal).  
2. Implementar `app.py` com endpoints e `normalize_event` básico.  
3. Implementar `orchestrator.py` com sessão em memória/SQLite e integrá-lo com `llm_client.py` (mock inicial).  
4. Implementar `payment.py` com Stripe sandbox e webhook verificando assinatura.  
5. Criar `dashboard.py` minimal para visualizar leads/projetos.  

---

## Observações finais

- Especifique provedor de WhatsApp (Meta/Twilio/WPPConnect) para adaptar payloads do `normalize_event`.  
- Para desenvolvimento rápido: usar `SQLite` e `reportlab`+`stripe test keys`.  
- Quando aprovar Spec, posso implementar o skeleton (`app.py`, `models.py`, `orchestrator.py`, `payment.py`) e rodar testes locais.

---

Arquivo gerado automaticamente pela análise do `PRD.md` e organização das tarefas.
