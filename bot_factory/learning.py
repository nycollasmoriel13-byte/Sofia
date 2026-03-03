"""
learning.py — Engine de aprendizado: analisa performance dos bots gerados e
atualiza o score das skills por nicho para builds futuros mais inteligentes.

Executa como tarefa periódica (chamada pelo watcher a cada 24h).
"""
import sqlite3
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_NAME", "agencia_autovenda.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def run_learning_cycle():
    """
    Ciclo completo de aprendizado:
    1. Coleta métricas de usage e feedback
    2. Atualiza scores de skills por nicho
    3. Detecta novos nichos e cria templates base
    4. Loga resumo do ciclo
    """
    logger.info("[Learning] Iniciando ciclo de aprendizado...")
    conn = _conn()
    cur = conn.cursor()

    # ── 1. Calcula taxa de escalação por bot ─────────────────────
    cur.execute("""
        SELECT bot_user_id,
               COUNT(*) as total,
               SUM(CASE WHEN tipo = 'escalacao' THEN 1 ELSE 0 END) as escalacoes
        FROM feedback_bots
        WHERE data >= date('now', '-30 days')
        GROUP BY bot_user_id
    """)
    escal_data = {r["bot_user_id"]: (r["escalacoes"] / max(r["total"], 1))
                  for r in cur.fetchall()}

    # ── 2. Calcula taxa de retenção (bots ativos após 30 dias) ────
    cur.execute("""
        SELECT user_id, nicho, skills_usadas
        FROM bots_gerados
        WHERE status = 'active'
          AND data_deploy <= date('now', '-30 days')
    """)
    active_old = cur.fetchall()

    cur.execute("""
        SELECT user_id FROM assinaturas WHERE status = 'ativo'
    """)
    active_clients = {r["user_id"] for r in cur.fetchall()}

    # ── 3. Atualiza scores por skill/nicho ────────────────────────
    updated = 0
    for bot in active_old:
        uid      = bot["user_id"]
        nicho    = bot["nicho"] or "servicos"
        skills   = []
        try:
            import json
            skills = json.loads(bot["skills_usadas"] or "[]")
        except Exception:
            pass

        retencao  = 1.0 if uid in active_clients else 0.0
        escalacao = escal_data.get(uid, 0.2)

        for skill in skills:
            cur.execute("""
                INSERT INTO skills_performance
                    (nicho, skill_name, total_usos, taxa_retencao, taxa_escalacao, ultima_atualizacao)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(nicho, skill_name) DO UPDATE SET
                    taxa_retencao = (taxa_retencao * total_usos + excluded.taxa_retencao) / (total_usos + 1),
                    taxa_escalacao = (taxa_escalacao * total_usos + excluded.taxa_escalacao) / (total_usos + 1),
                    total_usos = total_usos + 1,
                    ultima_atualizacao = excluded.ultima_atualizacao
            """, (nicho, skill, retencao, escalacao, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            updated += 1

    # ── 4. Detecta novos nichos não mapeados ─────────────────────
    cur.execute("""
        SELECT DISTINCT nicho FROM bots_gerados
        WHERE nicho NOT IN (
            SELECT DISTINCT nicho FROM skills_performance
        ) AND nicho IS NOT NULL
    """)
    new_niches = [r["nicho"] for r in cur.fetchall()]
    for nicho in new_niches:
        logger.info(f"[Learning] Novo nicho detectado: '{nicho}' — inicializando com skills genéricas.")
        _seed_new_niche(nicho, cur)

    conn.commit()
    conn.close()

    summary = f"Ciclo concluído: {updated} skills atualizadas, {len(new_niches)} novos nichos detectados."
    logger.info(f"[Learning] {summary}")
    return summary


def _seed_new_niche(nicho: str, cur):
    """Insere scores neutros para um nicho novo com as skills base."""
    base_skills = ["faq_responder", "horario_funcionamento", "captura_lead", "transbordo_humano"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for skill in base_skills:
        cur.execute("""
            INSERT OR IGNORE INTO skills_performance
                (nicho, skill_name, total_usos, media_satisfacao, taxa_retencao, taxa_escalacao, ultima_atualizacao)
            VALUES (?, ?, 0, 5.0, 0.5, 0.2, ?)
        """, (nicho, skill, now))


def register_message_count(user_id: str, count: int = 1):
    """Atualiza o total de mensagens de um bot gerado."""
    conn = _conn()
    conn.execute("""
        UPDATE bots_gerados
        SET total_mensagens = total_mensagens + ?,
            data_ultima_mensagem = ?
        WHERE user_id = ?
    """, (count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()


def register_escalation(user_id: str, message: str = ""):
    """Registra um evento de escalação para o bot do cliente."""
    from bot_factory.db_factory import log_feedback
    log_feedback(user_id, "escalacao", message)


def register_satisfaction(user_id: str, score: float, comment: str = ""):
    """Registra feedback de satisfação (0-10) para o bot do cliente."""
    conn = _conn()
    conn.execute("""
        UPDATE bots_gerados SET score = ? WHERE user_id = ?
    """, (score, user_id))
    conn.commit()
    conn.close()

    from bot_factory.db_factory import log_feedback
    log_feedback(user_id, "satisfacao", f"score={score} | {comment}")
