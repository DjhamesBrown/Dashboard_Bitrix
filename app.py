# app.py
import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Importação dos módulos customizados
import data_engine
import styles
import relatorios

# 1. Configurações Iniciais da Página
st.set_page_config(
    page_title="Gestão Suporte ITIL", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Aplica o CSS para organizar o layout e garantir visibilidade do menu
styles.aplicar_css()

# 2. Navegação Lateral (Menu de Gestão)
with st.sidebar:
    st.title("📟 Menu")
    aba = st.radio("Módulo:", ["🚀 Operacional", "📊 Gestão"])
    st.markdown("---")
    if st.button("🔄 Sincronizar Agora"): 
        st.cache_data.clear()
        st.rerun()

# 3. Lógica do Módulo OPERACIONAL
if aba == "🚀 Operacional":
    # Estado inicial de filtragem: Foca no Total Pendente por padrão
    if 'filtro_atual' not in st.session_state: 
        st.session_state['filtro_atual'] = 'TOTAL_PENDENTE'
    
    # Busca dados atualizados do Bitrix24
    df = data_engine.buscar_dados()
    
    if not df.empty:
        hoje = datetime.now().date()
        
        # Preparação das bases de filtragem
        df_abertos = df[df["Status"] == "Em Aberto"].copy()
        df_pausa = df[df["Status"] == "Em Pausa"].copy()
        df_pendentes = pd.concat([df_abertos, df_pausa]).copy()
        
        # Cálculos de KPI de Performance (Cálculos ITIL)
        t_efi, t_reab = data_engine.calcular_kpis_extras(df)

        # --- LINHA 1: BOTÕES DE FILTRAGEM (KPIs Clicáveis) ---
        c = st.columns(6)
        
        # Entradas (Tickets criados hoje)
        if c[0].button(f"📥 Entradas\n{len(df[df['Data Abertura'].dt.date == hoje])}", 
                      key="k1", help="Total de chamados (abertos ou fechados) criados hoje."): 
            st.session_state['filtro_atual'] = 'ENTRADAS'
            
        # Total Pendente (Backlog Atual)
        if c[1].button(f"📊 Pendentes\n{len(df_pendentes)}", 
                      key="k2", help="Soma total de chamados Ativos e em Pausa."): 
            st.session_state['filtro_atual'] = 'TOTAL_PENDENTE'
            
        # Fila Ativa (Foco de Trabalho)
        if c[2].button(f"🔥 Fila Ativa\n{len(df_abertos)}", 
                      key="k3", help="Chamados abertos aguardando ação (exclui pausa)."): 
            st.session_state['filtro_atual'] = 'FILA_ATIVA'
            
        # SLA Crítico (Recuperado)
        if c[3].button(f"🚨 SLA Crítico\n{len(df_abertos[df_abertos['Estourado']])}", 
                      key="k4", help="Chamados ativos que ultrapassaram o tempo limite (SLA)."): 
            st.session_state['filtro_atual'] = 'SLA'
            
        # Em Pausa (Aguardando Terceiros)
        if c[4].button(f"❄️ Em Pausa\n{len(df_pausa)}", 
                      key="k5", help="Chamados estacionados aguardando retorno de terceiros ou cliente."): 
            st.session_state['filtro_atual'] = 'PAUSA'
            
        # Solucionados (Resultados do Dia)
        if c[5].button(f"✅ Solucionados\n{len(df[df['Fase_Cod'] == 'C8:WON'])}", 
                      key="k6", help="Total de chamados finalizados com sucesso hoje."): 
            st.session_state['filtro_atual'] = 'SOLUCIONADOS'

        # --- LINHA 2: CARDS DE PERFORMANCE (Informativos de Valor) ---
        k = st.columns(3)
        with k[0]: 
            styles.card_informativo("Eficiência Diária", f"{t_efi}%", "Resoluções vs Aberturas hoje", 
                                   help_text="Cálculo: (Solucionados Hoje / Entradas Hoje) * 100")
        with k[1]: 
            styles.card_informativo("Reabertos/Movimentados", f"{t_reab}%", "Tickets antigos mexidos hoje", 
                                   help_text="Cálculo: (Tickets antigos modificados hoje / Total Ativos) * 100")
        with k[2]: 
            styles.card_informativo("Analistas Online", df_abertos['Responsável'].nunique(), "Com chamados ativos", 
                                   help_text="Quantidade de analistas únicos com pelo menos um ticket na Fila Ativa.")

        # --- LÓGICA DE FILTRAGEM DO GRID ---
        f = st.session_state['filtro_atual']
        
        if f == 'TOTAL_PENDENTE':
            df_view = df_pendentes.copy()
            df_view["ID_Int"] = pd.to_numeric(df_view["ID"])
            df_view = df_view.sort_values(by="ID_Int", ascending=True)
            tit = "Total Pendente (ID Crescente)"
            
        elif f == 'SLA':
            df_view = df_abertos[df_abertos["Estourado"]].copy()
            tit = "SLA Vencido"
            
        elif f == 'ENTRADAS':
            # Filtra apenas o que foi criado na data de hoje
            df_view = df[df["Data Abertura"].dt.date == hoje].copy()
            tit = "Entradas Criadas Hoje"
            
        elif f == 'SOLUCIONADOS':
            # Filtra o que está na fase WON (Finalizado)
            df_view = df[df["Fase_Cod"] == "C8:WON"].copy()
            tit = "Solucionados Hoje"
            
        elif f == 'FILA_ATIVA':
            df_view = df_abertos.copy()
            tit = "Fila Ativa de Trabalho"
            
        elif f == 'PAUSA':
            df_view = df_pausa.copy()
            tit = "Chamados em Pausa"
            
        else:
            df_view = df_pendentes.copy()
            tit = "Fila Geral"

        # Exibição do Título e Grid de Dados
        st.subheader(f"📋 {tit} ({len(df_view)})")
        
        # Renderização da Tabela com Cores Condicionais (styles.style_rows)
        st.dataframe(
            df_view[["ID", "Fase Nome", "SLA Restante", "Cliente", "Título Completo", "Responsável", "Data Formatada", "Último Follow-up"]].style.apply(styles.style_rows, axis=1), 
            width="stretch", 
            hide_index=True, 
            height=520
        )
    
    # Ciclo de atualização automática (60 segundos)
    time.sleep(60)
    st.rerun()

# 4. Lógica do Módulo GESTÃO E RELATÓRIOS
else: 
    relatorios.renderizar_aba_gestao()