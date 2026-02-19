import streamlit as st
import sqlite3
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Sofia — Auto-Venda Admin", layout="wide")

DB_NAME = "agencia_autovenda.db"

def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM assinaturas", conn)
    conn.close()
    return df

st.title("🚀 Sofia — Painel de Gestão Auto-Venda")

# Métricas Principais
data = load_data()
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total de Leads", len(data))
with col2:
    ativos = data[data['status'] == 'ativo']
    st.metric("Assinantes Ativos", len(ativos))
with col3:
    mrr = ativos['valor_mensal'].sum() if not ativos.empty else 0.0
    st.metric("MRR (Receita Recorrente)", f"R$ {mrr:,.2f}")

st.divider()

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Sofia Dashboard", layout="wide")

DB_NAME = "agencia_autovenda.db"

def get_data(query):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar banco: {e}")
        return pd.DataFrame()

st.title("📊 Painel de Controle - Sofia IA")
st.sidebar.info("Atualizado em tempo real via SQLite")

# --- MÉTRICAS ---
col1, col2, col3 = st.columns(3)

df_leads = get_data("SELECT * FROM assinaturas")
df_hist = get_data("SELECT * FROM historico")

with col1:
    st.metric("Total de Leads", len(df_leads))
with col2:
    vendas = len(df_leads[df_leads['status'] == 'ativo'])
    st.metric("Vendas Confirmadas", vendas)
with col3:
    st.metric("Mensagens Trocadas", len(df_hist))

# --- GRÁFICOS ---
st.subheader("📈 Atividade Recente")
if not df_hist.empty:
    # Converter timestamp para legível se necessário
    df_hist['hora'] = pd.to_datetime(df_hist['timestamp']).dt.strftime('%H:%M')
    msg_por_hora = df_hist.groupby('hora').size().reset_index(name='contagem')
    fig = px.line(msg_por_hora, x='hora', y='contagem', title="Volume de Mensagens")
    st.plotly_chart(fig, use_container_width=True)

# --- DETALHES DOS LEADS ---
st.subheader("👥 Lista de Contatos e Status")
if not df_leads.empty:
    st.dataframe(df_leads[['user_id', 'nome', 'status', 'plano_ativo']].fillna("-"), use_container_width=True)

# --- CHAT VIEWER ---
st.subheader("💬 Últimas Conversas")
selected_user = st.selectbox("Selecione um cliente para ver o chat:", df_leads['nome'].unique() if not df_leads.empty else [])

if selected_user:
    uid = df_leads[df_leads['nome'] == selected_user]['user_id'].values[0]
    chat = get_data(f"SELECT role, content, timestamp FROM historico WHERE user_id = '{uid}' ORDER BY timestamp DESC LIMIT 10")
    for index, row in chat.iterrows():
        color = "#e1ffc7" if row['role'] == 'user' else "#f0f0f0"
        align = "right" if row['role'] == 'user' else "left"
        st.markdown(f"""
            <div style="background-color:{color}; padding:10px; border-radius:10px; margin:5px; text-align:{align}; width: 70%; float:{align}">
                <small>{row['timestamp']}</small><br>
                <b>{row['role'].upper()}:</b> {row['content']}
            </div>
        """, unsafe_allow_html=True)
