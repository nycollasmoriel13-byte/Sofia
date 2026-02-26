@echo off
echo 🚀 Iniciando configuracao local da SOFIA...

:: 1. Criar ambiente virtual se nao existir
if not exist .venv (
    echo [1/4] Criando ambiente virtual...
    python -m venv .venv
)

:: 2. Ativar ambiente e atualizar pip
echo [2/4] Atualizando gerenciador de pacotes...
call .venv\Scripts\activate
python -m pip install --upgrade pip

:: 3. Instalar dependencias corrigidas
echo [3/4] Instalando bibliotecas (isso pode demorar um pouco)...
pip install stripe python-telegram-bot==21.10 openai fastapi uvicorn python-dotenv pandas streamlit httpx "numpy>=2.0.0" google-generativeai google-genai

:: 4. Inicializar Banco de Dados Local
echo [4/4] Configurando banco de dados SQLite local...
python setup_db.py --yes

echo.
echo ✅ CONFIGURACAO CONCLUIDA!
echo Para ligar a Sofia, digite: python app.py
pause
