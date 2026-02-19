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

# Caminho do banco de dados (ajustado para ser relativo à raiz do projeto no servidor)
DB_NAME = "agencia_autovenda.db"

def get_data(query):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        # Silencia erros de tabela inexistente no início, mas mostra outros problemas
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
    if not df_leads.empty and 'status' in df_leads.columns:
        vendas = len(df_leads[df_leads['status'] == 'ativo'])
    else:
        vendas = 0
    st.metric("Vendas Confirmadas", vendas)
with col3:
    st.metric("Mensagens Trocadas", len(df_hist))

# --- GRÁFICOS ---
st.subheader("📈 Atividade Recente")
if not df_hist.empty and 'timestamp' in df_hist.columns:
    # Converter timestamp para legível
    df_hist['hora'] = pd.to_datetime(df_hist['timestamp']).dt.strftime('%H:%M')
    msg_por_hora = df_hist.groupby('hora').size().reset_index(name='contagem')
    fig = px.line(msg_por_hora, x='hora', y='contagem', title="Volume de Mensagens (por hora)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aguardando primeiras interações para gerar gráficos.")

# --- DETALHES DOS LEADS ---
st.subheader("👥 Lista de Contatos e Status")
if not df_leads.empty:
    cols_to_show = [c for c in ['user_id', 'nome', 'status', 'plano_ativo'] if c in df_leads.columns]
    st.dataframe(df_leads[cols_to_show].fillna("-"), use_container_width=True)
else:
    st.warning("Nenhum lead encontrado no banco de dados ainda.")

# --- CHAT VIEWER ---
st.subheader("💬 Últimas Conversas")
if not df_leads.empty and 'nome' in df_leads.columns:
    names = df_leads['nome'].unique()
    selected_user = st.selectbox("Selecione um cliente para ver o chat:", names)

    if selected_user:
        # Busca o ID do usuário baseado no nome selecionado
        user_row = df_leads[df_leads['nome'] == selected_user]
        if not user_row.empty:
            uid = user_row['user_id'].values[0]
            chat_query = f"SELECT role, content, timestamp FROM historico WHERE user_id = '{uid}' ORDER BY timestamp DESC LIMIT 20"
            chat = get_data(chat_query)
            
            if not chat.empty:
                for index, row in chat.iterrows():
                    is_user = row['role'] == 'user'
                    color = "#e1ffc7" if is_user else "#f0f0f0"
                    align = "right" if is_user else "left"
                    margin = "left: 30%" if is_user else "right: 30%"
                    
                    st.markdown(f"""
                        <div style="background-color:{color}; padding:12px; border-radius:15px; margin:8px 0; text-align:left; {margin}; border: 1px solid #ddd">
                            <small style="color: #666">{row['timestamp']}</small><br>
                            <b>{"VOCÊ" if is_user else "SOFIA"}:</b> {row['content']}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sem histórico de mensagens para este usuário.")
else:
    st.info("Inicie uma conversa com o bot para ver o chat aqui.")
