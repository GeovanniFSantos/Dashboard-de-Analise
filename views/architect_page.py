import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

from modulos.config import COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA
from modulos.tratamento import formatar_milhar_br, calcular_evolucao_pct

CATEGORIES_STYLE = {
    "Pro": {"color": "#94a3b8", "css": "badge-pro", "min": 0},
    "Topázio": {"color": "#38bdf8", "css": "badge-topazio", "min": 150000},
    "Ruby": {"color": "#ef4444", "css": "badge-rubi", "min": 500000},
    "Esmeralda": {"color": "#10b981", "css": "badge-esmeralda", "min": 2000000},
    "Diamante": {"color": "#7c3aed", "css": "badge-diamante", "min": 5000000}
}

ARQUIVO_ACOES = "campanhas_ativas.csv"

def carregar_campanhas_ativas():
    if os.path.exists(ARQUIVO_ACOES):
        df = pd.read_csv(ARQUIVO_ACOES)
        df['Data_Inicio'] = pd.to_datetime(df['Data_Inicio'], errors='coerce').dt.date
        df['Data_Fim'] = pd.to_datetime(df['Data_Fim'], errors='coerce').dt.date
        # Garante coluna status
        if 'Status' not in df.columns: df['Status'] = 'Ativa'
        return df.dropna(subset=['Data_Inicio', 'Data_Fim'])
    return pd.DataFrame()

def calcular_progresso_campanha(df_vendas_consolidado, campanha):
    mask = (df_vendas_consolidado['Data da Venda'].dt.date >= campanha['Data_Inicio']) & \
           (df_vendas_consolidado['Data da Venda'].dt.date <= campanha['Data_Fim'])
    pontos_reais = df_vendas_consolidado.loc[mask, 'Pontos'].sum()
    pontos_com_bonus = pontos_reais * (1 + campanha['Acelerador_Pct'] / 100)
    return pontos_reais, pontos_com_bonus

def calcular_evolucao_ajustada(df_consolidado, temporada_atual_nome):
    try:
        num_atual = int(temporada_atual_nome.split(' ')[1])
        num_anterior = num_atual - 1
        temporada_anterior_nome = f"Temporada {num_anterior}"
        
        df_atual = df_consolidado[df_consolidado['Temporada_Exibicao'] == temporada_atual_nome]
        if df_atual.empty: return 0, "N/A", ""
        
        pontos_atual = df_atual['Pontos'].sum()
        meses_presentes = df_atual['Mês_Exibicao'].unique()
        
        df_anterior = df_consolidado[
            (df_consolidado['Temporada_Exibicao'] == temporada_anterior_nome) &
            (df_consolidado['Mês_Exibicao'].isin(meses_presentes))
        ]
        
        pontos_anterior_ajustado = df_anterior['Pontos'].sum()
        evolucao = calcular_evolucao_pct(pontos_atual, pontos_anterior_ajustado)
        
        if pontos_anterior_ajustado == 0:
            txt_evolucao = "Novo" if pontos_atual > 0 else "-"
        else:
            txt_evolucao = f"{evolucao:+.1%}"
            
        return evolucao, txt_evolucao, temporada_anterior_nome
    except: return 0, "Erro", ""

def get_category_details(points):
    sorted_cats = sorted(CATEGORIES_STYLE.items(), key=lambda x: x[1]['min'])
    current_cat_data = CATEGORIES_STYLE["Pro"]
    current_cat_data['name'] = "Pro"
    next_cat_data = None
    
    for i, (name, data) in enumerate(sorted_cats):
        if points >= data['min']:
            current_cat_data = data
            current_cat_data['name'] = name
            if i + 1 < len(sorted_cats):
                next_cat_data = sorted_cats[i+1][1]
                next_cat_data['name'] = sorted_cats[i+1][0]
            else:
                next_cat_data = None
    return current_cat_data, next_cat_data

def show_architect_dashboard(df_global, user_key):
    st.markdown("""
    <style>
        .badge { padding: 4px 12px; border-radius: 999px; font-weight: bold; font-size: 0.9rem; display: inline-block; }
        .badge-diamante { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
        .badge-esmeralda { background-color: #d1fae5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-rubi { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-topazio { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-pro { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
        .prog-container { width: 100%; background-color: #334155; border-radius: 999px; height: 16px; margin-top: 5px; overflow: hidden; }
        .prog-fill { height: 100%; border-radius: 999px; transition: width 1s ease-in-out; }
        .vinculos-box { font-size: 0.8rem; color: #64748b; background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

    df_consolidado = df_global[df_global[COLUNA_CHAVE_CONSOLIDADA] == user_key].copy()
    if df_consolidado.empty:
        st.error(f"Dados não encontrados para: {user_key}")
        return

    col_h1, col_h2 = st.columns([5, 1])
    col_h1.title(f"Bem-vindo(a), {user_key}")
    if col_h2.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

    qtd_docs = len(df_consolidado['CNPJ_CPF_LIMPO'].unique())
    if qtd_docs > 1:
        st.markdown(f"<div class='vinculos-box'><b>🔗 Conta Consolidada:</b> Pontuação somada de {qtd_docs} documentos vinculados.</div>", unsafe_allow_html=True)

    # --- BANNER ---
    if 'Temporada_Exibicao' in df_consolidado.columns:
        todas_temporadas = sorted(df_consolidado['Temporada_Exibicao'].unique(), reverse=True)
        selected_season = st.selectbox("📅 Temporada", todas_temporadas)
        df_season = df_consolidado[df_consolidado['Temporada_Exibicao'] == selected_season]
    else:
        df_season = df_consolidado
        selected_season = "Atual"

    total_points = df_season['Pontos'].sum()
    current_cat, next_cat = get_category_details(total_points)
    val_evolucao, txt_evolucao, nome_temp_anterior = calcular_evolucao_ajustada(df_consolidado, selected_season)
    
    cor_evolucao = "#10b981" if val_evolucao > 0 else ("#ef4444" if val_evolucao < 0 else "#94a3b8")
    icone_evolucao = "▲" if val_evolucao > 0 else ("▼" if val_evolucao < 0 else "•")

    if next_cat:
        range_pts = next_cat["min"] - current_cat["min"]
        achieved = total_points - current_cat["min"]
        pct_main = (achieved / range_pts) * 100 if range_pts > 0 else 0
        pct_main = min(max(pct_main, 2), 100)
        msg_meta = f"Faltam <b>{formatar_milhar_br(next_cat['min'] - total_points)}</b> para {next_cat['name']}"
    else:
        pct_main = 100
        msg_meta = "🏆 Topo alcançado!"

    # CORREÇÃO DO HTML (SEM ESPAÇOS NA MARGEM)
    st.markdown(f"""
<div style="background: linear-gradient(90deg, #0f172a 0%, #334155 100%); padding: 25px; border-radius: 16px; color: white; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
<div style="display:flex; justify-content: space-between; align-items:flex-start;">
<div>
<p style="margin:0; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Performance • {selected_season}</p>
<div style="display:flex; align-items:flex-end; gap:15px;">
<div style="display:flex; align-items:baseline; gap:8px;">
<span style="font-size: 2.8rem; font-weight: 800;">{formatar_milhar_br(total_points)}</span>
<span style="font-size: 1rem; color: #cbd5e1;">pontos</span>
</div>
<div style="margin-bottom: 8px; background: rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 8px;">
<span style="color: {cor_evolucao}; font-weight: bold; font-size: 0.9rem;">
{icone_evolucao} {txt_evolucao}
</span>
<span style="font-size: 0.75rem; color: #94a3b8; margin-left: 5px;">vs {nome_temp_anterior} (Mesmo período)</span>
</div>
</div>
</div>
<span class="badge {current_cat['css']}" style="font-size: 1rem;">{current_cat['name']}</span>
</div>
<div style="margin-top: 15px;">
<div style="display:flex; justify-content: space-between; font-size: 0.85rem; color: #cbd5e1; margin-bottom: 5px;">
<span>Progresso Categoria</span>
<span>{msg_meta}</span>
</div>
<div class="prog-container">
<div class="prog-fill" style="width: {pct_main}%; background-color: {current_cat['color']};"></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # --- CAMPANHAS ---
    st.subheader("🔥 Campanhas & Desafios")
    df_campanhas = carregar_campanhas_ativas()
    
    if not df_campanhas.empty:
        # Ordena: Ativas primeiro
        df_campanhas['Order'] = df_campanhas['Status'].apply(lambda x: 0 if x == 'Ativa' else 1)
        df_campanhas = df_campanhas.sort_values(['Order', 'Data_Fim'])
        
        for _, acao in df_campanhas.iterrows():
            pts_reais, pts_bonus = calcular_progresso_campanha(df_consolidado, acao)
            meta = acao['Meta']
            pct_acao = (pts_bonus / meta) * 100 if meta > 0 else 0
            pct_acao = min(pct_acao, 100)
            
            # Lógica Visual Baseada no Status
            is_ativa = acao['Status'] == 'Ativa'
            bateu_meta = pts_bonus >= meta
            
            if is_ativa:
                bg_color = "#1e293b" # Azul escuro padrão
                opacity = "1"
                cor_barra = "#10b981" if bateu_meta else "#3b82f6"
                status_txt = "✅ META BATIDA!" if bateu_meta else f"Faltam {formatar_milhar_br(meta - pts_bonus)}"
                tag_status = ""
            else:
                # Finalizada
                bg_color = "#334155" # Cinza
                opacity = "0.7"
                cor_barra = "#fbbf24" if bateu_meta else "#64748b" # Dourado se ganhou, cinza se perdeu
                status_txt = "🏆 VOCÊ GANHOU!" if bateu_meta else "ENCERRADA (Não atingida)"
                tag_status = "<span style='background:#ef4444; color:white; font-size:0.6rem; padding:2px 6px; border-radius:4px; margin-left:10px;'>FINALIZADA</span>"

            st.markdown(f"""
<div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; color: white; margin-bottom: 15px; border: 1px solid #475569; opacity: {opacity}; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
<div style="display:flex; justify-content:space-between; margin-bottom: 10px;">
<div>
<strong style="font-size: 1.1rem; color: #f8fafc;">{acao['Titulo']} {tag_status}</strong>
<div style="font-size: 0.8rem; color: #94a3b8;">{acao['Tipo']} • Até {acao['Data_Fim'].strftime('%d/%m/%Y')}</div>
</div>
<div style="text-align:right;">
<div style="font-size: 0.8rem; color: #cbd5e1;">Acelerador</div>
<strong style="color: #fbbf24;">+{acao['Acelerador_Pct']}%</strong>
</div>
</div>
<div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 10px;">
{acao['Descricao']}
</div>
<div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
<div style="display:flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 5px;">
<span>
Pontos: <b>{formatar_milhar_br(pts_reais)}</b> <span style="color:#fbbf24;">(+{formatar_milhar_br(pts_bonus - pts_reais)})</span>
</span>
<span style="color: {cor_barra}; font-weight: bold;">{status_txt}</span>
</div>
<div class="prog-container" style="height: 10px; background-color: #0f172a;">
<div class="prog-fill" style="width: {pct_acao}%; background-color: {cor_barra};"></div>
</div>
<div style="text-align: right; font-size: 0.75rem; color: #64748b; margin-top: 4px;">
Meta: {formatar_milhar_br(meta)} pontos
</div>
</div>
</div>
""", unsafe_allow_html=True)
    else: st.info("Nenhuma campanha registrada.")

    # --- EXTRATO ---
    st.markdown("---")
    st.subheader("📊 Extrato Detalhado")
    tab1, tab2 = st.tabs(["Extrato", "Gráfico"])
    
    with tab1:
        if not df_season.empty:
            df_view = df_season[['Data da Venda', 'Especificador/Empresa', 'Loja', 'Pontos']].copy()
            try: df_view['Data da Venda'] = pd.to_datetime(df_view['Data da Venda']).dt.strftime('%d/%m/%Y')
            except: pass
            st.dataframe(df_view.sort_values('Data da Venda', ascending=False), use_container_width=True, hide_index=True, column_config={"Pontos": st.column_config.NumberColumn(format="%.0f")})
        else: st.info("Sem compras.")
            
    with tab2:
        if not df_season.empty:
            st.plotly_chart(px.pie(df_season.groupby('Segmento')['Pontos'].sum().reset_index(), values='Pontos', names='Segmento', hole=0.4).update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300), use_container_width=True)
        else: st.info("Sem dados.")