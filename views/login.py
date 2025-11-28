import streamlit as st
import time
from modulos.config import COLUNA_CHAVE_CONSOLIDADA # Importante!

def show_login(df_global):
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Gabriel Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("Administradores: usem usuário/senha.\nArquitetos: usem apenas o CPF/CNPJ (somente números).")
        
        with st.form(key='login_form'):
            username = st.text_input("Usuário ou CPF/CNPJ (apenas números)")
            password = st.text_input("Senha (apenas para Admin)", type="password")
            submit_button = st.form_submit_button(label="Entrar")
            
        if submit_button:
            # 1. TENTA LOGIN ADMIN
            if username == "admin" and password == "1234":
                st.success("Login Admin realizado!")
                time.sleep(0.5)
                st.session_state['logged_in'] = True
                st.session_state['user_type'] = 'admin'
                st.rerun()
            
            # 2. TENTA LOGIN ARQUITETO (Lógica Consolidada)
            else:
                # Remove pontuação do input
                user_input_limpo = str(username).replace('.', '').replace('-', '').replace('/', '').strip()
                
                # Verifica se a coluna de identificação e chave consolidada existem
                if 'CNPJ_CPF_LIMPO' in df_global.columns and COLUNA_CHAVE_CONSOLIDADA in df_global.columns:
                    
                    # Procura o usuário na base
                    usuario_encontrado = df_global[df_global['CNPJ_CPF_LIMPO'] == user_input_limpo]
                    
                    if not usuario_encontrado.empty:
                        # --- O PULO DO GATO ---
                        # Pegamos a Chave Consolidada deste usuário (ex: 'Triplex Arquitetura')
                        chave_do_usuario = usuario_encontrado[COLUNA_CHAVE_CONSOLIDADA].iloc[0]
                        
                        st.success(f"Bem-vindo! Acessando dados de: {chave_do_usuario}")
                        time.sleep(0.5)
                        
                        st.session_state['logged_in'] = True
                        st.session_state['user_type'] = 'arquiteto'
                        st.session_state['user_id'] = user_input_limpo # Documento usado no login
                        st.session_state['user_key'] = chave_do_usuario # CHAVE MESTRA PARA SOMAR PONTOS
                        
                        st.rerun()
                    else:
                        st.error("CPF/CNPJ não encontrado na base de dados.")
                else:
                    st.error("Erro Crítico: Base de dados incompleta (Falta coluna de Chave Consolidada).")