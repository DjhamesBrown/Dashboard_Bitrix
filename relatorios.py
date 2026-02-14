# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4)")
    
    # --- 1. BARRA LATERAL ESTÁTICA ---
    st.sidebar.subheader("🎯 Filtros de Valor")
    
    d_ini = st.sidebar.date_input("Data Início", value=date.today() - pd.Timedelta(days=15), format="DD/MM/YYYY")
    d_fim = st.sidebar.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
    dias_periodo = max((d_fim - d_ini).days + 1, 1)

    tipo_data_grafico = st.sidebar.radio(
        "Referência para os Gráficos:",
        ["Data de Abertura", "Data de Encerramento"]
    )
    col_data_graficos = "Data Abertura" if tipo_data_grafico == "Data de Abertura" else "Data Modificacao"
    
    equipe_suporte = ["Ana Beatriz", "Djhames Moraes", "Luciana Scabini", "Thaísa Castilho"]
    analistas_sel = st.sidebar.multiselect("Filtrar Analistas", options=equipe_suporte, default=equipe_suporte)

    # --- 2. CHAMADA AO MOTOR DE DADOS ---
    with st.spinner(f"Sincronizando dados de {d_ini.strftime('%d/%m')} a {d_fim.strftime('%d/%m')}..."):
        df = data_engine_rel.buscar_dados_historico(d_ini, d_fim)
        
    if df.empty:
        st.warning(f"Nenhum dado encontrado no Bitrix24 entre {d_ini.strftime('%d/%m/%Y')} e {d_fim.strftime('%d/%m/%Y')}.")
        return

    clientes_sel = st.sidebar.multiselect("Filtrar Clientes", options=sorted(df["Cliente"].unique()))

    # --- 3. PROCESSAMENTO DE TOTALIZADORES E SLA HISTÓRICO ---
    mask_base = df["Responsável"].isin(analistas_sel)
    if clientes_sel: mask_base &= df["Cliente"].isin(clientes_sel)
    df_base = df[mask_base].copy()

    if not df_base.empty:
        agora = pd.Timestamp(datetime.now())
        df_base["Tempo_Gasto_Real"] = df_base.apply(
            lambda row: (row["Data Modificacao"] if row["Status"] == "Solucionado" else agora) - row["Data Abertura"], 
            axis=1
        ).dt.total_seconds() / 3600
        
        SLA_PADRAO_FECHADOS = 24 
        df_base["Meta_Real"] = df_base.apply(
            lambda row: SLA_PADRAO_FECHADOS if row["SLA_Meta"] == 9999 else row["SLA_Meta"],
            axis=1
        )
        df_base["Estourou_Real"] = df_base["Tempo_Gasto_Real"] > df_base["Meta_Real"]
    else:
        df_base["Estourou_Real"] = False
        df_base["Tempo_Gasto_Real"] = 0

    mask_abertos = (df_base["Data Abertura"].dt.date >= d_ini) & (df_base["Data Abertura"].dt.date <= d_fim)
    vol_periodo = len(df_base[mask_abertos])

    mask_fechados = (df_base["Data Modificacao"].dt.date >= d_ini) & (df_base["Data Modificacao"].dt.date <= d_fim) & (df_base["Status"] == "Solucionado")
    sol_periodo = len(df_base[mask_fechados])

    mask_referencia = mask_abertos if tipo_data_grafico == "Data de Abertura" else mask_fechados
    total_referencia = len(df_base[mask_referencia])

    sla_critico = len(df_base[mask_referencia & df_base["Estourou_Real"]])
    sla_cumprido = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourou_Real"])])
    fcr_count = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourou_Real"]) & (df_base["Tempo_Gasto_Real"] <= 1.0)])

    taxa_eficiencia = (sol_periodo / vol_periodo * 100) if vol_periodo > 0 else 0
    taxa_sla_critico = (sla_critico / total_referencia * 100) if total_referencia > 0 else 0
    taxa_sla_cumprido = (sla_cumprido / sol_periodo * 100) if sol_periodo > 0 else 0
    taxa_fcr = (fcr_count / sol_periodo * 100) if sol_periodo > 0 else 0
    vazao_dia = sol_periodo / dias_periodo

    # --- TOTALIZADORES (MANTIDOS) ---
    st.subheader(f"📈 Indicadores do Período ({d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')})")
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Volume Abertos", vol_periodo, help="Total absoluto de chamados ABERTOS no período filtrado.")
    with c2: st.metric("Solucionados", sol_periodo, delta=f"{taxa_eficiencia:.1f}% Eficiência", delta_color="normal")
    with c3: st.metric("✅ SLA Cumprido", sla_cumprido, delta=f"{taxa_sla_cumprido:.1f}% sucesso", delta_color="normal")
    with c4: st.metric("🚨 SLA Crítico", sla_critico, delta=f"{taxa_sla_critico:.1f}% estouraram", delta_color="inverse")
    with c5: st.metric("⚡ FCR (1º Contato)", fcr_count, delta=f"{taxa_fcr:.1f}% ágeis", delta_color="normal")
    with c6: st.metric("Vazão (Entregas/Dia)", f"{vazao_dia:.1f}", delta=f"{sol_periodo} total", delta_color="off")

    st.markdown("---")

    # --- 4. ANÁLISE VISUAL AVANÇADA ---
    # Aplica o filtro de data (referência) para todos os gráficos abaixo
    mask_charts = (df_base[col_data_graficos].dt.date >= d_ini) & (df_base[col_data_graficos].dt.date <= d_fim)
    df_charts = df_base[mask_charts].copy()

    # LINHA 1: VISÃO GERAL (Macro)
    st.subheader("🌐 Visão Macroeconômica do Setor")
    l1_g1, l1_g2 = st.columns(2)
    
    with l1_g1:
        # NOVO: Gráfico de Tendência (Volume Dia a Dia)
        st.markdown("**Evolução Diária de Demandas**")
        if not df_charts.empty:
            df_trend = df_charts.groupby(df_charts[col_data_graficos].dt.date).size().reset_index(name="Quantidade")
            fig_trend = px.line(df_trend, x=col_data_graficos, y="Quantidade", markers=True)
            fig_trend.update_layout(xaxis_title="", yaxis_title="Volume", margin=dict(t=10))
            st.plotly_chart(fig_trend, use_container_width=True)

    with l1_g2:
        # Gráfico Circular de Clientes
        st.markdown("**Concentração por Cliente (Top 10)**")
        if not df_charts.empty:
            df_pie = df_charts.groupby("Cliente").size().reset_index(name="Quantidade").nlargest(10, "Quantidade")
            fig_pie = px.pie(df_pie, values="Quantidade", names="Cliente", hole=0.4)
            fig_pie.update_traces(textinfo='percent+value')
            fig_pie.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # LINHA 2: VISÃO DE EQUIPE (Micro)
    st.subheader("👥 Performance e Carga da Equipe")
    l2_g1, l2_g2 = st.columns(2)

    with l2_g1:
        # Gráfico de Carga de Trabalho por Fase
        st.markdown("**Carga de Trabalho por Fase**")
        if not df_charts.empty:
            df_bar = df_charts.groupby(["Responsável", "Fase Nome"]).size().reset_index(name="Quantidade")
            fig_bar = px.bar(df_bar, x="Responsável", y="Quantidade", color="Fase Nome", barmode="group", text_auto='.0f')
            fig_bar.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            st.plotly_chart(fig_bar, use_container_width=True)

    with l2_g2:
        # NOVO: Gráfico de Eficiência de SLA por Analista
        st.markdown("**Qualidade de Entrega (SLA por Analista)**")
        if not df_charts.empty:
            df_charts['Status_SLA'] = df_charts['Estourou_Real'].map({True: 'Estourado 🚨', False: 'No Prazo ✅'})
            df_sla_ana = df_charts.groupby(['Responsável', 'Status_SLA']).size().reset_index(name='Total')
            
            # Cores intuitivas: Verde para No Prazo, Vermelho para Estourado
            cores_sla = {'No Prazo ✅': '#2e7d32', 'Estourado 🚨': '#c62828'}
            
            fig_sla = px.bar(df_sla_ana, x='Responsável', y='Total', color='Status_SLA', 
                             barmode='stack', text_auto='.0f', color_discrete_map=cores_sla)
            fig_sla.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            st.plotly_chart(fig_sla, use_container_width=True)

    # --- 5. RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Relatório Detalhado (Auditoria)"):
        if not df_charts.empty:
            df_detalhe = df_charts.copy()
            df_detalhe["Data Abertura"] = df_detalhe["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')
            
            df_detalhe["Histórico SLA"] = df_detalhe["Estourou_Real"].map({True: "🚨 Estourado", False: "✅ No Prazo"})
            
            # Reorganizando as colunas para a tabela ficar mais gerencial
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Histórico SLA", "Data Abertura"]
            st.dataframe(df_detalhe[cols_view], width="stretch", hide_index=True)
            
            csv = df_detalhe.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório Visível para CSV", csv, f"relatorio_auditoria_{d_ini}.csv", "text/csv")