import streamlit as st

def show_acelerador(store_name):
    st.title(f"🚀 Acelerador de Vendas: {store_name}")
    
    st.markdown("---")
    
    st.warning("🚧 **Módulo em Construção**")
    st.info("Em breve, você poderá acompanhar suas metas mensais, aceleradores de pontuação e simular cenários de vendas aqui.")
    
    # --- EXEMPLO VISUAL (Apenas para ilustrar o layout futuro) ---
    st.markdown("### 🔮 O que vem por aí...")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Meta do Mês (Exemplo)", "500.000 pts")
    with col2:
        st.metric("Realizado", "350.000 pts")
    with col3:
        st.metric("Falta", "150.000 pts", delta="-30%")
    
    st.write("Progresso da Meta:")
    st.progress(0.70) # 70%