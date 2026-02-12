# Guia de Inicialização - Sofia V1.0

Siga estes passos para colocar sua Agência de Automação online agora.

## 1. Configuração do Ambiente (`.env`)

Crie ou edite o arquivo `.env` na raiz do projeto com as chaves que você já possui (NÃO COMITE este arquivo). Abaixo há um exemplo pronto — copie para `.env` e preencha os valores:

```dotenv
# --- TOKENS ---
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# --- STRIPE ---
STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=YOUR_STRIPE_WEBHOOK_SECRET

# --- PRICE IDS (Reais) ---
STRIPE_PRICE_ATENDIMENTO=price_ID_DO_PRODUTO_1
STRIPE_PRICE_SECRETARIA=price_ID_DO_PRODUTO_2
STRIPE_PRICE_ECO=price_ID_DO_PRODUTO_3

# --- REDIRECIONAMENTO ---
SUCCESS_URL=https://t.me/AssistenteVirtualSofia_bot?start=sucesso
CANCEL_URL=https://t.me/AssistenteVirtualSofia_bot?start=cancelado
```

> Observação: substitua os placeholders `price_ID_DO_PRODUTO_*` pelos Price IDs reais do Stripe.

---

## 2. Checklist de Comandos (Terminal)

Execute na ordem exata.

### Passo 1: Limpar e Preparar o Banco de Dados

Este comando remove os testes antigos e cria a estrutura para o Telegram.

```bash
python setup_db.py --yes
```

### Passo 2: Iniciar a Sofia (Backend + Bot)

Abra um terminal e rode o comando abaixo. Ele ligará o cérebro da Sofia e a conexão com o Telegram.

```bash
python main.py
```

ou com uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Passo 3: Iniciar o Dashboard Admin

Abra um segundo terminal e rode o painel visual.

```bash
streamlit run dashboard.py
```

---

## 3. Observações Rápidas

- Configure o Webhook do Stripe apontando para `https://<seu-host>/webhook/stripe` e cole o `STRIPE_WEBHOOK_SECRET` no `.env`.
- Não compartilhe seu `.env` publicamente.
- Se quiser um `README.md` completo com passo-a-passo de deploy (Heroku/DigitalOcean), eu posso gerar em seguida.
 
# Guia de Inicialização - Sofia V1.0

Siga estes passos para colocar sua Agência de Automação online agora.

## 1. Configuração do Ambiente (`.env`)

Crie ou edite o arquivo `.env` na raiz do projeto com as chaves que você já possui (NÃO COMITE este arquivo). Abaixo há um exemplo pronto — copie para `.env` e preencha os valores:

```dotenv
# --- TOKENS ---
OPENAI_API_KEY=sua_chave_openai_aqui
TELEGRAM_BOT_TOKEN=SEU_TELEGRAM_BOT_TOKEN_AQUI

# --- STRIPE ---
STRIPE_SECRET_KEY=sk_test_SUA_CHAVE_AQUI
STRIPE_WEBHOOK_SECRET=whsec_...  # Obtenha no painel do Stripe após configurar o webhook

# --- PRICE IDS (Reais) ---
STRIPE_PRICE_ATENDIMENTO=price_ID_DO_PRODUTO_1
STRIPE_PRICE_SECRETARIA=price_ID_DO_PRODUTO_2
STRIPE_PRICE_ECO=price_ID_DO_PRODUTO_3

# --- REDIRECIONAMENTO ---
SUCCESS_URL=https://t.me/AssistenteVirtualSofia_bot?start=sucesso
CANCEL_URL=https://t.me/AssistenteVirtualSofia_bot?start=cancelado
```

> Observação: substitua os placeholders `price_ID_DO_PRODUTO_*` pelos Price IDs reais do Stripe.

---

# Guia de Inicialização - Sofia V1.0

Siga estes passos para colocar sua Agência de Automação online agora.

## 1. Configuração do Ambiente (`.env`)

Crie ou edite o arquivo `.env` na raiz do projeto com as chaves que você já possui (NÃO COMITE este arquivo). Abaixo há um exemplo pronto — copie para `.env` e preencha os valores:

```dotenv
# --- TOKENS ---
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# --- STRIPE ---
STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=YOUR_STRIPE_WEBHOOK_SECRET

# --- PRICE IDS (Reais) ---
STRIPE_PRICE_ATENDIMENTO=price_ID_DO_PRODUTO_1
STRIPE_PRICE_SECRETARIA=price_ID_DO_PRODUTO_2
STRIPE_PRICE_ECO=price_ID_DO_PRODUTO_3

# --- REDIRECIONAMENTO ---
SUCCESS_URL=https://t.me/AssistenteVirtualSofia_bot?start=sucesso
CANCEL_URL=https://t.me/AssistenteVirtualSofia_bot?start=cancelado
```

> Observação: substitua os placeholders `price_ID_DO_PRODUTO_*` pelos Price IDs reais do Stripe.

---

## 2. Checklist de Comandos (Terminal)

Execute na ordem exata.

### Passo 1: Limpar e Preparar o Banco de Dados

Este comando remove os testes antigos e cria a estrutura para o Telegram.

```bash
python setup_db.py --yes
```

### Passo 2: Iniciar a Sofia (Backend + Bot)

Abra um terminal e rode o comando abaixo. Ele ligará o cérebro da Sofia e a conexão com o Telegram.

```bash
python main.py
```

ou com uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Passo 3: Iniciar o Dashboard Admin

Abra um segundo terminal e rode o painel visual.

```bash
streamlit run dashboard.py
```

---

## 3. Observações Rápidas

- Configure o Webhook do Stripe apontando para `https://<seu-host>/webhook/stripe` e cole o `STRIPE_WEBHOOK_SECRET` no `.env`.
- Não compartilhe seu `.env` publicamente.
- Se quiser um `README.md` completo com passo-a-passo de deploy (Heroku/DigitalOcean), eu posso gerar em seguida.
## 2. Checklist de Comandos (Terminal)

