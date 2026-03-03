# Roteiro de Finalização e Segurança

Este documento descreve os passos finais para limpar o repositório, testar localmente o webhook do Stripe e garantir boas práticas para produção.

## 1) Objetivo

- Garantir que ficheiros sensíveis e artefatos locais não são rastreados pelo Git.
- Permitir testes locais do webhook Stripe sem quebrar a segurança em produção.

## 2) Variável de desenvolvimento

Para permitir testes locais sem verificação de assinatura do Stripe, adicione ao seu `.env` local (NUNCA commit):

```bash
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

```text
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

Plano Mestre Atualizado
26 de fev., 20:47

Com este guia atualizado e o `setup_db.py` sincronizado, o projeto está oficialmente fechado e pronto para o deploy.

Projeto: Agência de Automação "Auto-Venda" (Consolidado)

Objetivo: Vender soluções de automação via atendimento 100% automatizado, com gestão administrativa centralizada.

🛠️ Stack Tecnológica (Final)

Linguagem: Python 3.10+

Cérebro: Google Gemini 1.5 Flash

Canal: Telegram (Bot API)

Pagamentos: Stripe (Checkout Sessions + Webhooks)

Banco de Dados: SQLite (agencia_autovenda.db)

🛡️ Protocolo de Segurança e Produção (Crítico)

Para garantir que o sistema funcione corretamente tanto em teste como em produção, segue a regra de ouro para o ficheiro .env:

Variável DEV_SKIP_STRIPE_SIG

Esta variável controla a verificação de assinatura dos Webhooks do Stripe.

Ambiente de Desenvolvimento (Local):

Defina DEV_SKIP_STRIPE_SIG=1.

Porquê: Permite testar pagamentos usando scripts como o test_stripe.py sem precisar de HTTPS/SSL.

Ambiente de Produção (DigitalOcean/VPS):

Defina DEV_SKIP_STRIPE_SIG=0 (ou remova a linha).

Porquê: Garante que apenas o Stripe pode confirmar pagamentos, evitando ataques de falsificação.

💾 Manutenção da Base de Dados

Sempre que precisar de um início limpo (reset), utilize o script de setup:

```powershell
python setup_db.py
```

Atenção: Isto apagará todos os leads e assinaturas existentes.

📈 Fluxo de Trabalho Diário

Verificar Logs: pm2 logs sofia-bot

Atualizar Código: git pull origin main -> pm2 restart sofia-bot

Monitorizar Leads: Aceder ao Dashboard: [http://teu-ip/dashboard](http://teu-ip/dashboard)

Sofia V1.0 - Pronta para Escalar.

## Testes locais: Bypass de verificação de assinatura do Stripe (apenas para DEV)

AVISO: Use este bypass somente em ambientes de desenvolvimento locais. Nunca habilite em produção nem em servidores públicos.

Quando estiver a desenvolver localmente e não quiser configurar HTTPS e o `STRIPE_WEBHOOK_SECRET`, pode usar uma variável de ambiente para desabilitar temporariamente a verificação de assinatura:

PowerShell (sessão atual):

```powershell
$env:DEV_SKIP_STRIPE_SIG = "1"
python app.py
```

CMD (Windows):

```cmd
set DEV_SKIP_STRIPE_SIG=1 && python app.py
```

Como funciona:
- `DEV_SKIP_STRIPE_SIG=1` instrui o handler do webhook a ignorar a verificação de assinatura do Stripe (apenas dentro do processo em execução).
- O valor deve estar presente na sessão que inicia `app.py`; reinicie o processo sempre que alterar o `.env`.

Riscos e boas práticas:
- Nunca coloque `DEV_SKIP_STRIPE_SIG=1` no `.env` de produção.
- Proteja o ficheiro `.env` com permissões adequadas e não o comite.
- Antes de colocar o sistema em produção, defina `DEV_SKIP_STRIPE_SIG=0` ou remova a chave e adicione o `STRIPE_WEBHOOK_SECRET` real.

Reverter para modo seguro (produção):

```powershell
# Parar o processo e reiniciar sem a variável
Stop-Process -Name python -Force
python app.py
```

Validação final com Stripe (recomendado):
- Configure `STRIPE_WEBHOOK_SECRET` no `.env` do servidor.
- Teste usando o `stripe` CLI ou criando um `checkout.session.completed` no painel do Stripe em modo Test.

Arquivo de referência de testes: consulte [docs/stripe_bypass.md](docs/stripe_bypass.md) para exemplos e automações pequenas.
