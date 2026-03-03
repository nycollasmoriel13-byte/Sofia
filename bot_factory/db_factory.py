"""
db_factory.py — Setup e acesso ao banco de dados da fábrica de bots.
Cria as tabelas exclusivas do factory (bots_gerados, skills_performance, feedback_bots)
no mesmo DB principal do projeto.
"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.getenv("DB_NAME", "agencia_autovenda.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_factory_tables():
    """Garante que as tabelas do factory existem no DB principal."""
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        -- Registro de cada bot gerado
        CREATE TABLE IF NOT EXISTS bots_gerados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT UNIQUE NOT NULL,
            plano         TEXT,
            nicho         TEXT,
            plataforma    TEXT,
            skills_usadas TEXT,          -- JSON: lista de nome de skills
            prompt_hash   TEXT,          -- hash rápido do prompt (evita rebuild desnecessário)
            bot_path      TEXT,          -- caminho absoluto do bot.py gerado
            config_path   TEXT,          -- caminho do config.json gerado
            pid           INTEGER,       -- PID do processo rodando (NULL se parado)
            status        TEXT DEFAULT 'building',  -- building | active | error | stopped
            score         REAL DEFAULT 0.0,
            erro_msg      TEXT,
            data_deploy   TEXT,
            data_ultimo_start TEXT,
            total_mensagens INTEGER DEFAULT 0
        );

        -- Pontuação de skills por nicho — motor de aprendizado
        CREATE TABLE IF NOT EXISTS skills_performance (
            nicho              TEXT NOT NULL,
            skill_name         TEXT NOT NULL,
            total_usos         INTEGER DEFAULT 0,
            media_satisfacao   REAL DEFAULT 5.0,
            taxa_retencao      REAL DEFAULT 0.5,
            taxa_escalacao     REAL DEFAULT 0.2,   -- % de msgs que geram transbordo (menor = melhor)
            ultima_atualizacao TEXT,
            PRIMARY KEY (nicho, skill_name)
        );

        -- Log de feedback para refinamento
        CREATE TABLE IF NOT EXISTS feedback_bots (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_user_id  TEXT,
            tipo         TEXT,  -- 'sem_resposta' | 'escalacao' | 'satisfacao' | 'erro'
            conteudo     TEXT,
            data         TEXT
        );
    """)
    conn.commit()
    conn.close()


def get_pending_clients():
    """
    Retorna clientes ativos que ainda não têm bot gerado ou cujo bot está em erro genérico.
    Exclui status 'aguardando_token' para não repetir tentativas sem o token.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.* FROM assinaturas a
        LEFT JOIN bots_gerados b ON a.user_id = b.user_id
        WHERE a.status = 'ativo'
          AND (b.user_id IS NULL OR b.status = 'error')
          AND (b.status IS NULL OR b.status != 'aguardando_token')
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_bot_record(user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bots_gerados WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_bot_record(user_id: str, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    existing = get_bot_record(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    kwargs["user_id"] = user_id
    if not existing:
        kwargs.setdefault("data_deploy", now)
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur.execute(f"INSERT INTO bots_gerados ({cols}) VALUES ({placeholders})", list(kwargs.values()))
    else:
        set_clause = ", ".join([f"{k}=?" for k in kwargs if k != "user_id"])
        values = [v for k, v in kwargs.items() if k != "user_id"] + [user_id]
        cur.execute(f"UPDATE bots_gerados SET {set_clause} WHERE user_id=?", values)
    conn.commit()
    conn.close()


def log_feedback(bot_user_id: str, tipo: str, conteudo: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback_bots (bot_user_id, tipo, conteudo, data) VALUES (?,?,?,?)",
        (bot_user_id, tipo, conteudo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_skill_score(nicho: str, skill_name: str) -> float:
    """Retorna o score composto de uma skill para um nicho (0-10)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT media_satisfacao, taxa_retencao, taxa_escalacao FROM skills_performance "
        "WHERE nicho=? AND skill_name=?", (nicho, skill_name)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return 5.0  # score neutro para skill nova
    satisf = row[0] or 5.0
    retencao = (row[1] or 0.5) * 10
    escalacao_penalty = (row[2] or 0.2) * 5
    return round((satisf * 0.5 + retencao * 0.4) - escalacao_penalty * 0.1, 2)


def record_skill_usage(nicho: str, skill_name: str):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO skills_performance (nicho, skill_name, total_usos, ultima_atualizacao)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(nicho, skill_name) DO UPDATE SET
            total_usos = total_usos + 1,
            ultima_atualizacao = excluded.ultima_atualizacao
    """, (nicho, skill_name, now))
    conn.commit()
    conn.close()
