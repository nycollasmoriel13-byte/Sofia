import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# Configuração da Página
st.set_page_config(page_title="Sofia Dashboard", layout="wide")

# Caminho absoluto para evitar confusão de pastas no servidor
DB_PATH = "/root/sofia/agencia_autovenda.db"

def get_data(query):
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame()
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

# Título Único e Limpo (Removendo a duplicação vista no print)
st.title("🚀 Sofia — Painel de Gestão Auto-Venda")
st.sidebar.info(f"Conectado em: {DB_PATH}")

# --- MÉTRICAS PRINCIPAIS ---
df_leads = get_data("SELECT * FROM assinaturas")
df_hist = get_data("SELECT * FROM historico")

col1, col2, col3 = st.columns(3)

with col1:
    total_leads = len(df_leads) if not df_leads.empty else 0
    st.metric("Total de Leads", total_leads)

with col2:
    if not df_leads.empty and 'status' in df_leads.columns:
        vendas = len(df_leads[df_leads['status'] == 'ativo'])
    else:
        vendas = 0
    st.metric("Assinantes Ativos", vendas)

with col3:
    # Cálculo de MRR (Receita Mensal Recorrente)
    if not df_leads.empty and 'valor_mensal' in df_leads.columns:
        mrr = df_leads[df_leads['status'] == 'ativo']['valor_mensal'].sum()
    else:
        mrr = 0.0
    st.metric("MRR (Receita Recorrente)", f"R$ {mrr:,.2f}")

st.markdown("---")

# --- GRÁFICOS E ATIVIDADE ---
st.subheader("📈 Atividade Recente")
if not df_hist.empty and 'timestamp' in df_hist.columns:
    df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
    df_hist['hora'] = df_hist['timestamp'].dt.strftime('%H:00')
    msg_por_hora = df_hist.groupby('hora').size().reset_index(name='contagem')
    fig = px.area(msg_por_hora, x='hora', y='contagem', title="Volume de Mensagens", color_discrete_sequence=['#00CC96'])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aguardando interações para gerar gráficos.")

# --- TABELA DE LEADS ---
st.subheader("👥 Lista de Contatos")
if not df_leads.empty:
    cols = [c for c in ['user_id', 'nome', 'status', 'plano_ativo'] if c in df_leads.columns]
    st.dataframe(df_leads[cols].fillna("-"), use_container_width=True)
else:
    st.warning("Nenhum lead registrado.")

# --- VISUALIZADOR DE CHAT ---
st.subheader("💬 Últimas Conversas")
if not df_leads.empty and 'nome' in df_leads.columns:
    nomes_disponiveis = df_leads['nome'].dropna().unique()
    selected_user = st.selectbox("Selecione um cliente:", nomes_disponiveis)

    if selected_user:
        user_id = df_leads[df_leads['nome'] == selected_user]['user_id'].values[0]
        chat = get_data(f"SELECT role, content, timestamp FROM historico WHERE user_id = '{user_id}' ORDER BY timestamp DESC LIMIT 15")
        
        if not chat.empty:
            for _, row in chat.iterrows():
                is_user = row['role'] == 'user'
                bg = "#e1ffc7" if is_user else "#f0f0f0"
                align = "right" if is_user else "left"
                st.markdown(f"""
                    <div style="background-color:{bg}; padding:10px; border-radius:10px; margin:5px; text-align:left; float:{align}; width:70%; border: 1px solid #ccc">
                        <small style="color:gray">{row['timestamp']}</small><br>
                        <b>{"Você" if is_user else "Sofia"}:</b> {row['content']}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem histórico de mensagens para este usuário.")
else:
    st.info("O histórico de chat aparecerá aqui conforme os leads interagirem.")
