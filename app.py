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
            return 
            
    st.error("Acesso Negado. Credenciais inválidas.")

# --- 2. ISOLAMENTO ESTRUTURAL (IF/ELSE) ---
if not st.session_state.autenticado:
    st.markdown("<br><br><br><h2 style='text-align: center;'>🔐 Autenticação Corporativa</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1, 1.5])
    with c2:
        with st.container(border=True):
            st.text_input("Usuário", key="usuario_input")
            st.text_input("Senha", type="password", key="senha_input")
            st.button("Acessar Sistema", on_click=realizar_login, use_container_width=True)

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
            
        # ⚠️ ESTE É O BOTÃO QUE VOCÊ DEVE CLICAR APÓS SALVAR O CÓDIGO
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
            
            # --- 1. SOLUCIONADOS HOJE ---
            # Busca pelo campo Mestre do Bitrix, se não achar, usa Modificação.
            col_fechamento = "Data Encerramento" if "Data Encerramento" in df.columns else "Data Modificacao"
            mask_solucionados_hoje = (df["Status"] == "Solucionado") & (df[col_fechamento].dt.date == hoje)
            df_solucionados_hoje = df[mask_solucionados_hoje].copy()
            vol_solucionados_hoje = len(df_solucionados_hoje)

            # --- 2. REABERTOS (Lógica exata da Diretoria) ---
            # Regra A: Chamados com abertura anterior e que foram ENCERRADOS hoje.
            mask_reabertos_fechados = (df["Data Abertura"].dt.date < hoje) & mask_solucionados_hoje
            
            # Regra B: Chamados com abertura anterior, modificados de solucionado para aberto
            # Verificamos isso checando se o ticket NÃO é solucionado, mas possui "Motivo Fechamento"
            mask_reabertura_abertos = pd.Series(False, index=df.index)
            if "Motivo Fechamento" in df.columns:
                mask_reabertura_abertos = (
                    (df["Status"] != "Solucionado") & 
                    (df["Data Abertura"].dt.date < hoje) & 
                    (df["Data Modificacao"].dt.date == hoje) & 
                    (df["Motivo Fechamento"].notna()) & 
                    (df["Motivo Fechamento"].astype(str).str.strip() != "") & 
                    (df["Motivo Fechamento"].astype(str).str.strip() != "None")
                )
            
            mask_reabertos = mask_reabertos_fechados | mask_reabertura_abertos
            df_reabertos_hoje = df[mask_reabertos].copy()
            vol_reabertos_hoje = len(df_reabertos_hoje)

            # --- 3. CÁLCULO DE EFICIÊNCIA ---
            vol_entradas_hoje = len(df[df['Data Abertura'].dt.date == hoje])
            total_demanda_hoje = vol_entradas_hoje + vol_reabertos_hoje
            
            if total_demanda_hoje > 0:
                efi_diaria = (vol_solucionados_hoje / total_demanda_hoje) * 100
            else:
                efi_diaria = 100.0 if vol_solucionados_hoje > 0 else 0.0

            # --- RENDERIZAÇÃO ---
            c = st.columns(7)
            if c[0].button(f"📥 Entradas\n{vol_entradas_hoje}", key="k1", help="Tickets criados hoje."): st.session_state['filtro_atual'] = 'ENTRADAS'
            if c[1].button(f"📊 Pendentes\n{len(df_pendentes)}", key="k2", help="Total de chamados Ativos + Pausa."): st.session_state['filtro_atual'] = 'TOTAL_PENDENTE'
            if c[2].button(f"🔥 Fila Ativa\n{len(df_abertos)}", key="k3", help="Chamados aguardando ação da equipe."): st.session_state['filtro_atual'] = 'FILA_ATIVA'
            if c[3].button(f"🚨 SLA Crítico\n{len(df_abertos[df_abertos['Estourado']])}", key="k4", help="Chamados que ultrapassaram o tempo limite estipulado."): st.session_state['filtro_atual'] = 'SLA'
            if c[4].button(f"❄️ Em Pausa\n{len(df_pausa)}", key="k5", help="Aguardando retorno de terceiros."): st.session_state['filtro_atual'] = 'PAUSA'
            if c[5].button(f"✅ Solucionados\n{vol_solucionados_hoje}", key="k6", help="Finalizados hoje."): st.session_state['filtro_atual'] = 'SOLUCIONADOS'
            if c[6].button(f"♻️ Reabertos\n{vol_reabertos_hoje}", key="k7", help="Tickets reabertos ou solucionados do backlog hoje."): st.session_state['filtro_atual'] = 'REABERTOS'

            k = st.columns(3)
            with k[0]: styles.card_informativo("Eficiência Diária", f"{efi_diaria:.1f}%", "Solucionados vs (Entradas + Reabertos)")
            with k[1]: styles.card_informativo("Retrabalho Diário (Passivo)", f"{vol_reabertos_hoje}", "Tickets antigos movimentados hoje")
            with k[2]: styles.card_informativo("Analistas Online", df_abertos['Responsável'].nunique(), "Com chamados ativos")

            f = st.session_state['filtro_atual']
            
            # Matriz de colunas padrão
            cols_view = ["ID", "Fase Nome", "SLA Restante", "Cliente", "Título Completo", "Responsável", "Data Formatada", "Último Follow-up"]
            
            if f == 'TOTAL_PENDENTE': 
                df_view, tit = df_pendentes.sort_values(by="ID", key=lambda x: pd.to_numeric(x)).copy(), "Total Pendente"
            elif f == 'SLA': 
                df_view, tit = df_abertos[df_abertos["Estourado"]].copy(), "SLA Vencido"
            elif f == 'ENTRADAS': 
                df_view, tit = df[df["Data Abertura"].dt.date == hoje].copy(), "Entradas Criadas Hoje"
            elif f == 'SOLUCIONADOS': 
                df_view, tit = df_solucionados_hoje.copy(), "Solucionados Hoje"
                # Força a criação da coluna para exibição na tabela
                df_view["Encerramento"] = df_view[col_fechamento].dt.strftime('%d/%m %H:%M')
                cols_view = ["ID", "Fase Nome", "Cliente", "Título Completo", "Responsável", "Encerramento", "Último Follow-up"]
            elif f == 'FILA_ATIVA': 
                df_view, tit = df_abertos.copy(), "Fila Ativa de Trabalho"
            elif f == 'PAUSA': 
                df_view, tit = df_pausa.copy(), "Chamados em Pausa"
            elif f == 'REABERTOS': 
                df_view, tit = df_reabertos_hoje.copy(), "Auditoria: Chamados Reabertos/Movimentados Hoje"
                df_view["Abertura"] = df_view["Data Abertura"].dt.strftime('%d/%m %H:%M')
                df_view["Movimentação"] = df_view["Data Modificacao"].dt.strftime('%d/%m %H:%M')
                cols_view = ["ID", "Fase Nome", "Cliente", "Título Completo", "Responsável", "Abertura", "Movimentação", "Último Follow-up"]
            else: 
                df_view, tit = df_pendentes.copy(), "Fila Geral"

            st.subheader(f"📋 {tit} ({len(df_view)})")
            
            # Blindagem de Interface: Impede que a tela quebre caso alguma coluna não exista
            cols_present = [col for col in cols_view if col in df_view.columns]
            try:
                st.dataframe(df_view[cols_present].style.apply(styles.style_rows, axis=1), width="stretch", hide_index=True, height=520)
            except ValueError:
                st.dataframe(df_view[cols_present], width="stretch", hide_index=True, height=520)
        
        time.sleep(60)
        st.rerun()

    # --- MÓDULO DE GESTÃO ---
    elif aba == "📊 Gestão": 
        relatorios.renderizar_aba_gestao()
