"""
deployer.py — Inicia/para bots de clientes usando subprocess.
Arquitetura local primeiro, preparada para Docker no futuro.

Para cada bot, guarda o PID em clients/{user_id}/bot.pid.
Para migrar para Docker: substituir _start_local() por _start_docker().
"""
import os
import sys
import json
import signal
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FACTORY_DIR  = os.path.dirname(os.path.abspath(__file__))
CLIENTS_DIR  = os.path.join(os.path.dirname(FACTORY_DIR), "clients")
PYTHON_BIN   = sys.executable  # mesmo Python do venv ativo


def deploy_bot(bot_path: str, user_id: str) -> Optional[int]:
    """
    Inicia o bot do cliente como subprocesso independente.
    Retorna o PID do processo, ou None em caso de erro.
    """
    client_dir = os.path.join(CLIENTS_DIR, user_id)
    pid_file   = os.path.join(client_dir, "bot.pid")
    log_file   = os.path.join(client_dir, "bot.log")

    # Para qualquer instância anterior
    stop_bot(user_id)

    if not os.path.exists(bot_path):
        logger.error(f"[Deployer] bot.py não encontrado: {bot_path}")
        return None

    try:
        # Carrega variáveis de ambiente do .env do projeto raiz
        env = os.environ.copy()
        env_file = os.path.join(os.path.dirname(FACTORY_DIR), ".env")
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        env[k.strip()] = v.strip().strip('"').strip("'")

        log_handle = open(log_file, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [PYTHON_BIN, bot_path],
            stdout=log_handle,
            stderr=log_handle,
            env=env,
            cwd=client_dir,
            # creationflags para Windows — processo independente
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        pid = proc.pid

        # Salva PID
        with open(pid_file, "w") as f:
            f.write(str(pid))

        logger.info(f"[Deployer] Bot {user_id} iniciado — PID {pid} | Log: {log_file}")
        return pid

    except Exception as e:
        logger.error(f"[Deployer] Erro ao iniciar bot {user_id}: {e}")
        return None


def stop_bot(user_id: str) -> bool:
    """Para o bot do cliente pelo PID salvo."""
    client_dir = os.path.join(CLIENTS_DIR, user_id)
    pid_file   = os.path.join(client_dir, "bot.pid")

    if not os.path.exists(pid_file):
        return False

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)

        os.remove(pid_file)
        logger.info(f"[Deployer] Bot {user_id} (PID {pid}) encerrado.")
        return True
    except Exception as e:
        logger.warning(f"[Deployer] Não foi possível encerrar bot {user_id}: {e}")
        if os.path.exists(pid_file):
            os.remove(pid_file)
        return False


def is_running(user_id: str) -> bool:
    """Verifica se o processo do bot ainda está rodando."""
    client_dir = os.path.join(CLIENTS_DIR, user_id)
    pid_file   = os.path.join(client_dir, "bot.pid")

    if not os.path.exists(pid_file):
        return False

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)  # sinal 0 = apenas verifica existência
            return True
    except Exception:
        return False


# ── Interface para Docker (futura migração) ───────────────────────────────────
# Para migrar: descomente e substitua as chamadas acima por estas.
#
# def _start_docker(bot_path: str, user_id: str) -> Optional[int]:
#     client_dir = os.path.join(CLIENTS_DIR, user_id)
#     image = f"sofia-client-bot:latest"
#     cmd = [
#         "docker", "run", "-d",
#         "--name", f"client_bot_{user_id}",
#         "-v", f"{client_dir}:/app/client",
#         "-v", f"{os.path.abspath('agencia_autovenda.db')}:/app/agencia_autovenda.db",
#         "--env-file", ".env",
#         image,
#         "python", "/app/client/bot.py"
#     ]
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     if result.returncode == 0:
#         container_id = result.stdout.strip()
#         logger.info(f"[Docker] Container {container_id} iniciado para {user_id}")
#         return container_id
#     return None
