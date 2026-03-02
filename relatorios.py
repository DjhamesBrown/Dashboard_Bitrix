# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4 - CSI)", 
              help="[Princípio ITIL: Continual Service Improvement] Este módulo transforma os dados transacionais do Bitrix24 em inteligência estratégica para tomada de decisão.")
    
    # --- FUNÇÃO DE DRILL-DOWN ---
    def exibir_drilldown(selecao, df_base, coluna_filtro, is_pie=False, is_horizontal=False):
        if selecao and isinstance(selecao, dict) and "selection" in selecao:
            pontos = selecao["selection"].get("points", [])
            if pontos:
                valores = [p.get("label", p.get("x")) if is_pie else (p.get("y") if is_horizontal else p.get("x")) for p in pontos]
                valores = [v for v in valores if v is not None]
                if valores:
                    df_filtrado = df_base[df_base[coluna_filtro].isin(valores)]
                    st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtrado)} chamado(s) para a seleção '{', '.join(map(str, set(valores)))}'.")
                    cols = ["ID", "Responsável", "Cliente", "Fase Nome", "Motivo Abertura", "Esforco_Tarefas_h"]
                    st.dataframe(df_filtrado[[c for c in cols if c in df_filtrado.columns]], use_container_width=True, hide_index=True)

    def plot_interativo(fig, df_charts, coluna_filtro, key, is_pie=False, is_horizontal=False):
        try:
            selecao = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key)
            exibir_drilldown(selecao, df_charts, coluna_filtro, is_pie, is_horizontal)
        except TypeError:
            st.plotly_chart(fig, use_container_width=True, key=key)

    # --- BARRA LATERAL ESTÁTICA ---
    st.sidebar.subheader("🎯 Filtros Estocásticos")
    d_ini = st.sidebar.date_input("Data Início", value=date.today() - pd.Timedelta(days=15), format="DD/MM/YYYY")
    d_fim = st.sidebar.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
    dias_periodo = max((d_fim - d_ini).days + 1, 1)

    tipo_data_grafico = st.sidebar.radio("Referência de Busca:", ["Data de Abertura", "Data de Encerramento"], 
                                         help="Define se os gráficos abaixo devem filtrar os chamados que foram CRIADOS neste período ou FINALIZADOS neste período.")
    col_data_graficos = "Data Abertura" if tipo_data_grafico == "Data de Abertura" else "Data Modificacao"
    
    equipe_suporte = ["Ana Beatriz", "Djhames Moraes", "Luciana Scabini", "Thaísa Castilho"]
    analistas_sel = st.sidebar.multiselect("Filtrar Analistas", options=equipe_suporte, default=equipe_suporte)

    with st.spinner(f"Extraindo matriz de dados e cruzando com tarefas..."):
        df = data_engine_rel.buscar_dados_historico(d_ini, d_fim)
        
    if df.empty:
        st.warning("Variância Zero. Nenhum dado encontrado na base neste período.")
        return

    clientes_sel = st.sidebar.multiselect("Filtrar Clientes", options=sorted(df["Cliente"].unique()))

    mask_base = df["Responsável"].isin(analistas_sel)
    if clientes_sel: mask_base &= df["Cliente"].isin(clientes_sel)
    df_base = df[mask_base].copy()

    # Processamento de KPI
    mask_abertos = (df_base["Data Abertura"].dt.date >= d_ini) & (df_base["Data Abertura"].dt.date <= d_fim)
    vol_periodo = len(df_base[mask_abertos])

    mask_fechados = (df_base["Data Modificacao"].dt.date >= d_ini) & (df_base["Data Modificacao"].dt.date <= d_fim) & (df_base["Status"] == "Solucionado")
    sol_periodo = len(df_base[mask_fechados])

    mask_referencia = mask_abertos if tipo_data_grafico == "Data de Abertura" else mask_fechados
    total_referencia = len(df_base[mask_referencia])

    sla_critico = len(df_base[mask_referencia & df_base["Estourado"]])
    sla_cumprido = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourado"])])
    
    # FCR é baseado no Esforço de Tarefas agora (Se resolveu com menos de 1h de esforço, é ágil)
    fcr_count = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourado"]) & (df_base["Esforco_Tarefas_h"] <= 1.0)])

    taxa_eficiencia = (sol_periodo / vol_periodo * 100) if vol_periodo > 0 else 0
    taxa_sla_critico = (sla_critico / total_referencia * 100) if total_referencia > 0 else 0
    taxa_sla_cumprido = (sla_cumprido / sol_periodo * 100) if sol_periodo > 0 else 0
    taxa_fcr = (fcr_count / sol_periodo * 100) if sol_periodo > 0 else 0
    vazao_dia = sol_periodo / dias_periodo

    # --- TOTALIZADORES ---
    st.subheader(f"📈 Indicadores do Período", help="Totalizadores calculados com base nos filtros da barra lateral.")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Volume Abertos", vol_periodo, help="Cálculo: Contagem absoluta de tickets criados no período. Indica o volume de entrada.")
    with c2: st.metric("Solucionados", sol_periodo, delta=f"{taxa_eficiencia:.1f}% Eficiência", delta_color="normal", help="Cálculo: Total Finalizados. A % Delta é a Eficiência (Saídas / Entradas).")
    with c3: st.metric("✅ SLA Cumprido", sla_cumprido, delta=f"{taxa_sla_cumprido:.1f}% sucesso", delta_color="normal", help="Cálculo: Total de tickets finalizados dentro do prazo estipulado por contrato.")
    with c4: st.metric("🚨 SLA Crítico", sla_critico, delta=f"{taxa_sla_critico:.1f}% estouraram", delta_color="inverse", help="Cálculo: Tickets que romperam o prazo. Foco primário para correção gerencial.")
    with c5: st.metric("⚡ FCR (1º Contato)", fcr_count, delta=f"{taxa_fcr:.1f}% ágeis", delta_color="normal", help="Cálculo: First Call Resolution. Quantidade de tickets resolvidos onde a soma do cronômetro de tarefas foi inferior a 1 hora.")
    with c6: st.metric("Vazão (Entregas/Dia)", f"{vazao_dia:.1f}", delta=f"{sol_periodo} total", delta_color="off", help="Cálculo: Média geométrica de resoluções diárias (Solucionados / Dias do Período).")

    st.markdown("---")

    mask_charts = (df_base[col_data_graficos].dt.date >= d_ini) & (df_base[col_data_graficos].dt.date <= d_fim)
    df_charts = df_base[mask_charts].copy()
    if not df_charts.empty:
        df_charts['Status_SLA'] = df_charts['Estourado'].map({True: 'Estourado 🚨', False: 'No Prazo ✅'})
        df_charts["Data Formatada"] = df_charts["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')

    # --- ANÁLISE 1: CICLO DE VIDA (LEAD TIME) ---
    st.subheader("⏳ Análise de Ciclo de Vida do Chamado (Lead Time Bruto)", 
                 help="[Métrica ITIL: Lead Time] Reflete o tempo cronológico que o chamado ficou na fila, desde a abertura até a solução final (incluindo madrugadas e fins de semana). Serve para identificar gargalos de espera sistêmica.")
    if not df_charts.empty:
        lead_time_medio = df_charts["Lead_Time_Bruto"].mean()
        st.info(f"**Tempo Médio de Vida do Chamado:** O ticket leva em média {lead_time_medio:.1f} horas desde a criação até o encerramento no sistema.")
        
        c_lt1, c_lt2 = st.columns(2)
        with c_lt1:
            df_lt_fase = df_charts.groupby(["Responsável", "Fase Nome"]).size().reset_index(name="Quantidade")
            fig_lt1 = px.bar(df_lt_fase, x="Responsável", y="Quantidade", color="Fase Nome", barmode="group", text_auto='.0f', title="Backlog Histórico por Fase")
            plot_interativo(fig_lt1, df_charts, "Responsável", "graf_lt_fase", is_horizontal=False)
        with c_lt2:
            df_sla_ana = df_charts.groupby(['Responsável', 'Status_SLA']).size().reset_index(name='Total')
            cores_sla = {'No Prazo ✅': '#2e7d32', 'Estourado 🚨': '#c62828'}
            fig_lt2 = px.bar(df_sla_ana, x='Responsável', y='Total', color='Status_SLA', barmode='stack', text_auto='.0f', color_discrete_map=cores_sla, title="Qualidade de Entrega vs Prazo Contratual")
            plot_interativo(fig_lt2, df_charts, "Responsável", "graf_lt_sla", is_horizontal=False)

    st.markdown("---")

    # --- ANÁLISE 2: ESFORÇO DE TAREFAS (TOUCH TIME) ---
    st.subheader("⏱️ Análise de Esforço Operacional (Horas Trabalhadas)", 
                 help="[Métrica ITIL: Touch Time / MTTR Faturável] Diferente do Lead Time, este relatório soma exclusivamente os segundos registrados no 'Play/Pause' das tarefas do Bitrix24. Mostra o tempo real em que a equipe esteve ativamente debruçada sobre o problema do cliente.")
    if not df_charts.empty:
        tempo_total = df_charts["Esforco_Tarefas_h"].sum()
        mttr_real = df_charts[df_charts["Esforco_Tarefas_h"] > 0]["Esforco_Tarefas_h"].mean() # Média só dos que tem tempo logado
        
        t1, t2, t3 = st.columns(3)
        t1.info(f"**Σ Custo Total Faturável:** {tempo_total:.1f} Horas trabalhadas pela equipe.")
        t2.info(f"**μ MTTR Real (Média por Chamado):** {mttr_real:.1f} Horas de esforço direto.")
        t3.success("💡 **Foco Gerencial:** Otimizar as horas nestes clientes ou analistas ofensores reduzirá custo financeiro.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            df_tempo_cli = df_charts.groupby("Cliente")["Esforco_Tarefas_h"].sum().reset_index().nlargest(10, "Esforco_Tarefas_h")
            fig_t1 = px.bar(df_tempo_cli, x='Cliente', y='Esforco_Tarefas_h', title="Maiores Consumidores de Horas (Top 10 Clientes)", text_auto='.1f')
            fig_t1.update_layout(yaxis_title="Σ Horas Faturáveis")
            plot_interativo(fig_t1, df_charts, "Cliente", "graf_esforco_cli", is_horizontal=False)
            
        with col_t2:
            df_tempo_ana = df_charts.groupby("Responsável")["Esforco_Tarefas_h"].sum().reset_index()
            fig_t2 = px.pie(df_tempo_ana, values='Esforco_Tarefas_h', names='Responsável', title="Alocação de Tempo por Analista", hole=0.3)
            plot_interativo(fig_t2, df_charts, "Responsável", "graf_esforco_ana", is_pie=True)

    st.markdown("---")

    # --- ANÁLISE 3: CAUSA RAIZ (PARETO) ---
    st.subheader("🔍 Estocástica de Causa-Raiz (Diagrama de Pareto)", 
                 help="[ITIL: Gestão de Problemas] Aplica a regra de Pareto (80/20). Identificar e mitigar as barras do topo eliminará o grosso do retrabalho e volume da sua operação de suporte.")
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

    # --- RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Matriz Bruta (Auditoria)"):
        if not df_charts.empty:
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Lead_Time_Bruto", "Esforco_Tarefas_h", "Motivo Abertura", "Motivo Fechamento", "Data Formatada"]
            cols_view_present = [col for col in cols_view if col in df_charts.columns]
            
            st.dataframe(df_charts[cols_view_present], width="stretch", hide_index=True)
            csv = df_charts.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório para CSV", csv, f"auditoria_completa_{d_ini}.csv", "text/csv")
