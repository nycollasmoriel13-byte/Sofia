# Bypass de Webhook Stripe (DEV)

Este documento explica como usar o bypass de verificação de assinatura do Stripe durante desenvolvimento local.

## Quando usar
- Desenvolvimento local sem HTTPS/SSL.
- Testes rápidos da pipeline de onboarding (checkout.session.completed) sem configurar o `STRIPE_WEBHOOK_SECRET`.

## Como ativar (local)
- PowerShell (somente sessão atual):

```powershell
$env:DEV_SKIP_STRIPE_SIG = "1"
python app.py
```

- CMD (Windows):

```cmd
set DEV_SKIP_STRIPE_SIG=1 && python app.py
```

- Alternativa: coloque `DEV_SKIP_STRIPE_SIG=1` temporariamente no seu `.env` local (NUNCA comitar o `.env`).

## Como desativar (recomendações)
- Pare o processo do `app.py` e reinicie sem a variável:

```powershell
# Parar processos Python do projeto (ajustar filtro conforme necessário)
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'python' -and $_.CommandLine -match 'COSTRUÇÃO BOT WPP') }
if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }

# Iniciar sem variável
python app.py
```

## Testando com assinatura real (recomendado antes de produção)
1. Configure `STRIPE_WEBHOOK_SECRET` no `.env` do servidor.
2. Use o `stripe` CLI para enviar um evento de teste com assinatura:

```bash
stripe listen --forward-to localhost:8000/webhook/stripe
# noutra shell, crie um evento de Checkout
stripe trigger checkout.session.completed
```

## Avisos de segurança
- Não deixe `DEV_SKIP_STRIPE_SIG=1` em servidores expostos.
- Proteja o `.env` e as chaves do Stripe com segredos do provider (e.g., Vault).

## Exemplo rápido: script de teste
- Veja `test_stripe.py` na raiz para um exemplo de payloads que usamos para testes locais.

---
Documentado automaticamente pelo assistente de integração.
