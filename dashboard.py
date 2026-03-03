import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json
import os

# ─── Configuração da Página ───────────────────────────────────────────────────
st.set_page_config(page_title="Sofia — Painel Auto-Venda", layout="wide", page_icon="🤖")

DB_PATH = os.getenv('DB_NAME', os.getenv('DB_PATH', 'agencia_autovenda.db'))

# ─── Helper de leitura ───────────────────────────────────────────────────────

def _q(query: str, params: tuple = ()) -> pd.DataFrame:
    """Executa query e retorna DataFrame (vazio se banco não existir)."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.sidebar.warning(f"Erro DB: {e}")
        return pd.DataFrame()


def _has_column(table: str, column: str) -> bool:
    """Verifica se a tabela contém a coluna (evita ORDER BY em colunas ausentes)."""
    try:
        if not os.path.exists(DB_PATH):
            return False
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(%s)" % table)
        cols = [r[1] for r in cur.fetchall()]
        conn.close()
        return column in cols
    except Exception:
        return False


def _sanitize_df_for_display(df: pd.DataFrame, string_fill: str = "-") -> pd.DataFrame:
    """Return a copy of df safe for Streamlit display: numeric columns keep numeric (fillna 0),
    non-numeric columns fill missing with `string_fill` to avoid pyarrow conversion errors."""
    if df is None or df.empty:
        return df
    out = df.copy()
    from pandas.api.types import is_numeric_dtype
    for c in out.columns:
        try:
            if is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(0)
            else:
                out[c] = out[c].fillna(string_fill)
        except Exception:
            out[c] = out[c].fillna(string_fill)
    return out


# ─── Cabeçalho ───────────────────────────────────────────────────────────────
st.title("🤖 Sofia — Painel de Gestão Auto-Venda")
st.sidebar.caption(f"📂 Banco: `{DB_PATH}`")
st.sidebar.caption("Atualiza automático a cada 30s")
st.sidebar.markdown("---")

# ─── DADOS PRINCIPAIS ────────────────────────────────────────────────────────
df_leads = _q("SELECT * FROM assinaturas ORDER BY data_inicio DESC")
df_hist  = _q("SELECT * FROM historico ORDER BY timestamp DESC")
df_onb   = _q("SELECT * FROM onboarding_data ORDER BY data_coleta DESC")

# ─── MÉTRICAS ────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

df_ativos_global = df_leads[df_leads["status"] == "ativo"] if not df_leads.empty else pd.DataFrame()

ativos = len(df_ativos_global)
mrr    = 0.0
if not df_ativos_global.empty and "valor_mensal" in df_ativos_global.columns:
    mrr = df_ativos_global["valor_mensal"].fillna(0).sum()

# Mensagens totais no histórico
total_msg = len(df_hist) if not df_hist.empty else 0

col1.metric("💳 Clientes Ativos", ativos)
col2.metric("💰 MRR", f"R$ {mrr:,.2f}")
col3.metric("💬 Mensagens Trocadas", total_msg)
col4.metric("📄 Onboardings", len(df_onb) if not df_onb.empty else 0)

st.markdown("---")

# ─── ABAS ────────────────────────────────────────────────────────────────────
tab_leads, tab_onb, tab_chat, tab_stats, tab_factory = st.tabs(
    ["👥 Leads", "📋 Onboarding", "💬 Conversas", "📈 Estatísticas", "🏭 Bot Factory"]
)

# ═══════════════════════════════════════════════════════════
# TAB 1 — LEADS
# ═══════════════════════════════════════════════════════════
with tab_leads:
    st.subheader("Lista de Leads / Clientes")

    # Apenas clientes que efetivaram pagamento
    df_ativos = df_leads[df_leads["status"] == "ativo"] if not df_leads.empty else pd.DataFrame()

    if df_ativos.empty:
        st.info("Nenhum cliente ativo ainda. Esta lista é preenchida após confirmação de pagamento.")
    else:
        df_view = df_ativos

        # Colunas a exibir (só as que existem)
        all_cols = ["user_id", "nome", "whatsapp_id", "plano",
                    "status", "valor_mensal", "data_inicio"]
        show_cols = [c for c in all_cols if c in df_view.columns]
        st.dataframe(df_view[show_cols].fillna("-"), width='stretch')

        # Distribuição por plano (apenas ativos)
        if "plano" in df_ativos.columns:
            plano_counts = df_ativos["plano"].fillna("sem plano").value_counts().reset_index()
            plano_counts.columns = ["plano", "count"]
            fig_plano = px.pie(plano_counts, names="plano", values="count",
                               title="Clientes Ativos por Plano", hole=0.4,
                               color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig_plano, width='stretch')

        # Distribuição por plataforma (apenas ativos)
        if "plataforma" in df_ativos.columns:
            plat_counts = df_ativos["plataforma"].fillna("indefinida").value_counts().reset_index()
            plat_counts.columns = ["plataforma", "count"]
            fig_plat = px.bar(plat_counts, x="plataforma", y="count",
                              title="Clientes Ativos por Plataforma", color="plataforma",
                              color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_plat, width='stretch')

# ═══════════════════════════════════════════════════════════
# TAB 2 — ONBOARDING
# ═══════════════════════════════════════════════════════════
with tab_onb:
    st.subheader("Progresso de Onboarding dos Clientes")

    if df_onb.empty:
        st.info("Nenhum onboarding iniciado ainda.")
    else:
        # Status geral
        status_col = "status_configuracao" if "status_configuracao" in df_onb.columns else ("status" if "status" in df_onb.columns else None)
        if status_col:
            s_counts = df_onb[status_col].fillna("em_progresso").value_counts().reset_index()
            s_counts.columns = ["status", "count"]
            fig_s = px.bar(s_counts, x="status", y="count", title="Status do Onboarding",
                           color="status", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_s, width='stretch')

        # Detalhe por lead
        for _, row in df_onb.iterrows():
            uid    = row.get("user_id", "?")
            status = row.get("status_configuracao", "em_progresso")
            coleta = row.get("data_coleta", "-")
            contato = row.get("whatsapp_contato", "—")
            website = row.get("website_cliente", "—")
            objetivos = row.get("objetivos_ia", "—")

            with st.expander(f"👤 {uid}  |  {status}  |  Data: {coleta}"):
                colA, colB = st.columns(2)
                with colA:
                    st.markdown("**📱 WhatsApp:**")
                    st.write(contato)
                    st.markdown("**🌐 Website:**")
                    st.write(website)
                with colB:
                    st.markdown("**🎯 Objetivos IA:**")
                    st.write(objetivos)

# ═══════════════════════════════════════════════════════════
# TAB 3 — CONVERSAS (apenas clientes ativos)
# ═══════════════════════════════════════════════════════════
with tab_chat:
    st.subheader("💬 Conversas — Clientes com Plano Ativo")

    # Filtra apenas clientes com status "ativo"
    df_ativos_chat = df_leads[df_leads["status"] == "ativo"] if not df_leads.empty else pd.DataFrame()

    if df_ativos_chat.empty:
        st.info("Nenhum cliente ativo encontrado. As conversas serão exibidas após a confirmação do plano.")
    elif df_hist.empty:
        st.info("Nenhuma mensagem registrada ainda.")
    else:
        # Monta mapa user_id → nome de exibição
        nomes = {}
        if "nome" in df_ativos_chat.columns:
            nomes = {
                row["user_id"]: (row["nome"] or "").strip() or row["user_id"]
                for _, row in df_ativos_chat.iterrows()
            }

        # IDs ativos que têm histórico
        ids_ativos = set(df_ativos_chat["user_id"].tolist())
        ids_com_hist = set(df_hist["user_id"].unique().tolist())
        ids_validos = sorted(ids_ativos & ids_com_hist)

        if not ids_validos:
            st.info("Clientes ativos ainda não possuem mensagens registradas.")
        else:
            # Métricas gerais
            hist_ativos = df_hist[df_hist["user_id"].isin(ids_validos)]
            c1, c2 = st.columns(2)
            c1.metric("Total de Mensagens (ativos)", len(hist_ativos))
            c2.metric("Clientes com Conversa", len(ids_validos))

            st.markdown("---")

            # Sub-abas — uma por cliente ativo
            tab_labels = [f"👤 {nomes.get(uid, uid)}" for uid in ids_validos]
            sub_tabs = st.tabs(tab_labels)

            for sub_tab, uid in zip(sub_tabs, ids_validos):
                with sub_tab:
                    nome_exib = nomes.get(uid, uid)
                    plano_row = df_ativos_chat[df_ativos_chat["user_id"] == uid]
                    plano_val = plano_row["plano"].values[0] if "plano" in plano_row.columns and len(plano_row) > 0 else "—"
                    dt_val    = plano_row["data_inicio"].values[0] if "data_inicio" in plano_row.columns and len(plano_row) > 0 else "—"

                    st.caption(f"Plano: **{plano_val}** · Desde: **{dt_val}**")

                    chat_df = _q(
                        "SELECT role, content, timestamp FROM historico WHERE user_id = ? ORDER BY timestamp ASC",
                        (uid,)
                    )

                    if chat_df.empty:
                        st.info("Sem mensagens para este cliente.")
                    else:
                        for _, row in chat_df.iterrows():
                            is_user = row["role"] == "user"
                            bg      = "#dcf8c6" if is_user else "#f0f0f0"
                            align   = "right" if is_user else "left"
                            sender  = nome_exib if is_user else "Sofia 🤖"
                            st.markdown(
                                f"""<div style="background:{bg}; padding:10px 14px; border-radius:12px;
                                    margin:4px 0; max-width:75%; float:{align}; clear:both;
                                    border:1px solid #ccc; font-size:0.95em">
                                    <b>{sender}</b><br>{row['content']}
                                    <br><small style="color:#888">{row['timestamp']}</small>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        st.markdown('<div style="clear:both"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# TAB 4 — ESTATÍSTICAS
# ═══════════════════════════════════════════════════════════
with tab_stats:
    st.subheader("Análise de Atividade")

    if df_hist.empty:
        st.info("Sem dados de mensagens para análise.")
    else:
        df_hist_copy = df_hist.copy()
        df_hist_copy["timestamp"] = pd.to_datetime(df_hist_copy["timestamp"], errors="coerce")
        df_hist_copy = df_hist_copy.dropna(subset=["timestamp"])

        # Volume por hora
        df_hist_copy["hora"] = df_hist_copy["timestamp"].dt.strftime("%H:00")
        msg_hora = df_hist_copy.groupby("hora").size().reset_index(name="mensagens")
        fig_hora = px.area(msg_hora, x="hora", y="mensagens",
                           title="Volume de Mensagens por Hora",
                           color_discrete_sequence=["#00CC96"])
        st.plotly_chart(fig_hora, width='stretch')

        # Volume por dia
        df_hist_copy["dia"] = df_hist_copy["timestamp"].dt.date
        msg_dia = df_hist_copy.groupby("dia").size().reset_index(name="mensagens")
        fig_dia = px.bar(msg_dia, x="dia", y="mensagens",
                         title="Mensagens por Dia",
                         color_discrete_sequence=["#636EFA"])
        st.plotly_chart(fig_dia, width='stretch')

    # Nichosde mais frequentes entre os leads qualificados
    if not df_ativos_global.empty and "nicho" in df_ativos_global.columns:
        nicho_c = df_ativos_global["nicho"].dropna().value_counts().head(10).reset_index()
        nicho_c.columns = ["nicho", "count"]
        fig_nicho = px.bar(nicho_c, x="count", y="nicho", orientation="h",
                           title="Top Nichos (Clientes Ativos)",
                           color="count", color_continuous_scale="Tealgrn")
        st.plotly_chart(fig_nicho, width='stretch')

# ═══════════════════════════════════════════════════════════
# TAB 5 — BOT FACTORY
# ═══════════════════════════════════════════════════════════
with tab_factory:
    st.subheader("🏭 Bot Factory — Bots Gerados Automaticamente")

    if _has_column('bots_gerados', 'criado_em'):
        df_bots = _q("SELECT * FROM bots_gerados ORDER BY criado_em DESC")
    else:
        df_bots = _q("SELECT * FROM bots_gerados")

    if _has_column('skills_performance', 'score'):
        df_skills = _q("SELECT * FROM skills_performance ORDER BY score DESC")
    else:
        df_skills = _q("SELECT * FROM skills_performance")

    if df_bots.empty:
        st.info("Nenhum bot gerado ainda. O Factory cria bots automaticamente quando um cliente fica ativo.")
    else:
        # Métricas
        total_bots  = len(df_bots)
        ativos_bots = len(df_bots[df_bots["status"] == "ativo"]) if "status" in df_bots.columns else 0
        erros_bots  = len(df_bots[df_bots["status"] == "erro"]) if "status" in df_bots.columns else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Bots", total_bots)
        c2.metric("✅ Ativos", ativos_bots)
        c3.metric("❌ Com Erro", erros_bots)

        st.markdown("---")

        # Tabela de bots
        show_cols = [c for c in ["user_id", "plano", "nicho", "status", "bot_username",
                                  "skills_ativas", "criado_em", "ultimo_restart"] if c in df_bots.columns]
        st.dataframe(df_bots[show_cols].fillna("-"), width='stretch')

        # Gráfico status dos bots
        if "status" in df_bots.columns:
            st.markdown("#### Status dos Bots")
            s_bots = df_bots["status"].fillna("desconhecido").value_counts().reset_index()
            s_bots.columns = ["status", "count"]
            fig_bots = px.pie(s_bots, names="status", values="count", hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_bots, width='stretch')

    # Skills Performance
    st.markdown("---")
    st.subheader("🧠 Performance das Skills (Learning Engine)")
    if df_skills.empty:
        st.info("Dados de performance ainda não disponíveis. O Learning Engine roda após 24h de operação.")
    else:
        show_sk = [c for c in ["skill_name", "nicho", "score", "usos", "taxa_retencao",
                                "taxa_escalacao", "ultima_atualizacao"] if c in df_skills.columns]
        st.dataframe(df_skills[show_sk].fillna("-"), width='stretch')

        if "score" in df_skills.columns and "skill_name" in df_skills.columns:
            top_skills = df_skills.head(15)
            fig_sk = px.bar(top_skills, x="score", y="skill_name", orientation="h",
                            title="Top 15 Skills por Score", color="score",
                            color_continuous_scale="Tealgrn")
            st.plotly_chart(fig_sk, width='stretch')

# ─── Auto-refresh ────────────────────────────────────────────────────────────
st.markdown("---")
if st.button("🔄 Atualizar dados agora"):
    st.rerun()
