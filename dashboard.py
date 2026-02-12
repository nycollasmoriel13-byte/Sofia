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

# Tabela de Clientes
st.subheader("📋 Gestão de Clientes e Leads")
if not data.empty:
    # Formatação para exibição
    display_df = data[['nome', 'user_id', 'plano', 'status', 'valor_mensal', 'data_inicio']]
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("Nenhum lead ou assinante encontrado no banco de dados.")

# Logs de Conversa
st.sidebar.title("🔍 Ver Conversa")
user_id = st.sidebar.selectbox("Selecione um cliente (user_id)", data['user_id'].unique() if not data.empty else ["Nenhum"])

if user_id != "Nenhum":
    conn = sqlite3.connect(DB_NAME)
    conversas = pd.read_sql_query(f"SELECT role, content, timestamp FROM historico WHERE user_id = '{user_id}' ORDER BY timestamp ASC", conn)
    conn.close()
    
    for _, row in conversas.iterrows():
        with st.chat_message(row['role']):
            st.write(f"**{row['timestamp']}**")
            st.write(row['content'])

# Rodar com: streamlit run dashboard.py
