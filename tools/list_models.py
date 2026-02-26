import os
from pathlib import Path
import sys

def load_env_key(key_name):
    p = Path('.env')
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.strip().startswith(key_name + '='):
            return line.split('=',1)[1].strip()
    return None

def main():
    api_key = os.environ.get('GEMINI_API_KEY') or load_env_key('GEMINI_API_KEY') or load_env_key('GOOGLE_API_KEY')
    if api_key:
        os.environ['GOOGLE_API_KEY'] = api_key
        os.environ['GEMINI_API_KEY'] = api_key

    printed = False
    # Try modern SDK first
    try:
        import google.genai as gen
        print('SDK: google.genai')
        models = gen.Models.list()
        for m in models:
            print(m.name)
        printed = True
    except Exception as e:
        print('google.genai failed:', e)

    # Try deprecated SDK
    try:
        import google.generativeai as gga
        print('\nSDK: google.generativeai')
        for m in gga.list_models():
            try:
                print(getattr(m, 'name', m))
            except Exception:
                print(m)
        printed = True
    except Exception as e:
        print('google.generativeai failed:', e)

    if not printed:
        print('\nNo SDK returned model list. Check GEMINI_API_KEY and network.')

if __name__ == '__main__':
    main()
