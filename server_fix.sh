#!/bin/bash
set -euo pipefail

# server_fix.sh - Instala dependências no venv e reinicia o PM2 de forma segura
# Execute no servidor em /root/sofia: bash server_fix.sh

echo "== Entrando na pasta do projeto =="
cd /root/sofia

echo "== 1. Removendo processo antigo (se existir) =="
pm2 delete sofia-bot || true

echo "== 2. Atualizando repositório =="
git fetch origin
git reset --hard origin/main || git pull origin main || true

echo "== 3. Atualizando pip e instalando dependências no .venv =="
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -U google-generativeai python-telegram-bot openai python-dotenv httpx || true

echo "== 4. Verificando instalação do módulo openai =="
if ./.venv/bin/python -c "import openai" 2>/dev/null; then
  echo "OpenAI module found!"
else
  echo "ERRO: OpenAI não encontrado no .venv. Verifique a instalação." >&2
fi

echo "== 5. Iniciando o Bot via PM2 (usando python do venv) =="
pm2 start /root/sofia/.venv/bin/python --name "sofia-bot" -- app.py || pm2 start .venv/bin/python --name "sofia-bot" -- app.py

echo "== 6. Salvando configuração PM2 e exibindo logs (últimas 50 linhas) =="
pm2 save || true
sleep 2
pm2 logs sofia-bot --lines 50

echo "== Script finalizado =="
