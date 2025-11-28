import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# Importando módulos existentes
from modulos.config import COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA, COLUNA_NUMERO_TEMPORADA, COLUNA_PEDIDO
from modulos.tratamento import formatar_milhar_br, calcular_evolucao_pct

# --- CONSTANTES E CONFIGURAÇÕES ---
CATEGORIES_STYLE = {
    "Pro": {"color": "#94a3b8", "css": "badge-pro", "min": 0},
    "Topázio": {"color": "#38bdf8", "css": "badge-topazio", "min": 150000},
    "Ruby": {"color": "#ef4444", "css": "badge-rubi", "min": 500000},
    "Esmeralda": {"color": "#10b981", "css": "badge-esmeralda", "min": 2000000},
    "Diamante": {"color": "#7c3aed", "css": "badge-diamante", "min": 5000000}
}

ARQUIVO_ACOES = "campanhas_ativas.csv"
ARQUIVO_PREMIOS = "premios_temporada.csv"

# --- FUNÇÕES DE CARREGAMENTO ---
def carregar_campanhas_ativas():
    if os.path.exists(ARQUIVO_ACOES):
        df = pd.read_csv(ARQUIVO_ACOES)
        df['Data_Inicio'] = pd.to_datetime(df['Data_Inicio'], errors='coerce').dt.date
        df['Data_Fim'] = pd.to_datetime(df['Data_Fim'], errors='coerce').dt.date
        if 'Status' not in df.columns: df['Status'] = 'Ativa'
        return df.dropna(subset=['Data_Inicio', 'Data_Fim'])
    return pd.DataFrame()

def carregar_premios_temporada(temporada):
    if os.path.exists(ARQUIVO_PREMIOS):
        df = pd.read_csv(ARQUIVO_PREMIOS)
        if 'Status' not in df.columns: df['Status'] = 'Ativo'
        return df[(df['Temporada'] == temporada) & (df['Status'] == 'Ativo')].sort_values('Pontos_Meta')
    return pd.DataFrame()

# --- FUNÇÕES DE CÁLCULO ---
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
            if i + 1 < len(sorted_cats): next_cat_data = sorted_cats[i+1][1]; next_cat_data['name'] = sorted_cats[i+1][0]
            else: next_cat_data = None
    return current_cat_data, next_cat_data

def calcular_tabela_historico(df_consolidado, temporadas_lista):
    metricas = {
        'Pontuação': [],
        'Quantidade de Pedidos': [],
        'Quantidade de Lojas': [],
        'Valor Médio de Pedidos': [],
        'Quantidade de Segmentos': []
    }
    
    try:
        cols_temporadas = sorted(temporadas_lista, key=lambda x: int(x.split(' ')[1]))
    except:
        cols_temporadas = sorted(temporadas_lista)
    
    for temp in cols_temporadas:
        df_t = df_consolidado[df_consolidado['Temporada_Exibicao'] == temp]
        pontos = df_t['Pontos'].sum()
        pedidos = df_t[COLUNA_PEDIDO].nunique() if COLUNA_PEDIDO in df_t.columns else 0
        lojas = df_t['Loja'].nunique()
        segmentos = df_t['Segmento'].nunique()
        val_medio = pontos / pedidos if pedidos > 0 else 0
        
        metricas['Pontuação'].append(formatar_milhar_br(pontos))
        metricas['Quantidade de Pedidos'].append(formatar_milhar_br(pedidos))
        metricas['Quantidade de Lojas'].append(int(lojas))
        metricas['Valor Médio de Pedidos'].append(formatar_milhar_br(val_medio))
        metricas['Quantidade de Segmentos'].append(int(segmentos))

    return pd.DataFrame(metricas, index=cols_temporadas).T

def calcular_evolucao_mensal(df_consolidado, metrica_coluna='Pontos'):
    df_pivot = df_consolidado.pivot_table(
        index='Mês_Exibicao', 
        columns='Temporada_Exibicao', 
        values=metrica_coluna, 
        aggfunc='sum' if metrica_coluna == 'Pontos' else 'nunique',
        fill_value=0
    )
    
    def get_fiscal_order(mes_str):
        try:
            num = int(mes_str.split('(')[1].replace(')', ''))
            return num - 6 if num >= 7 else num + 6
        except: return 99
    df_pivot = df_pivot.sort_index(key=lambda index: index.map(get_fiscal_order))

    try: cols = sorted(df_pivot.columns, key=lambda x: int(x.split(' ')[1]))
    except: cols = sorted(df_pivot.columns)
    df_pivot = df_pivot[cols]

    if len(cols) >= 2:
        t_atual = cols[-1]; t_ant = cols[-2]   
        df_pivot['Evolução T/T-1'] = df_pivot.apply(lambda row: calcular_evolucao_pct(row[t_atual], row[t_ant]), axis=1)
        def fmt_evol(val): return "-" if val == 0 else f"{val:+.1%}"
        df_pivot['Evolução'] = df_pivot['Evolução T/T-1'].apply(fmt_evol)
        df_pivot = df_pivot.drop(columns=['Evolução T/T-1'])
        
    return df_pivot

def calcular_analise_segmento(df_season):
    df_seg = df_season.groupby('Segmento').agg({
        'Pontos': 'sum',
        COLUNA_PEDIDO: 'nunique'
    }).reset_index()
    df_seg = df_seg.sort_values('Pontos', ascending=False)
    return df_seg

# --- FUNÇÃO PRINCIPAL DA TELA ---
def show_architect_dashboard(df_global, user_key):
    # CSS AJUSTADO: Fontes maiores para tabelas e cards
    st.markdown("""
    <style>
        .badge { padding: 4px 12px; border-radius: 999px; font-weight: bold; font-size: 1rem; display: inline-block; }
        .badge-diamante { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
        .badge-esmeralda { background-color: #d1fae5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-rubi { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-topazio { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-pro { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
        
        .prog-container { width: 100%; background-color: rgba(128, 128, 128, 0.2); border-radius: 999px; height: 16px; margin-top: 5px; overflow: hidden; }
        .prog-fill { height: 100%; border-radius: 999px; transition: width 1s ease-in-out; }
        
        .vinculos-box { font-size: 0.9rem; opacity: 0.8; padding: 10px; border-radius: 8px; border: 1px solid rgba(128, 128, 128, 0.2); margin-bottom: 20px; }
        
        /* Card Adaptativo ao Tema com fonte maior */
        .card-adaptativo { 
            padding: 15px; 
            border-radius: 12px; 
            margin-bottom: 10px; 
            border: 1px solid rgba(128, 128, 128, 0.2); 
            background-color: rgba(128, 128, 128, 0.05);
            display: flex; 
            flex-direction: column; 
            justify-content: space-between;
            font-size: 1rem;
        }
        
        /* Aumento da fonte global das tabelas */
        .stDataFrame { font-size: 1.1rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
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

    # SELEÇÃO DE TEMPORADA (CORRIGIDO: Ordenação Numérica para pegar a maior como padrão)
    if 'Temporada_Exibicao' in df_consolidado.columns:
        try:
            todas_temporadas = sorted(df_consolidado['Temporada_Exibicao'].unique(), key=lambda x: int(x.split(' ')[1]), reverse=True)
        except:
            todas_temporadas = sorted(df_consolidado['Temporada_Exibicao'].unique(), reverse=True)
            
        selected_season = st.selectbox("📅 Temporada Atual", todas_temporadas, index=0)
        df_season = df_consolidado[df_consolidado['Temporada_Exibicao'] == selected_season]
    else:
        df_season = df_consolidado
        selected_season = "Atual"
        todas_temporadas = []

    total_points = df_season['Pontos'].sum()
    current_cat, next_cat = get_category_details(total_points)
    val_evolucao, txt_evolucao, nome_temp_anterior = calcular_evolucao_ajustada(df_consolidado, selected_season)
    
    cor_evolucao = "#10b981" if val_evolucao > 0 else ("#ef4444" if val_evolucao < 0 else "#9ca3af")
    icone_evolucao = "▲" if val_evolucao > 0 else ("▼" if val_evolucao < 0 else "•")

    if next_cat:
        range_pts = next_cat["min"] - current_cat["min"]
        achieved = total_points - current_cat["min"]
        pct_main = (achieved / range_pts) * 100 if range_pts > 0 else 0
        pct_main = min(max(pct_main, 2), 100)
        # AUMENTADO FONTE DA META
        msg_meta = f"Faltam <b style='font-size:1.1rem;'>{formatar_milhar_br(next_cat['min'] - total_points)}</b> para {next_cat['name']}"
    else:
        pct_main = 100
        msg_meta = "🏆 Topo alcançado!"

    # --- BANNER PRINCIPAL (Fontes Aumentadas) ---
    st.markdown(f"""
<div style="background: linear-gradient(90deg, #0f172a 0%, #334155 100%); padding: 25px; border-radius: 16px; color: white; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
<div style="display:flex; justify-content: space-between; align-items:flex-start;">
<div>
<p style="margin:0; font-size: 0.9rem; color: #94a3b8; text-transform: uppercase;">Performance • {selected_season}</p>
<div style="display:flex; align-items:flex-end; gap:15px;">
<div style="display:flex; align-items:baseline; gap:8px;">
<span style="font-size: 3.5rem; font-weight: 800;">{formatar_milhar_br(total_points)}</span>
<span style="font-size: 1.2rem; color: #cbd5e1;">pontos</span>
</div>
<div style="margin-bottom: 12px; background: rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 8px;">
<span style="color: {cor_evolucao}; font-weight: bold; font-size: 1rem;">
{icone_evolucao} {txt_evolucao}
</span>
<span style="font-size: 0.85rem; color: #94a3b8; margin-left: 5px;">vs {nome_temp_anterior} (Mesmo período)</span>
</div>
</div>
</div>
<span class="badge {current_cat['css']}">{current_cat['name']}</span>
</div>
<div style="margin-top: 15px;">
<div style="display:flex; justify-content: space-between; font-size: 1rem; color: #cbd5e1; margin-bottom: 5px;">
<span>Progresso Categoria</span>
<span>{msg_meta}</span>
</div>
<div class="prog-container">
<div class="prog-fill" style="width: {pct_main}%; background-color: {current_cat['color']};"></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # --- BLOCO 1: PRÊMIOS ---
    df_premios = carregar_premios_temporada(selected_season)
    if not df_premios.empty:
        lista_premios = df_premios.to_dict('records')
        with st.expander(f"🎁 Prêmios {selected_season} (Clique para visualizar)", expanded=False):
            st.markdown("Acompanhe suas conquistas de premiação nesta temporada.")
            for i in range(0, len(lista_premios), 2):
                col1, col2 = st.columns(2)
                
                def draw_premio(row, col):
                    meta = row['Pontos_Meta']; conqu = total_points >= meta
                    ic_st = "✅" if conqu else "🔒"; cor_st = "#10b981" if conqu else "gray"
                    # AUMENTADO FONTE DO "FALTA X"
                    txt_f = "" if conqu else f"<span style='color:#f87171; font-size:0.9rem; font-weight:bold;'>Falta {formatar_milhar_br(meta - total_points)}</span>"
                    pct_p = min((total_points / meta) * 100 if meta > 0 else 0, 100); cor_b = "#10b981" if conqu else "#3b82f6"
                    
                    col.markdown(f"""<div class="card-adaptativo" style="height: 150px;"><div><div style="display:flex; justify-content:space-between;"><strong style="font-size:1.1rem; line-height:1.2;">{row['Titulo']}</strong><span style="color:{cor_st}; font-size:1rem;">{ic_st}</span></div><div style="font-size:0.9rem; opacity:0.8; margin-top:6px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">{row['Descricao']}</div></div><div style="margin-top:10px;"><div style="display:flex; justify-content:space-between; font-size:0.9rem;"><span>Meta: {formatar_milhar_br(meta)}</span>{txt_f}</div><div style="width:100%; background:rgba(128,128,128,0.2); height:8px; border-radius:99px; margin-top:4px;"><div style="width:{pct_p}%; background:{cor_b}; height:100%; border-radius:99px;"></div></div></div></div>""", unsafe_allow_html=True)

                draw_premio(lista_premios[i], col1)
                if i+1 < len(lista_premios): draw_premio(lista_premios[i+1], col2)
        st.markdown("---")

    # --- BLOCO 2: CAMPANHAS ---
    df_campanhas = carregar_campanhas_ativas()
    if not df_campanhas.empty:
        df_campanhas['Order'] = df_campanhas['Status'].apply(lambda x: 0 if x == 'Ativa' else 1)
        campanhas_ativas = df_campanhas.sort_values(['Order', 'Data_Fim'])
        if not campanhas_ativas.empty:
            lista_campanhas = campanhas_ativas.to_dict('records')
            with st.expander("🔥 Campanhas & Aceleradores (Clique para visualizar)", expanded=False):
                for i in range(0, len(lista_campanhas), 2):
                    col1, col2 = st.columns(2)
                    def draw_card(acao, container):
                        pts_reais, pts_bonus = calcular_progresso_campanha(df_consolidado, acao)
                        meta = acao['Meta']; pct = min((pts_bonus/meta)*100 if meta>0 else 0, 100)
                        is_atv = acao['Status']=='Ativa'; bat_m = pts_bonus >= meta
                        st_tx = "META BATIDA!" if bat_m else f"Faltam {formatar_milhar_br(meta-pts_bonus)}"
                        cor_st_tx = "#10b981" if bat_m else "#3b82f6"
                        tg = "" if is_atv else "<span style='background:#ef4444; color:white; font-size:0.65rem; padding:3px 6px; border-radius:4px; margin-left:6px; vertical-align: middle;'>FINALIZADA</span>"
                        if not is_atv and bat_m: st_tx="🏆 GANHOU!"; cor_st_tx="#fbbf24"
                        try: d_f = acao['Data_Fim'].strftime('%d/%m/%Y')
                        except: d_f = str(acao['Data_Fim'])
                        
                        container.markdown(f"""<div class="card-adaptativo" style="height:240px;"><div><div style="display:flex; justify-content:space-between;"><div style="line-height:1.1;"><strong style="font-size:1.1rem;">{acao['Titulo']}</strong>{tg}<div style="font-size:0.8rem; opacity:0.8; margin-top:4px;">{acao['Tipo']} • Até {d_f}</div></div><div style="text-align:right; min-width:50px;"><div style="font-size:0.75rem; opacity:0.8;">Acelerador</div><strong style="color:#fbbf24; font-size:1.1rem;">+{acao['Acelerador_Pct']}%</strong></div></div><div style="font-size:0.9rem; opacity:0.8; margin-bottom:12px; line-height:1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin-top:8px;">{acao['Descricao']}</div></div><div style="background:rgba(128,128,128,0.05); padding:12px; border-radius:10px;"><div style="display:flex; justify-content:space-between; font-size:0.9rem; margin-bottom:6px;"><span><b>{formatar_milhar_br(pts_reais)}</b> <span style="color:#fbbf24; font-size:0.8rem;">(+{formatar_milhar_br(pts_bonus-pts_reais)})</span></span><span style="color:{cor_st_tx}; font-weight:bold;">{st_tx}</span></div><div class="prog-container" style="height:10px; margin-top:0;"><div class="prog-fill" style="width:{pct}%; background:{cor_st_tx};"></div></div><div style="text-align:right; font-size:0.8rem; opacity:0.7; margin-top:4px;">Meta: {formatar_milhar_br(meta)} pts</div></div></div>""", unsafe_allow_html=True)
                    
                    with col1: draw_card(lista_campanhas[i], col1)
                    if i+1 < len(lista_campanhas): 
                        with col2: draw_card(lista_campanhas[i+1], col2)
        st.markdown("---")

    # --- HISTÓRICO DESEMPENHO ---
    st.subheader("📈 Histórico de Desempenho")
    if todas_temporadas:
        temps_com_dados = [t for t in todas_temporadas if not df_consolidado[df_consolidado['Temporada_Exibicao'] == t].empty]
        if temps_com_dados:
            df_hist_tabela = calcular_tabela_historico(df_consolidado, temps_com_dados)
            st.dataframe(df_hist_tabela, use_container_width=True)
            
            st.markdown("###### Evolução Mensal (Pontuação)")
            df_evol_pontos = calcular_evolucao_mensal(df_consolidado, 'Pontos')
            def color_evol(val):
                if isinstance(val, str) and '-' in val and len(val) > 1: return 'color: #ef4444; font-weight: bold;'
                if isinstance(val, str) and '+' in val: return 'color: #10b981; font-weight: bold;'
                return ''
            if 'Evolução' in df_evol_pontos.columns:
                st.dataframe(df_evol_pontos.style.applymap(color_evol, subset=['Evolução']).format({col: formatar_milhar_br for col in df_evol_pontos.columns if col != 'Evolução'}), use_container_width=True)
            else:
                st.dataframe(df_evol_pontos, use_container_width=True)

            st.markdown("###### Evolução Mensal (Quantidade de Pedidos)")
            if COLUNA_PEDIDO in df_consolidado.columns:
                df_evol_pedidos = calcular_evolucao_mensal(df_consolidado, COLUNA_PEDIDO)
                if 'Evolução' in df_evol_pedidos.columns:
                    st.dataframe(df_evol_pedidos.style.applymap(color_evol, subset=['Evolução']).format({col: formatar_milhar_br for col in df_evol_pedidos.columns if col != 'Evolução'}), use_container_width=True)
                else:
                    st.dataframe(df_evol_pedidos, use_container_width=True)
        else:
            st.info("Sem histórico anterior.")
    st.markdown("---")

    # =========================================================================
    # NOVO BLOCO: ANÁLISE DE SEGMENTO (VISUAL AJUSTADO - LEGENDA NA DIREITA)
    # =========================================================================
    st.subheader("🛍️ Análise por Segmento")
    
    temp_seg_sel = st.selectbox("Selecione a Temporada para Análise:", todas_temporadas, index=0, key='sel_seg_temp')
    df_season_seg = df_consolidado[df_consolidado['Temporada_Exibicao'] == temp_seg_sel]
    
    if not df_season_seg.empty:
        df_seg = calcular_analise_segmento(df_season_seg)
        
        # Ajuste de colunas para dar espaço à legenda na direita
        col_table, col_chart = st.columns([1.3, 2]) 
        
        with col_table:
            st.caption("Visão Geral dos Segmentos")
            st.dataframe(
                df_seg.style.format({
                    'Pontos': formatar_milhar_br,
                    COLUNA_PEDIDO: formatar_milhar_br
                }), 
                use_container_width=True,
                hide_index=True,
                height=450
            )
            
        with col_chart:
            # GRÁFICO DE PIZZA COM LEGENDA NA DIREITA E FONTE MAIOR
            fig = px.pie(
                df_seg, 
                values='Pontos', 
                names='Segmento', 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=120), # Margem direita maior para a legenda
                height=450, 
                showlegend=True,
                # LEGENDA NA DIREITA, VERTICAL, FONTE MAIOR
                legend=dict(
                    orientation="v", 
                    yanchor="middle", 
                    y=0.5, 
                    xanchor="left", 
                    x=1.02,
                    font=dict(size=14) # Aumento da fonte da legenda
                )
            )
            fig.update_traces(textposition='inside', textinfo='percent', textfont_size=14)
            st.plotly_chart(fig, use_container_width=True)

        # --- DRILL-DOWN DE LOJAS ---
        st.markdown("###### Detalhe de Lojas por Segmento")
        
        lista_segmentos = ["Selecione um Segmento..."] + sorted(df_seg['Segmento'].unique())
        segmento_sel = st.selectbox("Filtrar lojas de:", lista_segmentos)
        
        if segmento_sel != "Selecione um Segmento...":
            df_lojas = df_season_seg[df_season_seg['Segmento'] == segmento_sel].groupby('Loja').agg({
                'Pontos': 'sum',
                COLUNA_PEDIDO: 'nunique'
            }).reset_index().sort_values('Pontos', ascending=False)
            
            st.dataframe(
                df_lojas.style.format({
                    'Pontos': formatar_milhar_br,
                    COLUNA_PEDIDO: formatar_milhar_br
                }),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Nenhuma compra registrada nesta temporada para análise de segmento.")