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
    st.session_state['user_type'] = None
if 'user_key' not in st.session_state:
    st.session_state['user_key'] = None

# Carrega dados globais
df_global, _ = carregar_e_tratar_dados(Relatorio)

# Imports das Telas (ADICIONEI PREMIOS AQUI)
from views import login, dashboard, acoes, architect_page, premios

def main():
    # --- LOGIN ---
    if not st.session_state['logged_in']:
        login.show_login(df_global) 
        return

    # --- ADMIN ---
    if st.session_state['user_type'] == 'admin':
        with st.sidebar:
            st.title("Menu Admin")
            menu_option = st.radio(
                "Navegação:",
                # ADICIONEI "Cadastro de Premiações" AQUI
                ["Dashboard de Análise", "Cadastro de Ações", "Cadastro de Premiações"],
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
        elif menu_option == "Cadastro de Premiações":
            # CHAMA A NOVA TELA
            premios.show_premios()

    # --- ARQUITETO ---
    elif st.session_state['user_type'] == 'arquiteto':
        architect_page.show_architect_dashboard(df_global, st.session_state['user_key'])

if __name__ == "__main__":
    main()