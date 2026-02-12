#!/bin/bash
# Ativa o ambiente virtual
source .venv/bin/activate
# Executa o streamlit com as configurações de rede para o servidor
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
