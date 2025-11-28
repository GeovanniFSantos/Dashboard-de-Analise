# app.py
import streamlit as st
from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio

# 1. Configuração da página
st.set_page_config(
    page_title="Gestão Gabriel Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicializa sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_type' not in st.session_state:
    st.session_state['user_type'] = None # 'admin' ou 'arquiteto'
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None # CPF/CNPJ limpo

# Carrega dados globais (Cacheado)
# Isso é importante para o login do arquiteto verificar se o CPF existe
df_global, _ = carregar_e_tratar_dados(Relatorio)

# Imports das Telas
from views import login, dashboard, acoes, architect_page

def main():
    # --- LOGIN ---
    if not st.session_state['logged_in']:
        # Passamos o df_global para o login verificar o CPF
        login.show_login(df_global) 
        return

    # --- ROTEAMENTO BASEADO NO TIPO DE USUÁRIO ---
    
    # 1. VISÃO DO ADMINISTRADOR
    if st.session_state['user_type'] == 'admin':
        with st.sidebar:
            st.title("Menu Admin")
            menu_option = st.radio(
                "Navegação:",
                ["Dashboard de Análise", "Cadastro de Ações"],
                index=0
            )
            st.markdown("---")
            if st.button("Sair"):
                st.session_state['logged_in'] = False
                st.session_state['user_type'] = None
                st.rerun()

        if menu_option == "Dashboard de Análise":
            dashboard.show_dashboard()
        elif menu_option == "Cadastro de Ações":
            acoes.show_acoes()

    # 2. VISÃO DO ARQUITETO
# 2. VISÃO DO ARQUITETO
    elif st.session_state['user_type'] == 'arquiteto':
        # Passamos a USER_KEY (Chave Consolidada) em vez do ID puro
        architect_page.show_architect_dashboard(df_global, st.session_state['user_key'])

if __name__ == "__main__":
    main()