# Roteiro de Finalização e Segurança

Este documento descreve os passos finais para limpar o repositório, testar localmente o webhook do Stripe e garantir boas práticas para produção.

## 1) Objetivo

- Garantir que ficheiros sensíveis e artefatos locais não são rastreados pelo Git.
- Permitir testes locais do webhook Stripe sem quebrar a segurança em produção.

## 2) Variável de desenvolvimento

Para permitir testes locais sem verificação de assinatura do Stripe, adicione ao seu `.env` local (NUNCA commit):

```
DEV_SKIP_STRIPE_SIG=1
```

Uso temporário na sessão PowerShell (ex.: para testes):

```powershell
# definir temporariamente na sessão
$env:DEV_SKIP_STRIPE_SIG='1'
```

Em produção, remova ou defina para `0`.

## 3) Verificações rápidas antes de testar

- Confirme que `.gitignore` contém:

```
__pycache__/
*.db
.env
*.pyc
```

- Verifique que `.env` NÃO está rastreado:

```powershell
git ls-files --error-unmatch .env 2>$null || Write-Output ".env not tracked"
```

## 4) Testar o fluxo local (webhook)

1. Ative o `venv`:

```powershell
.venv\Scripts\Activate.ps1
```

2. Inicie o `app.py` (em background opcional):

```powershell
# opcional: parar processos antigos
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'app.py' }
if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }

# iniciar em background
Start-Process -FilePath .venv\Scripts\python.exe -ArgumentList 'app.py' -NoNewWindow
Start-Sleep -Seconds 2
```

3. Execute o script de teste (o script cria o lead e dispara o webhook):

```powershell
# defina a URL se necessário
$env:WEBHOOK_STRIPE_URL='http://localhost:8000/webhook/stripe'
python tools/test_onboarding_flow.py
```

Esperado: resposta HTTP `200` e o registo em `assinaturas` com `status = 'ativo'`.

## 5) Verificar no banco de dados

Comando rápido para checar o status do user test:

```powershell
python -c "import sqlite3; conn=sqlite3.connect('agencia_autovenda.db'); print(conn.execute('SELECT user_id,status FROM assinaturas WHERE user_id=?', ('123456789',)).fetchone()); conn.close()"
```

## 6) Commit / Push final

1. Commit das alterações de código (não inclua `.env`):

```powershell
git add .
git commit -m "chore: limpeza de ambiente, ignore de sensíveis e correção de webhook"
```

2. Publicar no remoto:

```powershell
git push origin main
```

## 7) Boas práticas para produção

- Nunca defina `DEV_SKIP_STRIPE_SIG=1` em produção.
- Configure `STRIPE_WEBHOOK_SECRET` no ambiente do servidor (DigitalOcean, Heroku, etc.).
- Considere usar `ENV=production|development` para controlar comportamento no `app.py`.

## 8) Troubleshooting

- Se receber `{'status':'invalid'}` verifique nos logs do `app.py` a razão (`missing_client_reference_id`, `user_not_found` ou `db_error`).
- Se o webhook não chegar, confirme a URL e a porta onde o Flask está a correr (`WEBHOOK_PORT`/`WEBHOOK_HOST`).

---

Se preferires, eu faço o `git push` por ti depois do commit. Caso prefiras, executa `git push origin main` localmente.
# Auto-Venda — Cérebro (FastAPI)

Rápido esqueleto para receber webhooks da Evolution API e responder usando
Gemini (Google Generative AI).

Como executar (ambiente Windows):

1. Crie um virtualenv e ative:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

1. Instale dependências:

```powershell
pip install -r requirements.txt
```

1. Configure variáveis de ambiente (opcionais):

```powershell
$env:EVOLUTION_API_URL = 'http://localhost:8080'
$env:EVOLUTION_API_KEY = 'sua_api_key_aqui'
$env:EVOLUTION_INSTANCE = 'sua_instancia'
$env:GEMINI_API_KEY = 'sua_gemini_key'
```

1. Rode localmente:

```powershell
python app.py
```

Pontos importantes:

- Ajuste `EVOLUTION_INSTANCE` para o nome da sua instância na Evolution API.
- Para desenvolvimento, use chaves de teste apropriadas e atente para quotas
  da API.
