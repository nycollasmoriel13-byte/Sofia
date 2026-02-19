import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sofia CRM — Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SIMULAÇÃO DE DADOS REAIS (ESTRUTURA DE BANCO DE DADOS) ---
if 'data_leads' not in st.session_state:
    st.session_state.data_leads = pd.DataFrame([
        {"id": 1, "nome": "Nikolas B.", "status": "Novo", "servico": "Venda Carro", "interesse": "Alto", "valor": 45000, "data": "2024-02-12 17:30", "resumo_ia": "Interessado em SUV blindado. Já possui financiamento pré-aprovado.", "contato": "11999990001"},
        {"id": 2, "nome": "Amanda L.", "status": "Pendente", "servico": "Avaliação", "interesse": "Médio", "valor": 0, "data": "2024-02-12 16:15", "resumo_ia": "Quer avaliar um sedan 2022. Questionou sobre taxa de troca.", "contato": "11999990002"},
        {"id": 3, "nome": "Roberto K.", "status": "Venda Finalizada", "servico": "Consórcio", "interesse": "Fechado", "valor": 120000, "data": "2024-02-11 10:40", "resumo_ia": "Fechou cota de 120k. Documentação enviada via Telegram.", "contato": "11999990003"},
        {"id": 4, "nome": "Juliana M.", "status": "Perdido", "servico": "Venda Carro", "interesse": "Baixo", "valor": 32000, "data": "2024-02-10 14:20", "resumo_ia": "Achou o valor da entrada alto. Não pretende financiar.", "contato": "11999990004"},
        {"id": 5, "nome": "Ricardo S.", "status": "Pendente", "servico": "Seguro", "interesse": "Alto", "valor": 2500, "data": "2024-02-12 18:00", "resumo_ia": "Cotação de seguro para frota. Aguardando retorno sobre desconto.", "contato": "11999990005"},
    ])

# --- CSS CUSTOMIZADO (DARK PREMIUM) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="st-at"], .main {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117;
        color: #e6edf3;
    }

    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
        margin-bottom: 10px;
    }
    
    .metric-label { color: #8b949e; font-size: 0.8rem; text-transform: uppercase; font-weight: 600; }
    .metric-value { color: #ffffff; font-size: 1.6rem; font-weight: 700; }
    
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stDataFrame { background-color: #161b22; border-radius: 12px; }
    
    /* Custom tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] { border-color: #58a6ff !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50)
    st.markdown("<h3 style='margin-bottom:0;'>Sofia Intelligence</h3>", unsafe_allow_html=True)
    st.caption("Central de Vendas v2.1")
    st.markdown("---")
    
    menu = st.radio("Navegação", ["📊 Dashboard", "👥 CRM & Leads", "📈 Inteligência de Produto", "⚙️ Configurações"])
    
    st.markdown("---")
    st.subheader("Filtros Rápidos")
    f_status = st.multiselect("Status", st.session_state.data_leads['status'].unique(), default=st.session_state.data_leads['status'].unique())

# Filtragem Global baseada na Sidebar
df_filtered = st.session_state.data_leads[st.session_state.data_leads['status'].isin(f_status)]

# --- LÓGICA DE PÁGINAS ---

if menu == "📊 Dashboard":
    st.title("📊 Resumo Executivo")
    
    # KPIs principais
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        total_leads = len(st.session_state.data_leads)
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total de Leads</div><div class="metric-value">{total_leads}</div></div>', unsafe_allow_html=True)
    with kpi2:
        vendas = len(st.session_state.data_leads[st.session_state.data_leads['status'] == "Venda Finalizada"])
        st.markdown(f'<div class="metric-card"><div class="metric-label">Vendas Fechadas</div><div class="metric-value">{vendas}</div></div>', unsafe_allow_html=True)
    with kpi3:
        mrr = st.session_state.data_leads[st.session_state.data_leads['status'] == "Venda Finalizada"]['valor'].sum()
        st.markdown(f'<div class="metric-card"><div class="metric-label">Faturamento</div><div class="metric-value">R$ {mrr/1000:.1f}k</div></div>', unsafe_allow_html=True)
    with kpi4:
        conversao = (vendas / total_leads) * 100 if total_leads > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-label">Taxa Conversão</div><div class="metric-value">{conversao:.1f}%</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Volume de Vendas vs Leads")
        fig_evol = px.line(df_filtered, x='data', y='valor', title="Fluxo Financeiro de Vendas", 
                          markers=True, color_discrete_sequence=['#58a6ff'])
        fig_evol.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#8b949e")
        st.plotly_chart(fig_evol, use_container_width=True)

    with c2:
        st.subheader("Status do Funil")
        fig_pie = px.pie(st.session_state.data_leads, names='status', color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

elif menu == "👥 CRM & Leads":
    st.title("👥 Gestão de Relacionamento")
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "👤 Perfil Detalhado (IA)"])
    
    with tab1:
        st.subheader("Leads Ativos e Pendentes")
        search = st.text_input("🔍 Buscar cliente por nome...", "")
        df_display = df_filtered.copy()
        if search:
            df_display = df_display[df_display['nome'].str.contains(search, case=False)]
            
        st.dataframe(df_display[['nome', 'status', 'servico', 'data', 'interesse']], use_container_width=True)
    
    with tab2:
        client_list = df_filtered['nome'].tolist()
        selected_client = st.selectbox("Selecione um cliente para ver o dossiê da Sofia:", client_list)
        
        if selected_client:
            client_data = df_filtered[df_filtered['nome'] == selected_client].iloc[0]
            
            p1, p2 = st.columns([1, 2])
            with p1:
                st.markdown(f"""
                <div style='background-color:#161b22; padding:20px; border-radius:12px; border:1px solid #30363d;'>
                    <h3 style='margin-top:0;'>{client_data['nome']}</h3>
                    <p><b>Status:</b> {client_data['status']}</p>
                    <p><b>Telefone:</b> {client_data['contato']}</p>
                    <p><b>Interesse:</b> {client_data['interesse']}</p>
                    <p><b>Serviço:</b> {client_data['servico']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with p2:
                st.markdown("#### 🧠 Inteligência da Sofia (Resumo da IA)")
                st.info(client_data['resumo_ia'])
                
                st.markdown("#### 📝 Próximos Passos Sugeridos")
                if client_data['status'] == "Pendente":
                    st.warning("⚠️ Cliente aguardando retorno. Sugestão: Enviar proposta via WhatsApp.")
                elif client_data['status'] == "Novo":
                    st.success("✨ Lead quente! Iniciar qualificação técnica hoje.")
                else:
                    st.write("Sem ações pendentes para este perfil.")

elif menu == "📈 Inteligência de Produto":
    st.title("📈 O que estamos vendendo?")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Serviços Mais Procurados")
        servicos_count = st.session_state.data_leads['servico'].value_counts().reset_index()
        fig_serv = px.bar(servicos_count, x='servico', y='count', color='servico', 
                         color_discrete_sequence=px.colors.sequential.Viridis)
        fig_serv.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_serv, use_container_width=True)
        
    with col_b:
        st.subheader("Interesse por Categoria")
        nao_compradores = st.session_state.data_leads[st.session_state.data_leads['status'].isin(['Pendente', 'Perdido'])]
        fig_int = px.histogram(nao_compradores, x='interesse', color='servico', barmode='group')
        fig_int.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_int, use_container_width=True)

    st.markdown("---")
    st.subheader("Insights de Conversão")
    st.write("Baseado nas conversas da Sofia, 60% dos clientes que não fecham citam o 'Valor da Entrada' como principal barreira.")
