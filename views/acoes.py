import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA
from modulos.tratamento import formatar_milhar_br, formatar_documento

ARQUIVO_ACOES = "campanhas_ativas.csv"

def carregar_campanhas():
    if os.path.exists(ARQUIVO_ACOES):
        df = pd.read_csv(ARQUIVO_ACOES)
        # Garante que a coluna Status exista para arquivos antigos
        if 'Status' not in df.columns:
            df['Status'] = 'Ativa'
        return df
    return pd.DataFrame(columns=["Titulo", "Tipo", "Meta", "Data_Inicio", "Data_Fim", "Acelerador_Pct", "Descricao", "Status"])

def salvar_campanha_editada(df):
    df.to_csv(ARQUIVO_ACOES, index=False)

def formatar_lista_docs(texto_docs):
    if pd.isna(texto_docs): return ""
    lista = str(texto_docs).split(', ')
    lista_fmt = [formatar_documento(d) for d in lista]
    return ' | '.join(lista_fmt)

def calcular_ganhadores(df_vendas, data_inicio, data_fim, meta, acelerador_pct):
    if isinstance(data_inicio, str): data_inicio = pd.to_datetime(data_inicio).date()
    if isinstance(data_fim, str): data_fim = pd.to_datetime(data_fim).date()
    
    df_vendas['Data da Venda'] = pd.to_datetime(df_vendas['Data da Venda'], errors='coerce')
    mask = (df_vendas['Data da Venda'].dt.date >= data_inicio) & (df_vendas['Data da Venda'].dt.date <= data_fim)
    df_periodo = df_vendas.loc[mask].copy()
    
    if df_periodo.empty: return pd.DataFrame()

    df_resumo = df_periodo.groupby(COLUNA_CHAVE_CONSOLIDADA).agg({
        'Pontos': 'sum',
        COLUNA_ESPECIFICADOR: lambda x: ', '.join(sorted(set(x.astype(str)))), 
        'CNPJ_CPF_LIMPO': lambda x: ', '.join(sorted(set(x.astype(str))))
    }).reset_index()
    
    df_resumo['Pontos Reais'] = df_resumo['Pontos']
    df_resumo['Valor Bônus'] = df_resumo['Pontos'] * (acelerador_pct / 100)
    df_resumo['Total c/ Bônus'] = df_resumo['Pontos Reais'] + df_resumo['Valor Bônus']
    
    ganhadores = df_resumo[df_resumo['Total c/ Bônus'] >= meta].copy()
    ganhadores = ganhadores.sort_values('Total c/ Bônus', ascending=False)
    
    return ganhadores

def show_acoes():
    st.title("🎯 Gestão de Campanhas")
    st.markdown("Crie, edite e **encerre** desafios globais.")

    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_campanhas = carregar_campanhas()

    if 'indice_edicao' not in st.session_state: st.session_state['indice_edicao'] = None

    # --- FORMULÁRIO ---
    defaults = {"Titulo": "", "Tipo": "", "Meta": 1000.0, "Data_Inicio": date.today(), "Data_Fim": date.today(), "Acelerador": 0, "Descricao": ""}
    
    if st.session_state['indice_edicao'] is not None:
        idx = st.session_state['indice_edicao']
        if idx in df_campanhas.index:
            row_edit = df_campanhas.loc[idx]
            defaults.update({
                "Titulo": row_edit['Titulo'], "Tipo": row_edit['Tipo'], "Meta": float(row_edit['Meta']),
                "Data_Inicio": pd.to_datetime(row_edit['Data_Inicio']).date(),
                "Data_Fim": pd.to_datetime(row_edit['Data_Fim']).date(),
                "Acelerador": int(row_edit['Acelerador_Pct']), "Descricao": row_edit['Descricao']
            })

    with st.container(border=True):
        st.subheader("✏️ Editar" if st.session_state['indice_edicao'] is not None else "➕ Nova Campanha")
        if st.session_state['indice_edicao'] is not None and st.button("Cancelar"):
            st.session_state['indice_edicao'] = None; st.rerun()

        with st.form("form_campanha"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Título", defaults["Titulo"])
            tipo = c1.text_input("Prêmio", defaults["Tipo"])
            meta = c1.number_input("Meta Pontos", value=defaults["Meta"], step=500.0)
            periodo = c2.date_input("Período", (defaults["Data_Inicio"], defaults["Data_Fim"]), format="DD/MM/YYYY")
            acelerador = c2.slider("Acelerador %", 0, 50, defaults["Acelerador"])
            desc = st.text_area("Descrição", defaults["Descricao"])
            
            if st.form_submit_button("Salvar"):
                if len(periodo) == 2:
                    new_data = {"Titulo": titulo, "Tipo": tipo, "Meta": meta, "Data_Inicio": periodo[0], "Data_Fim": periodo[1], "Acelerador_Pct": acelerador, "Descricao": desc, "Status": "Ativa"}
                    if st.session_state['indice_edicao'] is not None:
                        for k, v in new_data.items(): df_campanhas.at[st.session_state['indice_edicao'], k] = v
                    else:
                        df_campanhas = pd.concat([df_campanhas, pd.DataFrame([new_data])], ignore_index=True)
                    salvar_campanha_editada(df_campanhas)
                    st.session_state['indice_edicao'] = None; st.rerun()
                else: st.warning("Datas inválidas.")

    # --- LISTAGEM ---
    st.markdown("---")
    if not df_campanhas.empty:
        # Ordena: Ativas primeiro, depois Finalizadas
        df_campanhas['Status_Order'] = df_campanhas['Status'].apply(lambda x: 0 if x == 'Ativa' else 1)
        df_campanhas = df_campanhas.sort_values('Status_Order')
        
        for idx in df_campanhas.index: # Mantém índice original para edição
            row = df_campanhas.loc[idx]
            
            # Cor do Status
            status_emoji = "🟢" if row['Status'] == "Ativa" else "🔴"
            
            with st.expander(f"{status_emoji} {row['Titulo']} ({row['Status']})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Meta", formatar_milhar_br(row['Meta']))
                col2.metric("Acelerador", f"{row['Acelerador_Pct']}%")
                
                try:
                    d_ini = pd.to_datetime(row['Data_Inicio']).strftime('%d/%m/%Y')
                    d_fim = pd.to_datetime(row['Data_Fim']).strftime('%d/%m/%Y')
                except: d_ini, d_fim = row['Data_Inicio'], row['Data_Fim']
                
                # CORREÇÃO AQUI: USANDO col3 EM VEZ DE c3
                col3.write(f"**Período:** {d_ini} até {d_fim}")
                
                st.write(f"**Prêmio:** {row['Tipo']}")
                st.info(row['Descricao'])
                
                # --- AÇÕES GERAIS ---
                if st.button("🏆 Verificar Ganhadores", key=f"win_{idx}"):
                    if not df_global.empty:
                        ganhadores = calcular_ganhadores(df_global, row['Data_Inicio'], row['Data_Fim'], row['Meta'], row['Acelerador_Pct'])
                        if not ganhadores.empty:
                            st.success(f"{len(ganhadores)} Grupos bateram a meta!")
                            exibicao = ganhadores[[COLUNA_CHAVE_CONSOLIDADA, COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO', 'Pontos Reais', 'Valor Bônus', 'Total c/ Bônus']].copy()
                            exibicao['CNPJ_CPF_LIMPO'] = exibicao['CNPJ_CPF_LIMPO'].apply(formatar_lista_docs)
                            exibicao.columns = ['Grupo', 'Nomes', 'Docs', 'Pontos', 'Bônus', 'Total Final']
                            st.dataframe(exibicao.style.format({'Pontos': formatar_milhar_br, 'Bônus': formatar_milhar_br, 'Total Final': formatar_milhar_br}), use_container_width=True)
                        else: st.warning("Ninguém atingiu a meta.")
                
                st.markdown("---")
                # --- BOTÕES DE CONTROLE ---
                c_edit, c_status, c_del = st.columns([1, 1.5, 1])
                
                if c_edit.button("✏️ Editar", key=f"ed_{idx}"): 
                    st.session_state['indice_edicao'] = idx; st.rerun()
                
                # BOTÃO DE TROCAR STATUS
                novo_status = "Finalizada" if row['Status'] == "Ativa" else "Ativa"
                label_status = "⏹️ Finalizar Ação" if row['Status'] == "Ativa" else "▶️ Reativar Ação"
                type_status = "secondary" if row['Status'] == "Ativa" else "primary"
                
                if c_status.button(label_status, key=f"st_{idx}", type=type_status):
                    df_campanhas.at[idx, 'Status'] = novo_status
                    salvar_campanha_editada(df_campanhas)
                    st.rerun()

                if c_del.button("🗑️ Excluir", key=f"dl_{idx}"): 
                    df_campanhas = df_campanhas.drop(idx).reset_index(drop=True)
                    salvar_campanha_editada(df_campanhas); st.rerun()
    else:
        st.info("Nenhuma campanha cadastrada.")