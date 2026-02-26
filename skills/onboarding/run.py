import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Optional, List, Tuple

DB_NAME = os.getenv('DB_NAME', 'agencia_autovenda.db')


def setup_onboarding_table():
    """Garante que a tabela de onboarding existe com os campos necessários."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS onboarding_data (
            user_id TEXT PRIMARY KEY,
            whatsapp_contato TEXT,
            website_cliente TEXT,
            objetivos_ia TEXT,
            data_coleta TEXT,
            status_configuracao TEXT DEFAULT 'pendente'
        )
    ''')
    conn.commit()
    conn.close()


def _get_subscription_status(user_id: str) -> Optional[str]:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM assinaturas WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _extract_whatsapp(text: str) -> Optional[str]:
    m = re.search(r"(\+?\d[\d\s\-()]{7,20}\d)", text)
    if m:
        return re.sub(r"[\s\-()]+", "", m.group(1))
    return None


def _extract_website(text: str) -> Optional[str]:
    m = re.search(r"(https?://[^\s]+)", text)
    if m:
        return m.group(1)
    m2 = re.search(r"([\w\-]+\.(com|com.br|net|org|io|tech)(/[^\s]*)?)", text, re.IGNORECASE)
    if m2:
        return m2.group(1)
    return None


def _extract_objetivos(text: str) -> Optional[str]:
    txt = text.strip()
    if len(txt) < 6:
        return None
    parts = [p.strip() for p in re.split(r"[\n;]+|,\s*", txt) if p.strip()]
    if not parts:
        return None
    return "; ".join(parts[:5])


def run(user_id: str, message_text: str, history: List[Tuple[str, str]] = None):
    """
    Processa a conversa de onboarding.
    Retorna JSON estruturado com status e instruções de follow-up.
    """
    history = history or []
    setup_onboarding_table()

    # 1. Verificar assinatura
    status = _get_subscription_status(user_id)
    if not status or status != 'ativo':
        return {"status": "bloqueado", "message": "Onboarding não permitido. Assinatura não identificada como ativa."}

    # 2. Combina texto recente para extração
    combined = message_text + "\n" + "\n".join([m for _, m in (history[-6:] if history else [])])

    whatsapp = _extract_whatsapp(combined)
    website = _extract_website(combined)
    objetivos = _extract_objetivos(combined)

    missing = []
    if not whatsapp:
        missing.append('whatsapp')
    if not website:
        missing.append('website')
    if not objetivos:
        missing.append('objetivos')

    if missing:
        return {
            "status": "em_progresso",
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "missing": missing,
            "json_output": {
                "prompt_instructions": "Extraia [whatsapp, website, objetivos] da mensagem do usuário.",
                "next_step": "Verificar campos ausentes e perguntar ao usuário."
            }
        }

    # 3. Salvamento final (upsert)
    result = salvar_dados_finais(user_id, whatsapp, website, objetivos)
    return result


def salvar_dados_finais(user_id: str, whatsapp: str, site: str, objetivos: str):
    """Insere ou atualiza os dados de onboarding do usuário."""
    try:
        setup_onboarding_table()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO onboarding_data (user_id, whatsapp_contato, website_cliente, objetivos_ia, data_coleta)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                whatsapp_contato=excluded.whatsapp_contato,
                website_cliente=excluded.website_cliente,
                objetivos_ia=excluded.objetivos_ia,
                data_coleta=excluded.data_coleta
        ''', (user_id, whatsapp, site, objetivos, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return {"status": "completo", "message": "Dados de onboarding salvos com sucesso!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # Teste local rápido
    test_user = 'test_onb'
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS assinaturas (user_id TEXT PRIMARY KEY, status TEXT, plano TEXT)')
        cur.execute('INSERT OR REPLACE INTO assinaturas (user_id, status, plano) VALUES (?, ?, ?)', (test_user, 'ativo', 'flash'))
        conn.commit()
        conn.close()
    except Exception:
        pass

    print(run(test_user, 'Meu WhatsApp é +55 (11) 91234-5678. Site: https://meusite.com. Objetivos: aumentar leads, automatizar agendamentos, melhorar atendimento.', []))
