#!/usr/bin/env bash
set -euo pipefail

# deploy.sh - automatiza pull, (re)criação do .venv, instalação de deps e reinício PM2
# Uso: no servidor, em /root/sofia:
#   curl -O https://raw.githubusercontent.com/nycollasmoriel13-byte/Sofia/main/deploy.sh
#   chmod +x deploy.sh
#   ./deploy.sh

REPO_DIR="/root/sofia"
if [ -d "$REPO_DIR" ]; then
  cd "$REPO_DIR"
else
  echo "Aviso: pasta $REPO_DIR não encontrada. Execute este script dentro do diretório do projeto." >&2
  exit 1
fi

echo "== 1. Atualizando repositório =="
git fetch origin
git reset --hard origin/main || true
git pull origin main || true

# Optional: recreate venv if requested by env var RECREATE_VENV=1
if [ "${RECREATE_VENV:-0}" = "1" ]; then
  echo "== 2. Recriando .venv (destrutivo) =="
  rm -rf .venv
  python3 -m venv .venv
fi

# Ensure venv exists
if [ ! -x ".venv/bin/python" ]; then
  echo "== Criando .venv =="
  python3 -m venv .venv
fi

echo "== 3. Ativando .venv e atualizando pip =="
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

# Install from requirements.txt if present, else install core deps
if [ -f requirements.txt ]; then
  echo "== Instalando pacotes de requirements.txt =="
  python -m pip install -r requirements.txt
else
  echo "== requirements.txt não encontrado — instalando pacotes essenciais =="
  python -m pip install fastapi uvicorn google-genai google-generativeai python-telegram-bot stripe openai pandas streamlit httpx python-dotenv
fi

# Ensure SDKs updated (user asked to include update)
echo "== 4. Garantindo SDKs do Google atualizados =="
python -m pip install -U google-genai google-generativeai || true

# Deactivate venv for safety during PM2 operations
deactivate || true

echo "== 5. Limpeza PM2 e reinício de serviços =="
pm2 delete sofia-bot || true
pm2 delete sofia-dashboard || true

# Start services using ecosystem and explicit streamlit command
if [ -f ecosystem.config.js ]; then
  pm2 start ecosystem.config.js || true
fi

# Start dashboard using venv python -m streamlit
pm2 start "$REPO_DIR/.venv/bin/python" --name "sofia-dashboard" -- -m streamlit run "$REPO_DIR/dashboard.py" --server.port 8501 --server.address 0.0.0.0 || true

# Start bot (ecosystem should have started it; fallback to explicit start)
pm2 start "$REPO_DIR/.venv/bin/python" --name "sofia-bot" -- "$REPO_DIR/app.py" || true

pm2 save || true

echo "== 6. Status PM2 =="
pm2 ls || pm2 status || true

echo "== 7. Últimas linhas dos logs (bot + dashboard) =="
pm2 logs sofia-bot --lines 50 --no-daemon & sleep 1 || true
pm2 logs sofia-dashboard --lines 50 --no-daemon & sleep 1 || true

echo "Deploy concluído. Se algo falhar, verifique 'pm2 logs sofia-bot' e 'pm2 logs sofia-dashboard'."
