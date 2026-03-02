# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4 - CSI)")
    
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
        # Cálculo exato do Tempo Investido (Horas)
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

    # Aplica o filtro de data (referência) para todos os gráficos abaixo
    mask_charts = (df_base[col_data_graficos].dt.date >= d_ini) & (df_base[col_data_graficos].dt.date <= d_fim)
    df_charts = df_base[mask_charts].copy()

    # --- ANÁLISE DE GARGALOS E OTIMIZAÇÃO (CUSTO/TEMPO) ---
    st.subheader("⏱️ Análise de Esforço Operacional (Tempo Investido)")
    if not df_charts.empty:
        tempo_total = df_charts["Tempo_Gasto_Real"].sum()
        mttr_medio = df_charts["Tempo_Gasto_Real"].mean()
        
        t1, t2, t3 = st.columns(3)
        t1.info(f"**Σ Custo Total de Tempo:** {tempo_total:.1f} Horas investidas.")
        t2.info(f"**μ MTTR Médio (Resolução):** {mttr_medio:.1f} Horas por chamado.")
        t3.success("💡 **Foco de Otimização:** Reduzir o MTTR em 10% economizará horas faturáveis da equipe.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            df_tempo_cli = df_charts.groupby("Cliente")["Tempo_Gasto_Real"].sum().reset_index().nlargest(10, "Tempo_Gasto_Real")
            fig_t1 = px.bar(df_tempo_cli, x='Cliente', y='Tempo_Gasto_Real', title="Esforço Horas vs. Cliente (Top 10 Consumidores)", text_auto='.1f')
            fig_t1.update_layout(yaxis_title="Σ Horas Gasto")
            st.plotly_chart(fig_t1, use_container_width=True)
        with col_t2:
            df_tempo_ana = df_charts.groupby("Responsável")["Tempo_Gasto_Real"].sum().reset_index()
            fig_t2 = px.pie(df_tempo_ana, values='Tempo_Gasto_Real', names='Responsável', title="Distribuição de Carga Horária por Analista", hole=0.3)
            st.plotly_chart(fig_t2, use_container_width=True)

    st.markdown("---")

    # --- ANÁLISE DE CAUSA-RAIZ (Estatística Descritiva / Pareto) ---
    st.subheader("🔍 Estocástica de Incidentes (Diagrama de Pareto)")
    l3_g1, l3_g2 = st.columns(2)

    def gerar_dados_pareto(df_p, coluna):
        df_freq = df_p[coluna].value_counts().reset_index()
        df_freq.columns = [coluna, 'Frequência Absoluta']
        return df_freq

    with l3_g1:
        st.markdown("**Matriz de Motivos de Abertura (Volumetria de Entrada)**")
        if "Motivo Abertura" in df_charts.columns and not df_charts["Motivo Abertura"].dropna().empty:
            df_abertura = gerar_dados_pareto(df_charts, "Motivo Abertura").head(10) 
            fig_abertura = px.bar(df_abertura, y='Motivo Abertura', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Blues')
            fig_abertura.update_layout(xaxis_title="Σ Volume", yaxis_title="Vetor de Motivo", margin=dict(t=10))
            st.plotly_chart(fig_abertura, use_container_width=True)

    with l3_g2:
        st.markdown("**Matriz de Resoluções (Motivos de Encerramento)**")
        if "Motivo Fechamento" in df_charts.columns and not df_charts["Motivo Fechamento"].dropna().empty:
            df_solucionados = df_charts[df_charts["Status"] == "Solucionado"]
            if not df_solucionados.empty:
                df_fechamento = gerar_dados_pareto(df_solucionados, "Motivo Fechamento").head(10)
                fig_fechamento = px.bar(df_fechamento, y='Motivo Fechamento', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Greens')
                fig_fechamento.update_layout(xaxis_title="Σ Volume", yaxis_title="Vetor de Fechamento", margin=dict(t=10))
                st.plotly_chart(fig_fechamento, use_container_width=True)

    st.markdown("---")

    # --- VISÃO GERAL (Macro) ---
    st.subheader("🌐 Visão Macroeconômica do Setor e Equipe")
    l1_g1, l1_g2 = st.columns(2)
    
    with l1_g1:
        # Gráfico de Tendência (Volume Dia a Dia)
        st.markdown("**Evolução Diária de Demandas**")
        if not df_charts.empty:
            df_trend = df_charts.groupby(df_charts[col_data_graficos].dt.date).size().reset_index(name="Quantidade")
            fig_trend = px.line(df_trend, x=col_data_graficos, y="Quantidade", markers=True)
            fig_trend.update_layout(xaxis_title="", yaxis_title="Volume", margin=dict(t=10))
            st.plotly_chart(fig_trend, use_container_width=True)

    with l1_g2:
        # Gráfico de Carga de Trabalho por Fase
        st.markdown("**Carga de Trabalho por Fase**")
        if not df_charts.empty:
            df_bar = df_charts.groupby(["Responsável", "Fase Nome"]).size().reset_index(name="Quantidade")
            fig_bar = px.bar(df_bar, x="Responsável", y="Quantidade", color="Fase Nome", barmode="group", text_auto='.0f')
            fig_bar.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Relatório Detalhado (Auditoria)"):
        if not df_charts.empty:
            df_detalhe = df_charts.copy()
            df_detalhe["Data Abertura"] = df_detalhe["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')
            
            df_detalhe["Histórico SLA"] = df_detalhe["Estourou_Real"].map({True: "🚨 Estourado", False: "✅ No Prazo"})
            df_detalhe["Tempo Investido (h)"] = df_detalhe["Tempo_Gasto_Real"].apply(lambda x: round(x, 2))
            
            # Reorganizando as colunas para a tabela ficar mais gerencial
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Histórico SLA", "Tempo Investido (h)", "Motivo Abertura", "Motivo Fechamento", "Data Abertura"]
            
            # Exibe as colunas dinamicamente verificando se existem na estrutura
            cols_view_present = [col for col in cols_view if col in df_detalhe.columns]
            
            st.dataframe(df_detalhe[cols_view_present], width="stretch", hide_index=True)
            
            csv = df_detalhe.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório Visível para CSV", csv, f"relatorio_auditoria_{d_ini}.csv", "text/csv")
