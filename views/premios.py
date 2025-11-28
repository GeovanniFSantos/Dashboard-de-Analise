import streamlit as st
import pandas as pd
import os

from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA
from modulos.tratamento import formatar_milhar_br, formatar_documento

ARQUIVO_PREMIOS = "premios_temporada.csv"

def carregar_premios():
    if os.path.exists(ARQUIVO_PREMIOS):
        return pd.read_csv(ARQUIVO_PREMIOS)
    return pd.DataFrame(columns=["Titulo", "Pontos_Meta", "Temporada", "Descricao", "Status"])

def salvar_premios_editado(df):
    df.to_csv(ARQUIVO_PREMIOS, index=False)

def formatar_lista_docs(texto_docs):
    if pd.isna(texto_docs): return ""
    lista = str(texto_docs).split(', ')
    lista_fmt = [formatar_documento(d) for d in lista]
    return ' | '.join(lista_fmt)

def calcular_ganhadores_premio(df_global, temporada, meta_pontos):
    """
    Calcula quem bateu a meta de pontos DENTRO da temporada específica.
    """
    # 1. Filtra a temporada no DataFrame Global
    df_season = df_global[df_global['Temporada_Exibicao'] == temporada].copy()
    
    if df_season.empty:
        return pd.DataFrame()

    # 2. Agrupa por Chave Consolidada
    df_resumo = df_season.groupby(COLUNA_CHAVE_CONSOLIDADA).agg({
        'Pontos': 'sum',
        COLUNA_ESPECIFICADOR: lambda x: ', '.join(sorted(set(x.astype(str)))), 
        'CNPJ_CPF_LIMPO': lambda x: ', '.join(sorted(set(x.astype(str))))
    }).reset_index()
    
    # 3. Filtra quem tem pontos >= meta
    ganhadores = df_resumo[df_resumo['Pontos'] >= meta_pontos].copy()
    ganhadores = ganhadores.sort_values('Pontos', ascending=False)
    
    return ganhadores

def show_premios():
    st.title("🏆 Cadastro de Premiações (Metas da Temporada)")
    st.markdown("Defina os prêmios anuais/sazonais baseados na pontuação acumulada da temporada.")

    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_premios = carregar_premios()

    # Lista de Temporadas disponíveis no Relatório (para o Selectbox)
    if 'Temporada_Exibicao' in df_global.columns:
        lista_temporadas = sorted(df_global['Temporada_Exibicao'].dropna().unique(), reverse=True)
    else:
        lista_temporadas = ["Temporada Atual"]

    # --- CONTROLE DE EDIÇÃO ---
    if 'idx_edit_premio' not in st.session_state: st.session_state['idx_edit_premio'] = None

    defaults = {"Titulo": "", "Pontos": 50000.0, "Temporada": lista_temporadas[0], "Descricao": ""}
    
    if st.session_state['idx_edit_premio'] is not None:
        idx = st.session_state['idx_edit_premio']
        if idx in df_premios.index:
            row = df_premios.loc[idx]
            defaults.update({
                "Titulo": row['Titulo'], 
                "Pontos": float(row['Pontos_Meta']), 
                "Temporada": row['Temporada'],
                "Descricao": row['Descricao']
            })

    # --- FORMULÁRIO ---
    with st.container(border=True):
        header_txt = "✏️ Editar Prêmio" if st.session_state['idx_edit_premio'] is not None else "➕ Novo Prêmio"
        c_h, c_c = st.columns([5,1])
        c_h.subheader(header_txt)
        if st.session_state['idx_edit_premio'] is not None and c_c.button("Cancelar"):
            st.session_state['idx_edit_premio'] = None; st.rerun()

        with st.form("form_premio"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Nome do Prêmio", defaults["Titulo"], placeholder="Ex: Viagem Paris, Carro Zero")
            temporada = c2.selectbox("Temporada", options=lista_temporadas, index=lista_temporadas.index(defaults["Temporada"]) if defaults["Temporada"] in lista_temporadas else 0)
            
            pontos = st.number_input("Meta de Pontos", min_value=0.0, value=defaults["Pontos"], step=1000.0, help="Pontuação acumulada na temporada para ganhar")
            desc = st.text_area("Descrição / Detalhes", defaults["Descricao"])
            
            if st.form_submit_button("💾 Salvar Prêmio"):
                if not titulo:
                    st.warning("Nome do prêmio é obrigatório.")
                else:
                    novo_dado = {
                        "Titulo": titulo, "Pontos_Meta": pontos, 
                        "Temporada": temporada, "Descricao": desc, "Status": "Ativo"
                    }
                    if st.session_state['idx_edit_premio'] is not None:
                        for k, v in novo_dado.items(): df_premios.at[st.session_state['idx_edit_premio'], k] = v
                    else:
                        df_premios = pd.concat([df_premios, pd.DataFrame([novo_dado])], ignore_index=True)
                    
                    salvar_premios_editado(df_premios)
                    st.session_state['idx_edit_premio'] = None
                    st.success("Prêmio salvo!"); st.rerun()

    # --- LISTAGEM ---
    st.markdown("---")
    st.subheader("🎁 Prêmios Cadastrados")
    
    if not df_premios.empty:
        # Ordena por Temporada e depois por Meta de Pontos (do menor para o maior)
        df_premios = df_premios.sort_values(['Temporada', 'Pontos_Meta'])
        
        for idx in df_premios.index:
            row = df_premios.loc[idx]
            emoji_status = "🟢" if row['Status'] == "Ativo" else "🔴"
            
            with st.expander(f"{emoji_status} {row['Titulo']} | {formatar_milhar_br(row['Pontos_Meta'])} pts | {row['Temporada']}"):
                st.write(f"**Descrição:** {row['Descricao']}")
                
                c_win, c_edit, c_stat, c_del = st.columns([2, 1, 1.5, 1])
                
                # VERIFICAR GANHADORES
                if c_win.button("🏆 Quem já ganhou?", key=f"win_p_{idx}"):
                    ganhadores = calcular_ganhadores_premio(df_global, row['Temporada'], row['Pontos_Meta'])
                    if not ganhadores.empty:
                        st.success(f"{len(ganhadores)} Grupos atingiram a meta!")
                        exibicao = ganhadores[[COLUNA_CHAVE_CONSOLIDADA, COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO', 'Pontos']].copy()
                        exibicao['CNPJ_CPF_LIMPO'] = exibicao['CNPJ_CPF_LIMPO'].apply(formatar_lista_docs)
                        exibicao.columns = ['Grupo', 'Nomes', 'Docs', 'Pontos Totais']
                        st.dataframe(exibicao.style.format({'Pontos Totais': formatar_milhar_br}), use_container_width=True)
                    else:
                        st.warning("Ninguém atingiu esta pontuação na temporada selecionada ainda.")

                if c_edit.button("Editar", key=f"ed_p_{idx}"):
                    st.session_state['idx_edit_premio'] = idx; st.rerun()
                
                # MUDAR STATUS
                lbl_st = "Pausar" if row['Status'] == "Ativo" else "Ativar"
                if c_stat.button(lbl_st, key=f"st_p_{idx}"):
                    df_premios.at[idx, 'Status'] = "Inativo" if row['Status'] == "Ativo" else "Ativo"
                    salvar_premios_editado(df_premios); st.rerun()
                    
                if c_del.button("Excluir", key=f"del_p_{idx}"):
                    df_premios = df_premios.drop(idx).reset_index(drop=True)
                    salvar_premios_editado(df_premios); st.rerun()
    else:
        st.info("Nenhum prêmio cadastrado.")