#!/usr/bin/env bash
set -euo pipefail

# Script para limpar processos antigos, sincronizar código e reiniciar o bot + dashboard
# Execute isto no servidor (SSH) como root ou com permissões suficientes.

echo "== Parando e removendo todos os processos PM2 =="
pm2 stop all || true
pm2 delete all || true

echo "== Matando processos que ocupam a porta 8501 (fuser/lsof fallback) =="
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8501/tcp || true
else
  lsof -ti:8501 | xargs -r kill -9 || true
fi

REPO_DIR="/root/sofia"
if [ -d "$REPO_DIR" ]; then
  cd "$REPO_DIR"
else
  echo "Pasta $REPO_DIR não existe. Usando diretório actual: $(pwd)"
fi

echo "== Sincronizando código com origin/main =="
# Garante que usamos exatamente o que está no remote
git fetch origin
git reset --hard origin/main
git pull origin main || true

echo "== Instalando dependências no virtualenv .venv =="
if [ -x ".venv/bin/pip" ]; then
  .venv/bin/pip install -r requirements.txt
else
  echo ".venv/bin/pip não encontrado. Verifique o caminho do virtualenv e instale manualmente se necessário."
fi

echo "== Iniciando o bot com PM2 (app.py) =="
pm2 start .venv/bin/python --name "sofia-bot" -- app.py || true

echo "== Iniciando o dashboard com PM2 (streamlit) =="
pm2 start "streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0" --name "sofia-dashboard" || true

pm2 save || true

echo "== Status PM2 =="
pm2 ls || true

echo "Se ocorrerem erros, veja os logs:"
echo "  pm2 logs sofia-bot --lines 200"
echo "ou para o dashboard: pm2 logs sofia-dashboard --lines 200"

echo "Pronto. Abra o dashboard em http://<server-ip>:8501 e execute /start na Sofia."