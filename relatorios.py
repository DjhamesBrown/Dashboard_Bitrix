# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4 - CSI)")
    
    # --- FUNÇÕES DE INTERATIVIDADE E DRILL-DOWN ---
    def exibir_drilldown(selecao, df_base, coluna_filtro, is_pie=False, is_horizontal=False):
        """Função matemática para extrair o vetor selecionado no gráfico e renderizar a sub-tabela."""
        if selecao and isinstance(selecao, dict) and "selection" in selecao:
            pontos = selecao["selection"].get("points", [])
            if pontos:
                valores = []
                for p in pontos:
                    if is_pie: valores.append(p.get("label", p.get("x")))
                    elif is_horizontal: valores.append(p.get("y"))
                    else: valores.append(p.get("x"))
                
                valores = [v for v in valores if v is not None]
                
                if valores:
                    df_filtrado = df_base[df_base[coluna_filtro].isin(valores)]
                    st.success(f"🔎 **Detalhamento:** {len(df_filtrado)} chamado(s) encontrado(s) para a seleção: {', '.join(map(str, set(valores)))}")
                    
                    cols_exibir = ["ID", "Responsável", "Cliente", "Fase Nome", "Tempo Investido (h)", "Histórico SLA"]
                    cols_presentes = [c for c in cols_exibir if c in df_filtrado.columns]
                    
                    st.dataframe(df_filtrado[cols_presentes], use_container_width=True, hide_index=True)

    def plot_interativo(fig, df_charts, coluna_filtro, key, is_pie=False, is_horizontal=False):
        """Envelopamento com tratamento de exceção para garantir suporte a versões do Streamlit."""
        try:
            # Tenta utilizar o parâmetro on_select do Streamlit 1.35+
            selecao = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key)
            exibir_drilldown(selecao, df_charts, coluna_filtro, is_pie, is_horizontal)
        except TypeError:
            # Fallback seguro caso o servidor esteja com pacote desatualizado
            st.plotly_chart(fig, use_container_width=True, key=key)
            st.caption("💡 Para habilitar o clique e detalhamento, atualize o pacote via terminal: `pip install -U streamlit`")

    # --- 1. BARRA LATERAL ESTÁTICA ---
    st.sidebar.subheader("🎯 Filtros Estocásticos")
    
    d_ini = st.sidebar.date_input("Data Início", value=date.today() - pd.Timedelta(days=15), format="DD/MM/YYYY")
    d_fim = st.sidebar.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
    dias_periodo = max((d_fim - d_ini).days + 1, 1)

    tipo_data_grafico = st.sidebar.radio("Referência para os Gráficos:", ["Data de Abertura", "Data de Encerramento"])
    col_data_graficos = "Data Abertura" if tipo_data_grafico == "Data de Abertura" else "Data Modificacao"
    
    equipe_suporte = ["Ana Beatriz", "Djhames Moraes", "Luciana Scabini", "Thaísa Castilho"]
    analistas_sel = st.sidebar.multiselect("Filtrar Analistas", options=equipe_suporte, default=equipe_suporte)

    # --- 2. CHAMADA AO MOTOR DE DADOS ---
    with st.spinner(f"Extraindo matriz de dados de {d_ini.strftime('%d/%m')} a {d_fim.strftime('%d/%m')}..."):
        df = data_engine_rel.buscar_dados_historico(d_ini, d_fim)
        
    if df.empty:
        st.warning(f"Variância Zero. Nenhum dado encontrado no Bitrix24 entre {d_ini.strftime('%d/%m/%Y')} e {d_fim.strftime('%d/%m/%Y')}.")
        return

    clientes_sel = st.sidebar.multiselect("Filtrar Clientes", options=sorted(df["Cliente"].unique()))

    # --- 3. PROCESSAMENTO DE TOTALIZADORES ---
    mask_base = df["Responsável"].isin(analistas_sel)
    if clientes_sel: mask_base &= df["Cliente"].isin(clientes_sel)
    df_base = df[mask_base].copy()

    if not df_base.empty:
        agora = pd.Timestamp(datetime.now())
        df_base["Tempo_Gasto_Real"] = df_base.apply(
            lambda row: (row["Data Modificacao"] if row["Status"] == "Solucionado" else agora) - row["Data Abertura"], axis=1
        ).dt.total_seconds() / 3600
        df_base["Meta_Real"] = df_base.apply(lambda row: 24 if row["SLA_Meta"] == 9999 else row["SLA_Meta"], axis=1)
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

    st.subheader(f"📈 Indicadores do Período ({d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')})",
                 help="Fornece o panorama quantitativo do setor de suporte. Todas as métricas reagem aos filtros da barra lateral.")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Volume Abertos", vol_periodo, help="Total absoluto de chamados criados no período.")
    with c2: st.metric("Solucionados", sol_periodo, delta=f"{taxa_eficiencia:.1f}% Eficiência", delta_color="normal", help="Total de finalizados. A % mede Entradas vs Saídas.")
    with c3: st.metric("✅ SLA Cumprido", sla_cumprido, delta=f"{taxa_sla_cumprido:.1f}% sucesso", delta_color="normal", help="Probabilidade de entrega dentro do tempo estipulado em contrato.")
    with c4: st.metric("🚨 SLA Crítico", sla_critico, delta=f"{taxa_sla_critico:.1f}% estouraram", delta_color="inverse", help="Volume de desvios operacionais. Foco primário para atuação de gestão.")
    with c5: st.metric("⚡ FCR (1º Contato)", fcr_count, delta=f"{taxa_fcr:.1f}% ágeis", delta_color="normal", help="First Call Resolution. Chamados solucionados em menos de 1 hora de esforço.")
    with c6: st.metric("Vazão (Entregas/Dia)", f"{vazao_dia:.1f}", delta=f"{sol_periodo} total", delta_color="off", help="Média geométrica diária de entregas da equipe.")

    st.markdown("---")

    # PREPARAÇÃO MATEMÁTICA PARA OS DRILL-DOWNS
    mask_charts = (df_base[col_data_graficos].dt.date >= d_ini) & (df_base[col_data_graficos].dt.date <= d_fim)
    df_charts = df_base[mask_charts].copy()
    if not df_charts.empty:
        df_charts['Status_SLA'] = df_charts['Estourou_Real'].map({True: 'Estourado 🚨', False: 'No Prazo ✅'})
        df_charts["Histórico SLA"] = df_charts["Status_SLA"]
        df_charts["Tempo Investido (h)"] = df_charts["Tempo_Gasto_Real"].apply(lambda x: round(x, 2))
        df_charts["Data Formatada"] = df_charts["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')

    # --- ANÁLISE DE CUSTO/TEMPO ---
    st.subheader("⏱️ Análise de Esforço Operacional (Tempo Investido)", 
                 help="Mede o MTTR (Tempo Médio de Resolução) e as horas faturáveis consumidas. Permite identificar gargalos, justificar a necessidade de treinamentos, renegociar contratos com clientes ofensores e identificar áreas para redução de custos.")
    if not df_charts.empty:
        tempo_total = df_charts["Tempo_Gasto_Real"].sum()
        mttr_medio = df_charts["Tempo_Gasto_Real"].mean()
        
        t1, t2, t3 = st.columns(3)
        t1.info(f"**Σ Custo Total de Tempo:** {tempo_total:.1f} Horas investidas.")
        t2.info(f"**μ MTTR Médio (Resolução):** {mttr_medio:.1f} Horas por chamado.")
        t3.success("💡 **Foco de Otimização:** Reduzir o MTTR atuando nas causas mais frequentes economizará custo operacional.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            df_tempo_cli = df_charts.groupby("Cliente")["Tempo_Gasto_Real"].sum().reset_index().nlargest(10, "Tempo_Gasto_Real")
            fig_t1 = px.bar(df_tempo_cli, x='Cliente', y='Tempo_Gasto_Real', title="Esforço vs. Cliente (Top 10)", text_auto='.1f')
            fig_t1.update_layout(yaxis_title="Σ Horas Gasto")
            plot_interativo(fig_t1, df_charts, "Cliente", "graf_esforco_cli", is_horizontal=False)
            
        with col_t2:
            df_tempo_ana = df_charts.groupby("Responsável")["Tempo_Gasto_Real"].sum().reset_index()
            fig_t2 = px.pie(df_tempo_ana, values='Tempo_Gasto_Real', names='Responsável', title="Distribuição de Carga Horária", hole=0.3)
            plot_interativo(fig_t2, df_charts, "Responsável", "graf_esforco_ana", is_pie=True)

    st.markdown("---")

    # --- ANÁLISE DE CAUSA-RAIZ (Pareto) ---
    st.subheader("🔍 Estocástica de Incidentes (Diagrama de Pareto)", 
                 help="Aplica o Princípio de Pareto (Regra 80/20). Mostra as categorias estruturais dos chamados. A teoria indica que atuar nos maiores ofensores (barras no topo) reduzirá drasticamente o volume futuro de incidentes.")
    l3_g1, l3_g2 = st.columns(2)

    def gerar_dados_pareto(df_p, coluna):
        df_freq = df_p[coluna].value_counts().reset_index()
        df_freq.columns = [coluna, 'Frequência Absoluta']
        return df_freq

    with l3_g1:
        st.markdown("**Matriz de Motivos de Abertura (Entrada)**")
        if "Motivo Abertura" in df_charts.columns and not df_charts["Motivo Abertura"].dropna().empty:
            df_abertura = gerar_dados_pareto(df_charts, "Motivo Abertura").head(10) 
            fig_abertura = px.bar(df_abertura, y='Motivo Abertura', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Blues')
            fig_abertura.update_layout(xaxis_title="Σ Volume", yaxis_title="")
            plot_interativo(fig_abertura, df_charts, "Motivo Abertura", "graf_motivo_abertura", is_horizontal=True)

    with l3_g2:
        st.markdown("**Matriz de Resoluções (Fechamento)**")
        if "Motivo Fechamento" in df_charts.columns and not df_charts["Motivo Fechamento"].dropna().empty:
            df_solucionados = df_charts[df_charts["Status"] == "Solucionado"]
            if not df_solucionados.empty:
                df_fechamento = gerar_dados_pareto(df_solucionados, "Motivo Fechamento").head(10)
                fig_fechamento = px.bar(df_fechamento, y='Motivo Fechamento', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Greens')
                fig_fechamento.update_layout(xaxis_title="Σ Volume", yaxis_title="")
                plot_interativo(fig_fechamento, df_charts, "Motivo Fechamento", "graf_motivo_fechamento", is_horizontal=True)

    st.markdown("---")

    # --- VISÃO MACRO E QUALIDADE SLA ---
    st.subheader("🌐 Visão Macroeconômica e Produtividade", 
                 help="Monitora as tendências de alta ou baixa demanda dia a dia, e avalia a qualidade da entrega (SLA Cumprido vs Estourado) individualmente por analista da equipe.")
    l1_g1, l1_g2 = st.columns(2)
    
    with l1_g1:
        st.markdown("**Evolução Diária de Demandas**")
        if not df_charts.empty:
            df_trend = df_charts.groupby(df_charts[col_data_graficos].dt.date).size().reset_index(name="Quantidade")
            fig_trend = px.line(df_trend, x=col_data_graficos, y="Quantidade", markers=True)
            fig_trend.update_layout(xaxis_title="", yaxis_title="Volume", margin=dict(t=10))
            # Gráfico de linha puro, visualização de tendência (sem necessidade de drill-down vertical)
            st.plotly_chart(fig_trend, use_container_width=True)

    with l1_g2:
        st.markdown("**Qualidade de Entrega (SLA por Analista)**")
        if not df_charts.empty:
            df_sla_ana = df_charts.groupby(['Responsável', 'Status_SLA']).size().reset_index(name='Total')
            cores_sla = {'No Prazo ✅': '#2e7d32', 'Estourado 🚨': '#c62828'}
            fig_sla = px.bar(df_sla_ana, x='Responsável', y='Total', color='Status_SLA', barmode='stack', text_auto='.0f', color_discrete_map=cores_sla)
            fig_sla.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            plot_interativo(fig_sla, df_charts, "Responsável", "graf_sla_qualidade", is_horizontal=False)

    # --- RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Relatório Detalhado (Matriz Bruta)"):
        if not df_charts.empty:
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Histórico SLA", "Tempo Investido (h)", "Motivo Abertura", "Motivo Fechamento", "Data Formatada"]
            cols_view_present = [col for col in cols_view if col in df_charts.columns]
            
            st.dataframe(df_charts[cols_view_present], width="stretch", hide_index=True)
            
            csv = df_charts.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório Visível para CSV", csv, f"relatorio_auditoria_{d_ini}.csv", "text/csv")
