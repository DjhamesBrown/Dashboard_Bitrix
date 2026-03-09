# app.py
import streamlit as st
import pandas as pd
import time
from datetime import datetime

import data_engine
import styles
import relatorios
import config

st.set_page_config(page_title="Gestão Suporte ITIL", layout="wide", initial_sidebar_state="expanded")

# --- 1. GESTÃO DE ESTADO (MEMÓRIA) ---
if 'tema' not in st.session_state: st.session_state.tema = 'dark'
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'role' not in st.session_state: st.session_state.role = None

styles.aplicar_css(st.session_state.tema)

def realizar_login():
    usr = st.session_state.usuario_input
    pwd = st.session_state.senha_input
    
    for nivel, cred in config.CREDENCIAIS.items():
        if usr == cred["user"] and pwd == cred["pass"]:
            st.session_state.autenticado = True
            st.session_state.role = cred["role"]
            return # Apenas retorna, o Streamlit recarrega automaticamente
            
    st.error("Acesso Negado. Credenciais inválidas.")

# --- 2. ISOLAMENTO ESTRUTURAL (IF/ELSE) ---
# Se P(Autenticado) = 0, renderiza APENAS o login.
if not st.session_state.autenticado:
    st.markdown("<br><br><br><h2 style='text-align: center;'>🔐 Autenticação Corporativa</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1, 1.5])
    with c2:
        with st.container(border=True):
            st.text_input("Usuário", key="usuario_input")
            st.text_input("Senha", type="password", key="senha_input")
            st.button("Acessar Sistema", on_click=realizar_login, use_container_width=True)

# Se P(Autenticado) = 1, renderiza APENAS o Dashboard.
else:
    with st.sidebar:
        st.title("📟 Menu")
        
        opcoes_menu = ["🚀 Operacional"]
        if st.session_state.role == "gestor":
            opcoes_menu.append("📊 Gestão")
            
        aba = st.radio("Módulo:", opcoes_menu)
        st.markdown("---")
        
        if st.button("🌓 Alternar Tema (UI)"):
            st.session_state.tema = 'light' if st.session_state.tema == 'dark' else 'dark'
            st.rerun()
            
        if st.button("🔄 Sincronizar Agora"): 
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        st.info(f"👤 Logado como: **{st.session_state.role.upper()}**")
        
        if st.button("🚪 Sair (Logoff)", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.role = None
            st.rerun()

    # --- MÓDULO OPERACIONAL ---
    if aba == "🚀 Operacional":
        if 'filtro_atual' not in st.session_state: st.session_state['filtro_atual'] = 'TOTAL_PENDENTE'
        
        df = data_engine.buscar_dados()
        
        if not df.empty:
            hoje = datetime.now().date()
            df_abertos = df[df["Status"] == "Em Aberto"].copy()
            df_pausa = df[df["Status"] == "Em Pausa"].copy()
            df_pendentes = pd.concat([df_abertos, df_pausa]).copy()
            
            # ⚠️ CORREÇÃO 1: SOLUCIONADOS HOJE
            # O bug: antes pegava TODOS os solucionados da memória do Bitrix.
            # A correção: agora exige estritamente que a Data de Modificação seja HOJE.
            mask_solucionados_hoje = (df["Fase_Cod"] == "C8:WON") & (df["Data Modificacao"].dt.date == hoje)
            df_solucionados_hoje = df[mask_solucionados_hoje].copy()

            # ⚠️ CORREÇÃO 2: REABERTOS / RETRABALHO
            # Puxa chamados antigos que receberam alteração (comentários, mudança de fase ou fechamento) HOJE
            mask_reabertos = (df["Data Abertura"].dt.date < hoje) & (df["Data Modificacao"].dt.date == hoje)
            df_reabertos_hoje = df[mask_reabertos].copy()
            vol_reabertos_hoje = len(df_reabertos_hoje)

            t_efi, _ = data_engine.calcular_kpis_extras(df) 

            c = st.columns(7)
            if c[0].button(f"📥 Entradas\n{len(df[df['Data Abertura'].dt.date == hoje])}", key="k1", help="Tickets criados hoje."): st.session_state['filtro_atual'] = 'ENTRADAS'
            if c[1].button(f"📊 Pendentes\n{len(df_pendentes)}", key="k2", help="Total de chamados Ativos + Pausa."): st.session_state['filtro_atual'] = 'TOTAL_PENDENTE'
            if c[2].button(f"🔥 Fila Ativa\n{len(df_abertos)}", key="k3", help="Chamados aguardando ação da equipe."): st.session_state['filtro_atual'] = 'FILA_ATIVA'
            if c[3].button(f"🚨 SLA Crítico\n{len(df_abertos[df_abertos['Estourado']])}", key="k4", help="Chamados que ultrapassaram o tempo limite estipulado."): st.session_state['filtro_atual'] = 'SLA'
            if c[4].button(f"❄️ Em Pausa\n{len(df_pausa)}", key="k5", help="Aguardando retorno de terceiros."): st.session_state['filtro_atual'] = 'PAUSA'
            
            # Aplicando o Dataframe com o filtro de data correto no botão
            if c[5].button(f"✅ Solucionados\n{len(df_solucionados_hoje)}", key="k6", help="Finalizados hoje."): st.session_state['filtro_atual'] = 'SOLUCIONADOS'
            
            if c[6].button(f"♻️ Reabertos\n{vol_reabertos_hoje}", key="k7", help="Tickets antigos movimentados hoje."): st.session_state['filtro_atual'] = 'REABERTOS'

            k = st.columns(3)
            with k[0]: styles.card_informativo("Eficiência Diária", f"{t_efi}%", "Resoluções vs Aberturas hoje")
            with k[1]: styles.card_informativo("Retrabalho Diário (Passivo)", f"{vol_reabertos_hoje}", "Tickets antigos movimentados hoje")
            with k[2]: styles.card_informativo("Analistas Online", df_abertos['Responsável'].nunique(), "Com chamados ativos")

            f = st.session_state['filtro_atual']
            if f == 'TOTAL_PENDENTE': df_view, tit = df_pendentes.sort_values(by="ID", key=lambda x: pd.to_numeric(x)).copy(), "Total Pendente"
            elif f == 'SLA': df_view, tit = df_abertos[df_abertos["Estourado"]].copy(), "SLA Vencido"
            elif f == 'ENTRADAS': df_view, tit = df[df["Data Abertura"].dt.date == hoje].copy(), "Entradas Criadas Hoje"
            
            # Aplicando a variável com o filtro de data correto na renderização da tabela
            elif f == 'SOLUCIONADOS': df_view, tit = df_solucionados_hoje.copy(), "Solucionados Hoje"
            
            elif f == 'FILA_ATIVA': df_view, tit = df_abertos.copy(), "Fila Ativa de Trabalho"
            elif f == 'PAUSA': df_view, tit = df_pausa.copy(), "Chamados em Pausa"
            elif f == 'REABERTOS': df_view, tit = df_reabertos_hoje.copy(), "Auditoria: Chamados Reabertos/Movimentados Hoje"
            else: df_view, tit = df_pendentes.copy(), "Fila Geral"

            st.subheader(f"📋 {tit} ({len(df_view)})")
            st.dataframe(df_view[["ID", "Fase Nome", "SLA Restante", "Cliente", "Título Completo", "Responsável", "Data Formatada", "Último Follow-up"]].style.apply(styles.style_rows, axis=1), width="stretch", hide_index=True, height=520)
        
        time.sleep(60)
        st.rerun()

    # --- MÓDULO DE GESTÃO ---
    elif aba == "📊 Gestão": 
        relatorios.renderizar_aba_gestao()
