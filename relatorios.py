# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4 - CSI)", 
              help="[Princípio ITIL: Continual Service Improvement] Este módulo transforma os dados transacionais do Bitrix24 em inteligência estratégica para tomada de decisão.")
    
    # --- FUNÇÃO DE DRILL-DOWN OTIMIZADA ---
    def exibir_drilldown(selecao, df_base, coluna_filtro):
        if selecao and isinstance(selecao, dict) and "selection" in selecao:
            pontos = selecao["selection"].get("points", [])
            if pontos:
                # Otimizado para caçar a variável em eixos X, Y ou Label (Pizza)
                valores = []
                for p in pontos:
                    val = p.get("label") or p.get("x") or p.get("y")
                    if val is not None: valores.append(val)
                
                valores = list(set(valores))
                if valores:
                    df_filtrado = df_base[df_base[coluna_filtro].isin(valores)]
                    st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtrado)} chamado(s) localizado(s) para '{', '.join(map(str, valores))}'.")
                    
                    cols = ["ID", "Responsável", "Cliente", "Fase Nome", "Motivo Abertura", "Esforco_Tarefas_h"]
                    df_show = df_filtrado[[c for c in cols if c in df_filtrado.columns]].copy()
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

    def plot_interativo(fig, df_charts, coluna_filtro, key):
        # Desabilita o evento de esconder da legenda. Oculta frustrações da diretoria.
        fig.update_layout(legend=dict(itemclick=False, itemdoubleclick=False))
        try:
            selecao = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key)
            exibir_drilldown(selecao, df_charts, coluna_filtro)
        except TypeError:
            st.plotly_chart(fig, use_container_width=True, key=key)

    # --- BARRA LATERAL ESTÁTICA ---
    st.sidebar.subheader("🎯 Filtros Estocásticos")
    d_ini = st.sidebar.date_input("Data Início", value=date.today() - pd.Timedelta(days=15), format="DD/MM/YYYY")
    d_fim = st.sidebar.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
    dias_periodo = max((d_fim - d_ini).days + 1, 1)

    tipo_data_grafico = st.sidebar.radio("Referência de Busca:", ["Data de Abertura", "Data de Encerramento"], 
                                         help="Define a constante temporal: Se os relatórios avaliarão chamados CRIADOS ou FINALIZADOS no período selecionado acima.")
    col_data_graficos = "Data Abertura" if tipo_data_grafico == "Data de Abertura" else "Data Modificacao"
    
    equipe_suporte = ["Ana Beatriz", "Djhames Moraes", "Luciana Scabini", "Thaísa Castilho"]
    analistas_sel = st.sidebar.multiselect("Filtrar Analistas", options=equipe_suporte, default=equipe_suporte)

    with st.spinner(f"Processando matriz vetorial e cruzando tarefas no Bitrix24..."):
        df = data_engine_rel.buscar_dados_historico(d_ini, d_fim)
        
    if df.empty:
        st.warning("Variância Zero. Nenhum dado encontrado na base neste período.")
        return

    clientes_sel = st.sidebar.multiselect("Filtrar Clientes", options=sorted(df["Cliente"].unique()))

    mask_base = df["Responsável"].isin(analistas_sel)
    if clientes_sel: mask_base &= df["Cliente"].isin(clientes_sel)
    df_base = df[mask_base].copy()

    # --- PROCESSAMENTO DE VARIÁVEIS MACRO ---
    mask_abertos = (df_base["Data Abertura"].dt.date >= d_ini) & (df_base["Data Abertura"].dt.date <= d_fim)
    vol_periodo = len(df_base[mask_abertos])

    mask_fechados = (df_base["Data Modificacao"].dt.date >= d_ini) & (df_base["Data Modificacao"].dt.date <= d_fim) & (df_base["Status"] == "Solucionado")
    sol_periodo = len(df_base[mask_fechados])

    mask_referencia = mask_abertos if tipo_data_grafico == "Data de Abertura" else mask_fechados
    total_referencia = len(df_base[mask_referencia])

    sla_critico = len(df_base[mask_referencia & df_base["Estourado"]])
    sla_cumprido = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourado"])])
    
    fcr_count = len(df_base[mask_referencia & (df_base["Status"] == "Solucionado") & (~df_base["Estourado"]) & (df_base.get("Esforco_Tarefas_h", 0) <= 1.0)])

    taxa_eficiencia = (sol_periodo / vol_periodo * 100) if vol_periodo > 0 else 0
    taxa_sla_critico = (sla_critico / total_referencia * 100) if total_referencia > 0 else 0
    taxa_sla_cumprido = (sla_cumprido / sol_periodo * 100) if sol_periodo > 0 else 0
    taxa_fcr = (fcr_count / sol_periodo * 100) if sol_periodo > 0 else 0
    vazao_dia = sol_periodo / dias_periodo

    # --- 1. TOTALIZADORES ---
    st.subheader(f"📈 Indicadores do Período", help="Totalizadores quantitativos do setor. Respondem dinamicamente aos filtros aplicados na barra lateral esquerda.")
    with st.expander("ℹ️ Dicionário de Métricas (Como são calculadas)"):
        st.markdown("""
        * **Volume Abertos:** Soma absoluta de tickets criados no período. Indica a demanda entrante.
        * **Solucionados:** Tickets finalizados (WON). A porcentagem indica Eficiência (Solucionados / Abertos).
        * **SLA Cumprido/Crítico:** Tickets resolvidos dentro vs fora da meta de tempo do contrato.
        * **FCR (First Call Resolution):** Chamados onde a soma do *cronômetro das tarefas* foi inferior a 1 hora. Indica alta destreza técnica.
        * **Vazão:** Média aritmética de entregas diárias da equipe.
        """)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Volume Abertos", vol_periodo)
    with c2: st.metric("Solucionados", sol_periodo, delta=f"{taxa_eficiencia:.1f}% Eficiência", delta_color="normal")
    with c3: st.metric("✅ SLA Cumprido", sla_cumprido, delta=f"{taxa_sla_cumprido:.1f}% sucesso", delta_color="normal")
    with c4: st.metric("🚨 SLA Crítico", sla_critico, delta=f"{taxa_sla_critico:.1f}% estouraram", delta_color="inverse")
    with c5: st.metric("⚡ FCR (1º Contato)", fcr_count, delta=f"{taxa_fcr:.1f}% ágeis", delta_color="normal")
    with c6: st.metric("Vazão (Entregas/Dia)", f"{vazao_dia:.1f}", delta=f"{sol_periodo} total", delta_color="off")
    st.markdown("---")

    mask_charts = (df_base[col_data_graficos].dt.date >= d_ini) & (df_base[col_data_graficos].dt.date <= d_fim)
    df_charts = df_base[mask_charts].copy()
    if not df_charts.empty:
        df_charts['Status_SLA'] = df_charts['Estourado'].map({True: 'Estourado 🚨', False: 'No Prazo ✅'})
        df_charts["Data Formatada"] = df_charts["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')

    # Alerta Ergonômico de Uso
    st.info("💡 **Atenção (Drill-Down):** Para detalhar os dados nas tabelas, clique diretamente nas **barras ou nas fatias coloridas** dos gráficos. O sistema não captura cliques sobre os nomes da legenda lateral.")

    # --- 2. ANÁLISE DE ESFORÇO (TOUCH TIME) ---
    st.subheader("⏱️ Análise de Esforço Operacional (Horas Trabalhadas)", help="[ITIL: Touch Time] Soma matemática do tempo exato em que a equipe deu o 'Play' no cronômetro das tarefas dentro dos chamados.")
    
    with st.expander("ℹ️ Como ler este relatório (Otimização de Custos)"):
        st.markdown("""
        **Para que serve:** Identificar os clientes que mais consomem as horas faturáveis da equipe e como a carga horária direta está dividida entre os analistas.
        **Cálculo Matemático:** O sistema varre o banco de tarefas do Bitrix, extrai o campo `TIME_SPENT_IN_LOGS` e soma os segundos. **Foi corrigido o bug de redundância da API**, garantindo que não existam horas duplicadas somadas.
        """)

    if not df_charts.empty:
        tempo_total = df_charts.get("Esforco_Tarefas_h", pd.Series([0])).sum()
        df_com_esforco = df_charts[df_charts.get("Esforco_Tarefas_h", 0) > 0]
        mttr_real = df_com_esforco["Esforco_Tarefas_h"].mean() if not df_com_esforco.empty else 0
        
        t1, t2 = st.columns(2)
        t1.info(f"**Σ Custo Total Faturável:** {tempo_total:.1f} Horas trabalhadas pela equipe.")
        t2.info(f"**μ MTTR Real (Média por Chamado):** {mttr_real:.1f} Horas de esforço direto.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if "Esforco_Tarefas_h" in df_charts:
                df_tempo_cli = df_charts.groupby("Cliente")["Esforco_Tarefas_h"].sum().reset_index().nlargest(10, "Esforco_Tarefas_h")
                fig_t1 = px.bar(df_tempo_cli, x='Cliente', y='Esforco_Tarefas_h', title="Maiores Consumidores de Horas (Top 10 Clientes)", text_auto='.1f')
                fig_t1.update_layout(yaxis_title="Σ Horas Faturáveis")
                plot_interativo(fig_t1, df_charts, "Cliente", "graf_esforco_cli")
            
        with col_t2:
            if "Esforco_Tarefas_h" in df_charts:
                df_tempo_ana = df_charts.groupby("Responsável")["Esforco_Tarefas_h"].sum().reset_index()
                fig_t2 = px.pie(df_tempo_ana, values='Esforco_Tarefas_h', names='Responsável', title="Alocação de Tempo por Analista", hole=0.3)
                plot_interativo(fig_t2, df_charts, "Responsável", "graf_esforco_ana")

    st.markdown("---")

    # --- 3. CAUSA RAIZ (PARETO) ---
    st.subheader("🔍 Estocástica de Causa-Raiz (Diagrama de Pareto)", help="[ITIL: Problem Management] Visualização hierárquica dos maiores motivos de acionamento do suporte.")
    
    with st.expander("ℹ️ Como utilizar esta análise (Regra 80/20)"):
        st.markdown("""
        **Princípio de Pareto:** Estatisticamente, $80\%$ dos problemas são gerados por $20\%$ das causas. 
        **Ação Gerencial:** Ao atacar e resolver estruturalmente os problemas representados pelas maiores barras, o volume total de chamados na empresa despencará.
        """)

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
            plot_interativo(fig_abertura, df_charts, "Motivo Abertura", "graf_motivo_abertura")

    with l3_g2:
        st.markdown("**Matriz de Resoluções (Fechamento)**")
        if "Motivo Fechamento" in df_charts.columns and not df_charts["Motivo Fechamento"].dropna().empty:
            df_solucionados = df_charts[df_charts["Status"] == "Solucionado"]
            if not df_solucionados.empty:
                df_fechamento = gerar_dados_pareto(df_solucionados, "Motivo Fechamento").head(10)
                fig_fechamento = px.bar(df_fechamento, y='Motivo Fechamento', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Greens')
                fig_fechamento.update_layout(xaxis_title="Σ Volume", yaxis_title="")
                plot_interativo(fig_fechamento, df_charts, "Motivo Fechamento", "graf_motivo_fechamento")

    st.markdown("---")

    # --- 4. VISÃO MACRO E QUALIDADE SLA ---
    st.subheader("🌐 Visão Macroeconômica e Produtividade", help="Cruza o volume cronológico de entrada com a qualidade de entrega contratual de cada membro da equipe.")
    
    with st.expander("ℹ️ Leitura Gerencial (Tendência e Qualidade)"):
        st.markdown("""
        * **Evolução de Demandas:** Mostra picos e vales do volume de trabalho dia a dia. Útil para prever escalas de plantão e descobrir sazonalidades.
        * **Qualidade de SLA:** Uma análise puramente técnica das infrações de prazo por funcionário. Ideal para basear feedbacks.
        """)

    l1_g1, l1_g2 = st.columns(2)
    with l1_g1:
        st.markdown("**Evolução Diária de Demandas**")
        if not df_charts.empty:
            df_trend = df_charts.groupby(df_charts[col_data_graficos].dt.date).size().reset_index(name="Quantidade")
            fig_trend = px.line(df_trend, x=col_data_graficos, y="Quantidade", markers=True)
            fig_trend.update_layout(xaxis_title="", yaxis_title="Volume", margin=dict(t=10))
            st.plotly_chart(fig_trend, use_container_width=True)

    with l1_g2:
        st.markdown("**Qualidade de Entrega (SLA por Analista)**")
        if not df_charts.empty:
            df_sla_ana = df_charts.groupby(['Responsável', 'Status_SLA']).size().reset_index(name='Total')
            cores_sla = {'No Prazo ✅': '#2e7d32', 'Estourado 🚨': '#c62828'}
            fig_sla = px.bar(df_sla_ana, x='Responsável', y='Total', color='Status_SLA', barmode='stack', text_auto='.0f', color_discrete_map=cores_sla)
            fig_sla.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            plot_interativo(fig_sla, df_charts, "Responsável", "graf_sla_qualidade")

    # --- RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Matriz Bruta (Auditoria)"):
        if not df_charts.empty:
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Lead_Time_Bruto", "Esforco_Tarefas_h", "Motivo Abertura", "Motivo Fechamento", "Data Formatada"]
            cols_view_present = [col for col in cols_view if col in df_charts.columns]
            
            st.dataframe(df_charts[cols_view_present], width="stretch", hide_index=True)
            csv = df_charts.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório para CSV", csv, f"auditoria_completa_{d_ini}.csv", "text/csv")
