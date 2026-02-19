# Guia de Inicialização — Sofia Bot v2.0

Este documento descreve como manter, reiniciar e diagnosticar a Sofia na VPS.

## Comandos de Manutenção

**Status**: Verifica estados do PM2

```bash
ssh root@67.205.183.59 "pm2 status"
```

**Ver logs em tempo real**:

```bash
ssh root@67.205.183.59 "pm2 logs sofia-bot"
```

**Reiniciar o bot**:

```bash
ssh root@67.205.183.59 "pm2 restart sofia-bot"
```

**Reiniciar (forçar reinício completo)**:

```bash
ssh root@67.205.183.59 "pm2 delete sofia-bot || true; cd /root/sofia && source .venv/bin/activate && pm2 start main.py --name sofia-bot --interpreter python3"
```

## Estrutura de Arquivos na VPS

- Projeto: `/root/sofia/`
- Arquivos principais:
  - [main.py](main.py) — Código principal (FastAPI + Telegram + Gemini).
  - [.env](.env) — Variáveis de ambiente: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`.
  - `.venv/` — Ambiente virtual Python usado para execução.

## Resolução de Problemas Comuns

### Erro: "This Application was not initialized"

Causa: a inicialização do `Application`/`Updater` do `python-telegram-bot` ocorreu fora da ordem ou antes do FastAPI estar pronto.

Ação: garantir que o `main.py` usa o evento de `startup` do FastAPI e chama `await telegram_app.initialize()` seguido de `await telegram_app.start()` (a versão atual do `main.py` já faz isso).

### Erro: "Gemini API Key missing"

Verifique se `.env` contém a chave correta:

```bash
ssh root@67.205.183.59 "cat /root/sofia/.env"
```

### Erro: model not found / 404 para `gemini-1.5-flash`

Causa: modelo não disponível na API/versão instalada.

Ação rápida: testar modelos disponíveis com um pequeno script Python (ex.: `gemini-1.5-mini`) ou executar ListModels (abaixo).

## Como atualizar o código (workflow seguro)

1. Editar `main.py` localmente.

1. Enviar para a VPS (exemplo com `scp`):

```bash
scp main.py root@67.205.183.59:/root/sofia/main.py
```

1. Reiniciar o PM2:

```bash
ssh root@67.205.183.59 "cd /root/sofia && source .venv/bin/activate && pm2 restart sofia-bot --update-env"
```

1. Verificar logs para confirmar startup:

```bash
ssh root@67.205.183.59 "pm2 logs sofia-bot --lines 100"
```

## Comandos auxiliares úteis

**Conferir `pm2` status e últimas linhas de log**:

```bash
ssh root@67.205.183.59 "pm2 status && pm2 logs sofia-bot --lines 50"
```

**Teste rápido de modelos Gemini (executar na VPS dentro do `.venv`)**:

```bash
# conecte-se à VPS e ative o ambiente
ssh root@67.205.183.59
source /root/sofia/.venv/bin/activate

# script Python inline para listar modelos (requer google-genai instalado)
python3 - <<'PY'
import os
try:
    from google import genai
    c = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    infos = c.list_models().model_infos
    for m in infos:
        print(m.name)
except Exception as e:
    print('Erro ao listar modelos:', e)
PY
```

> Observação: a API cliente pode variar (`google.genai` vs `google.generativeai`). Adapte o snippet conforme o cliente instalado na `.venv`.

## Logs e mensagens relevantes para diagnóstico

Se o bot falhar ao iniciar, procure por mensagens no log de erro do PM2 como:

- `SyntaxError: unmatched '}'` — arquivo corrompido (reinstalar `main.py`).
- `API_KEY_INVALID` — chave GEMINI inválida/ausente.
- `404 models/... is not found` — modelo incompatível; rode ListModels.
- `This Application was not initialized` — ordem de inicialização incorreta.

## Checklist rápido (quando algo falhar)

- [ ] `pm2 status` mostra `sofia-bot` como `online`?
- [ ] `.env` contém `TELEGRAM_BOT_TOKEN` e `GEMINI_API_KEY` corretos?
- [ ] `main.py` não está corrompido (sem `SyntaxError`)?
- [ ] Dependências instaladas em `.venv` (`pip install -r requirements.txt`)?

## Próximos passos sugeridos

- Enviar uma mensagem de teste para o bot e monitorar os logs para confirmar geração e envio.
- Caso apareça `model not found`, rodar o comando de listagem de modelos e atualizar `GEMINI_MODEL` em `.env`/`main.py`.

---
Sofia Intelligence — Agência Auto‑Venda
Versão do guia: 2.0
Criado automaticamente — se quiser, atualizo e envio instruções para reiniciar e verificar em tempo real.
