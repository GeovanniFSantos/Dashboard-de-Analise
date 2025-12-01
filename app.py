import streamlit as st
from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio

# 1. Configuração da página (DEVE ser a primeira linha)
st.set_page_config(
    page_title="Gestão Gabriel Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicialização de Estado (Session State)
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_type' not in st.session_state: st.session_state['user_type'] = None # 'admin', 'arquiteto', 'loja'
if 'user_key' not in st.session_state: st.session_state['user_key'] = None # Para o Arquiteto (Chave Consolidada)
if 'user_loja_nome' not in st.session_state: st.session_state['user_loja_nome'] = None # Para a Loja
if 'user_loja_resp' not in st.session_state: st.session_state['user_loja_resp'] = None

# 3. Carregamento de Dados Globais
# Isso é feito aqui para que o Login tenha acesso à lista de CPFs
try:
    df_global, _ = carregar_e_tratar_dados(Relatorio)
except Exception as e:
    st.error(f"Erro crítico ao carregar dados: {e}")
    df_global = None

# 4. Imports das Telas (Views)
# Certifique-se de que os arquivos store_page.py e acelerador_loja.py existem em 'views', mesmo que vazios
try:
    from views import login, dashboard, acoes, architect_page, premios, store_page, acelerador_loja
except ImportError as e:
    st.error(f"Erro ao importar módulos das telas. Verifique se criou os arquivos 'store_page.py' e 'acelerador_loja.py' na pasta views. Detalhe: {e}")
    st.stop()

def main():
    # --- LÓGICA DE LOGIN ---
    if not st.session_state['logged_in']:
        if df_global is not None:
            login.show_login(df_global)
        return

    # --- ROTEAMENTO POR TIPO DE USUÁRIO ---

    # === 1. ADMIN ===
    if st.session_state['user_type'] == 'admin':
        with st.sidebar:
            st.title("Menu Admin")
            menu_option = st.radio(
                "Navegação:",
                ["Dashboard de Análise", "Ações (Arquitetos)", "Premiações", "Acelerador Loja"],
                index=0
            )
            st.markdown("---")
            if st.button("Sair / Logout"):
                st.session_state.clear()
                st.rerun()

        if menu_option == "Dashboard de Análise":
            dashboard.show_dashboard()
        elif menu_option == "Ações (Arquitetos)":
            acoes.show_acoes()
        elif menu_option == "Premiações":
            premios.show_premios()
        elif menu_option == "Acelerador Loja":
            st.title("🔧 Configuração de Acelerador (Admin)")
            st.info("Aqui você poderá configurar metas e aceleradores para as lojas (Em breve).")

    # === 2. LOJA (NOVO) ===
    elif st.session_state['user_type'] == 'loja':
        with st.sidebar:
            # Mostra quem está logado
            st.title(f"Olá, {st.session_state['user_loja_resp']}")
            st.caption(f"Loja: {st.session_state['user_loja_nome']}")
            
            menu_loja = st.radio(
                "Menu:",
                ["Dashboard Loja", "Acelerador"],
                index=0
            )
            st.markdown("---")
            if st.button("Sair"):
                st.session_state.clear()
                st.rerun()
        
        if menu_loja == "Dashboard Loja":
            # Chama a tela da loja passando o DF global e o nome da loja para filtrar
            store_page.show_store_dashboard(df_global, st.session_state['user_loja_nome'])
            
        elif menu_loja == "Acelerador":
            acelerador_loja.show_acelerador(st.session_state['user_loja_nome'])

    # === 3. ARQUITETO ===
    elif st.session_state['user_type'] == 'arquiteto':
        # O Arquiteto vê apenas o seu dashboard consolidado
        architect_page.show_architect_dashboard(df_global, st.session_state['user_key'])

if __name__ == "__main__":
    main()