"""
watcher.py — Monitor principal do Bot Factory.
Roda em loop contínuo, verifica novos clientes ativos no DB e dispara o pipeline.
Também executa o ciclo de aprendizado a cada 24h e verifica saúde dos bots.

Uso: python -m bot_factory.watcher
  ou: python bot_factory/watcher.py
"""
import os
import sys
import time
import logging
import signal
from datetime import datetime, timedelta

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from bot_factory.db_factory  import setup_factory_tables, get_pending_clients, get_bot_record, upsert_bot_record
from bot_factory.pipeline    import run_pipeline
from bot_factory.deployer    import is_running, deploy_bot
from bot_factory.learning    import run_learning_cycle

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("watcher")

POLL_INTERVAL    = int(os.getenv("FACTORY_POLL_INTERVAL", "60"))   # segundos entre verificações
LEARNING_INTERVAL = 24 * 3600                                        # ciclo de aprendizado a cada 24h

_running = True
_last_learning = datetime.now() - timedelta(hours=25)  # garante ciclo na primeira execução


def _handle_signal(sig, frame):
    global _running
    logger.info(f"[Watcher] Sinal {sig} recebido — encerrando...")
    _running = False


def _health_check():
    """Verifica se bots marcados como 'active' ainda estão rodando. Reinicia se necessário."""
    import sqlite3
    db = os.getenv("DB_NAME", "agencia_autovenda.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT user_id, bot_path, pid FROM bots_gerados WHERE status = 'active'")
    active_bots = cur.fetchall()
    conn.close()

    for bot in active_bots:
        uid      = bot["user_id"]
        bot_path = bot["bot_path"]
        if not is_running(uid):
            logger.warning(f"[Watcher] Bot {uid} não está rodando — reiniciando...")
            pid = deploy_bot(bot_path, uid)
            if pid:
                upsert_bot_record(uid, pid=pid, data_ultimo_start=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                logger.info(f"[Watcher] Bot {uid} reiniciado — PID {pid}")
            else:
                upsert_bot_record(uid, status="error", erro_msg="Falha ao reiniciar — verifique bot.log")


def main():
    global _last_learning

    # Intercepta Ctrl+C e SIGTERM
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("=" * 60)
    logger.info("  🏭 BOT FACTORY — WATCHER INICIADO")
    logger.info(f"  Intervalo de poll: {POLL_INTERVAL}s")
    logger.info("=" * 60)

    # Garante tabelas do factory no DB
    setup_factory_tables()
    logger.info("[Watcher] Tabelas do factory verificadas/criadas.")

    while _running:
        try:
            # ── Verifica novos clientes para criar bot ──
            pending = get_pending_clients()
            if pending:
                logger.info(f"[Watcher] {len(pending)} cliente(s) pendente(s) detectado(s).")
                for client in pending:
                    uid = client["user_id"]
                    logger.info(f"[Watcher] ▶ Disparando pipeline para {uid} "
                                f"(plano={client.get('plano')}, nicho={client.get('nicho')})")
                    result = run_pipeline(uid)
                    if result["success"]:
                        logger.info(f"[Watcher] ✅ Bot de {uid} criado e ativo.")
                    else:
                        logger.error(f"[Watcher] ❌ Falha no pipeline de {uid}: "
                                     f"{result['steps'].get('error', 'erro desconhecido')}")
            else:
                logger.debug("[Watcher] Nenhum cliente novo pendente.")

            # ── Health check dos bots ativos ────────────
            _health_check()

            # ── Ciclo de aprendizado (a cada 24h) ───────
            now = datetime.now()
            if (now - _last_learning).total_seconds() >= LEARNING_INTERVAL:
                logger.info("[Watcher] Executando ciclo de aprendizado...")
                summary = run_learning_cycle()
                logger.info(f"[Watcher] Aprendizado: {summary}")
                _last_learning = now

        except Exception as e:
            logger.error(f"[Watcher] Erro no loop principal: {e}", exc_info=True)

        # Aguarda antes do próximo poll
        for _ in range(POLL_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    logger.info("[Watcher] 🛑 Watcher encerrado.")


if __name__ == "__main__":
    main()
