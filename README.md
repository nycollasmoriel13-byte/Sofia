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
