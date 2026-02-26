import os
from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv('GEMINI_API_KEY')
print('Using GEMINI_API_KEY set?', bool(KEY))

def try_google_generativeai():
    try:
        import google.generativeai as genai
    except Exception as e:
        print('google.generativeai import failed:', e)
        return

    try:
        genai.configure(api_key=KEY)
    except Exception as e:
        print('genai.configure failed:', e)

    print('\n--- google.generativeai models ---')
    try:
        models_iter = genai.list_models()
        # genai.list_models returns a generator; iterate and print
        for m in models_iter:
            try:
                name = getattr(m, 'name', None) or m.get('name') if isinstance(m, dict) else str(m)
            except Exception:
                name = str(m)
            print('-', name)
    except Exception as e:
        print('genai.list_models() failed:', e)

def try_google_genai():
    try:
        import google.genai as gen
    except Exception as e:
        print('google.genai import failed or not installed:', e)
        return

    print('\n--- google.genai models ---')
    try:
        from google.genai import client as genclient
        c = genclient.Client()
        # attempt to call list_models if available
        if hasattr(c, 'list_models'):
            res = c.list_models()
            # res may be iterable
            for m in res:
                print('-', m)
        else:
            print('genai.Client has no list_models method; available attrs:', [a for a in dir(c) if not a.startswith('_')])
    except Exception as e:
        print('google.genai list_models failed:', e)

if __name__ == '__main__':
    try_google_generativeai()
    try_google_genai()
    print('\nIf you see model names like "gemini-1.5-flash", set that exact value in GEMINI_MODEL in .env and restart the bot.')
