"""
pipeline.py — Orquestrador do fluxo completo de criação de bots.
Dados DB → Perfil → Plano → Skills → Prompt → Geração → Deploy → Notificação.
"""
import logging
import json
from datetime import datetime

from bot_factory.db_factory       import upsert_bot_record, setup_factory_tables
from bot_factory.profile_loader   import load_client_profile
from bot_factory.plan_resolver    import resolve as resolve_plan
from bot_factory.skill_selector   import select_skills
from bot_factory.prompt_builder   import build_system_prompt
from bot_factory.generator        import generate_bot
from bot_factory.deployer         import deploy_bot, is_running
from bot_factory.notifier         import notify_client, notify_owner

logger = logging.getLogger(__name__)


def run_pipeline(user_id: str) -> dict:
    """
    Executa o pipeline completo para um cliente:
    1. Carrega perfil do DB
    2. Resolve plano e seleciona skills
    3. Monta system prompt personalizado
    4. Gera o código do bot
    5. Faz o deploy (inicia o processo)
    6. Notifica o cliente e o dono da agência

    Retorna status dict com resultado de cada etapa.
    """
    result = {"user_id": user_id, "steps": {}, "success": False}
    logger.info(f"[Pipeline] ▶ Iniciando pipeline para {user_id}")

    # ── ETAPA 0 — Marca como em construção ───────────────────────
    upsert_bot_record(user_id, status="building", data_deploy=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    try:
        # ── ETAPA 1 — Carrega perfil ──────────────────────────────
        profile = load_client_profile(user_id)
        result["steps"]["profile"] = "ok"
        logger.info(f"[Pipeline] Perfil carregado: nicho={profile.get('nicho')}, plano={profile.get('plano')}, "
                    f"plataforma={profile.get('plataforma')}, empresa={profile.get('empresa_nome')}")

        # Validação mínima: bot do cliente precisa de token de plataforma
        plataforma = profile.get("plataforma", "telegram").lower()
        if plataforma == "telegram" and not profile.get("telegram_bot_token"):
            # Marca como aguardando_token — watcher não retentará até o token ser adicionado
            upsert_bot_record(user_id, status="aguardando_token",
                              erro_msg="Token do BotFather não informado pelo cliente.")
            notify_owner(f"Cliente {user_id} está ativo mas sem token do Telegram. "
                         f"Solicite o token do BotFather para prosseguir.")
            result["steps"]["error"] = "aguardando_token"
            return result
        if plataforma == "whatsapp" and not profile.get("meta_phone_number_id"):
            upsert_bot_record(user_id, status="aguardando_token",
                              erro_msg="Credenciais do WhatsApp não informadas.")
            notify_owner(f"Cliente {user_id} sem credenciais WhatsApp (Meta). Configure Phone Number ID e Token.")
            result["steps"]["error"] = "aguardando_token"
            return result

        # ── ETAPA 2 — Resolve plano + seleciona skills ────────────
        features = resolve_plan(profile.get("plano", "flash"))
        skills   = select_skills(profile.get("nicho", "servicos"), profile.get("plano", "flash"))
        result["steps"]["skills"] = skills
        logger.info(f"[Pipeline] Skills selecionadas: {skills}")

        # ── ETAPA 3 — Monta system prompt ─────────────────────────
        system_prompt = build_system_prompt(profile, skills)
        result["steps"]["prompt"] = "ok"

        # ── ETAPA 4 — Gera código do bot ──────────────────────────
        gen = generate_bot(profile, skills, system_prompt)
        result["steps"]["generation"] = gen["bot_path"]
        logger.info(f"[Pipeline] Bot gerado em: {gen['bot_path']}")

        # ── ETAPA 5 — Deploy (inicia o processo) ──────────────────
        pid = deploy_bot(gen["bot_path"], user_id)
        if not pid:
            raise RuntimeError("Deploy falhou — subprocess não iniciou.")

        result["steps"]["deploy"] = f"PID {pid}"
        logger.info(f"[Pipeline] Deploy OK — PID {pid}")

        # ── ETAPA 6 — Salva no DB ─────────────────────────────────
        upsert_bot_record(
            user_id,
            plano         = profile.get("plano"),
            nicho         = profile.get("nicho"),
            plataforma    = plataforma,
            skills_usadas = json.dumps(skills),
            prompt_hash   = gen["prompt_hash"],
            bot_path      = gen["bot_path"],
            config_path   = gen["config_path"],
            pid           = pid,
            status        = "active",
            erro_msg      = None,
            data_ultimo_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # ── ETAPA 7 — Notifica cliente e dono ─────────────────────
        bot_username = profile.get("telegram_bot_username") or ""
        notify_client(user_id, profile, bot_username=bot_username)
        notify_owner(
            f"✅ Bot ativado para *{profile.get('empresa_nome')}*\n"
            f"Plano: {profile.get('plano')} | Nicho: {profile.get('nicho')} | Skills: {len(skills)}\n"
            f"PID: {pid}"
        )

        result["success"] = True
        logger.info(f"[Pipeline] ✅ Pipeline concluído com sucesso para {user_id}")

    except Exception as e:
        err_msg = str(e)
        logger.error(f"[Pipeline] ❌ Erro no pipeline de {user_id}: {err_msg}", exc_info=True)
        upsert_bot_record(user_id, status="error", erro_msg=err_msg)
        notify_client(user_id, load_client_profile(user_id) if True else {}, error=err_msg)
        notify_owner(f"❌ Erro no pipeline de `{user_id}`:\n{err_msg}")
        result["steps"]["error"] = err_msg

    return result
