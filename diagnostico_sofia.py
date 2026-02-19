import os
import asyncio
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception as e:
    genai = None

try:
    from telegram import Bot
except Exception as e:
    Bot = None

load_dotenv()

async def test_services():
    print("--- INICIANDO TESTE DE DIAGNÓSTICO ---")

    # 1. Testar Gemini
    try:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Gemini: GEMINI_API_KEY não encontrada no .env")
        elif not genai:
            print("Gemini: biblioteca google-generativeai não está instalada")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # run in thread in case it's blocking
            resp = await asyncio.to_thread(lambda: model.generate_content("Olá, responda apenas 'IA OK'"))
            text = getattr(resp, 'text', None) or (getattr(resp, 'candidates', [None])[0] and getattr(resp.candidates[0], 'content', None))
            print(f"Status Gemini: {text}")
    except Exception as e:
        print(f"Erro no Gemini: {e}")

    # 2. Testar Telegram
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        if not token:
            print("Telegram: TELEGRAM_BOT_TOKEN não encontrada no .env")
        elif not Bot:
            print("Telegram: python-telegram-bot não está instalado")
        else:
            bot = Bot(token=token)
            me = await bot.get_me()
            print(f"Status Telegram: Conectado como @{me.username}")
    except Exception as e:
        print(f"Erro no Telegram: {e}")

if __name__ == '__main__':
    asyncio.run(test_services())
