# relatorios.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_engine_rel

def renderizar_aba_gestao():
    st.header("📊 Inteligência de Dados e Gestão (ITIL 4 - CSI)", 
              help="[Princípio ITIL: Continual Service Improvement] Este módulo transforma os dados transacionais do Bitrix24 em inteligência estratégica para tomada de decisão.")
    
    def exibir_drilldown(selecao, df_base, coluna_filtro, eixo_alvo):
        if selecao and isinstance(selecao, dict) and "selection" in selecao:
            pontos = selecao["selection"].get("points", [])
            if pontos:
                valores = []
                for p in pontos:
                    # Captura de chaves compostas (vetor bidimensional) ou eixos padrões
                    if eixo_alvo == "customdata" and "customdata" in p and p["customdata"]:
                        val = p["customdata"][0]
                    else:
                        val = p.get(eixo_alvo)
                        if val is None:
                            val = p.get("label") or p.get("x") or p.get("y")
                    if val is not None: valores.append(val)
                
                valores = list(set(valores))
                if valores:
                    df_filtrado = df_base[df_base[coluna_filtro].isin(valores)]
                    st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtrado)} chamado(s) localizado(s) na intersecção selecionada.")
                    
                    cols = ["ID", "Responsável", "Cliente", "Fase Nome", "Motivo Abertura", "Motivo Fechamento", "Status_SLA", "Esforco_Formatado", "Data Formatada"]
                    df_show = df_filtrado[[c for c in cols if c in df_filtrado.columns]].copy()
                    
                    if "Esforco_Formatado" in df_show.columns:
                        df_show.rename(columns={"Esforco_Formatado": "Tempo Trabalhado"}, inplace=True)
                        
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

    def plot_interativo(fig, df_charts, coluna_filtro, key, eixo_alvo):
        try:
            selecao = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key)
            exibir_drilldown(selecao, df_charts, coluna_filtro, eixo_alvo)
        except TypeError:
            st.plotly_chart(fig, use_container_width=True, key=key)

    # --- BARRA LATERAL ESTÁTICA ---
    st.sidebar.subheader("🎯 Filtros Estocásticos")
    d_ini = st.sidebar.date_input("Data Início", value=date.today() - pd.Timedelta(days=15), format="DD/MM/YYYY")
    d_fim = st.sidebar.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
    dias_periodo = max((d_fim - d_ini).days + 1, 1)

    tipo_data_grafico = st.sidebar.radio("Referência de Busca:", ["Data de Abertura", "Data de Encerramento"])
    col_data_graficos = "Data Abertura" if tipo_data_grafico == "Data de Abertura" else "Data Modificacao"
    
    equipe_suporte = ["Ana Beatriz", "Djhames Moraes", "Luciana Scabini", "Thaísa Castilho"]
    analistas_sel = st.sidebar.multiselect("Filtrar Analistas", options=equipe_suporte, default=equipe_suporte)

    with st.spinner(f"Processando matriz vetorial e cruzando tarefas no Bitrix24..."):
        df = data_engine_rel.buscar_dados_historico(d_ini, d_fim)
        
    if df.empty:
        st.warning("Variância Zero. Nenhum dado encontrado na base neste período.")
        return

    clientes_sel = st.sidebar.multiselect("Filtrar Clientes", options=sorted(df["Cliente"].unique()))

    mask_charts = (df[col_data_graficos].dt.date >= d_ini) & (df[col_data_graficos].dt.date <= d_fim)
    df_base_temporal = df[mask_charts].copy()

    mask_base = df_base_temporal["Responsável"].isin(analistas_sel)
    if clientes_sel: mask_base &= df_base_temporal["Cliente"].isin(clientes_sel)
    df_base = df_base_temporal[mask_base].copy()

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

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Volume Abertos", vol_periodo, help="Total absoluto de chamados ABERTOS no período filtrado.")
    with c2: st.metric("Solucionados", sol_periodo, delta=f"{taxa_eficiencia:.1f}% Eficiência", delta_color="normal", help="Volume de tickets finalizados. A eficiência cruza resoluções x aberturas.")
    with c3: st.metric("✅ SLA Cumprido", sla_cumprido, delta=f"{taxa_sla_cumprido:.1f}% sucesso", delta_color="normal", help="Chamados entregues dentro da meta matemática estabelecida.")
    with c4: st.metric("🚨 SLA Crítico", sla_critico, delta=f"{taxa_sla_critico:.1f}% estouraram", delta_color="inverse", help="Chamados que ultrapassaram o tempo limite (Estourados).")
    with c5: st.metric("⚡ FCR (1º Contato)", fcr_count, delta=f"{taxa_fcr:.1f}% ágeis", delta_color="normal", help="First Call Resolution: Chamados fechados em menos de 1 hora de esforço direto.")
    with c6: st.metric("Vazão (Entregas/Dia)", f"{vazao_dia:.1f}", delta=f"{sol_periodo} total", delta_color="off", help="Média de chamados solucionados por dia de operação.")
    st.markdown("---")

    df_charts = df_base.copy()
    if not df_charts.empty:
        df_charts['Status_SLA'] = df_charts['Estourado'].map({True: 'Estourado 🚨', False: 'No Prazo ✅'})
        df_charts["Data Formatada"] = df_charts["Data Abertura"].dt.strftime('%d/%m/%Y %H:%M')
        df_charts['Data_Ref_Str'] = df_charts[col_data_graficos].dt.strftime('%Y-%m-%d')
        # ⚠️ CRIAÇÃO DA CHAVE COMPOSTA PARA O SLA (Intersecção)
        df_charts['Chave_SLA'] = df_charts['Responsável'].astype(str) + "|" + df_charts['Status_SLA'].astype(str)

    st.info("💡 **Atenção (Drill-Down):** Interaja com os gráficos e tabelas abaixo clicando diretamente nos **pontos, barras ou linhas** para detalhar as informações.")

    # --- 2. ANÁLISE DE ESFORÇO (TOUCH TIME) ---
    st.subheader("⏱️ Análise de Esforço Operacional (Horas Trabalhadas)")
    
    with st.expander("ℹ️ Como ler este relatório (Otimização de Custos)"):
        st.markdown("""
        **Para que serve:** Identificar os clientes que mais consomem as horas faturáveis da equipe e como a carga horária direta está dividida entre os analistas.
        
        **Cálculo Matemático:** O sistema varre o banco de tarefas do Bitrix, extrai o campo `TIME_SPENT_IN_LOGS` e soma os segundos, convertendo para horas fracionadas. **Não** contabiliza o tempo de espera do ticket, apenas o trabalho braçal direto.
        
        *Dica da Gestão:* Renegociar contratos com os clientes nas primeiras barras à esquerda.
        """)

    def formatar_hhmmss(horas_dec):
        h = int(horas_dec)
        m = int((horas_dec - h) * 60)
        s = int((((horas_dec - h) * 60) - m) * 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    if not df_charts.empty:
        tempo_total = df_charts.get("Esforco_Tarefas_h", pd.Series([0])).sum()
        df_com_esforco = df_charts[df_charts.get("Esforco_Tarefas_h", 0) > 0]
        mttr_real = df_com_esforco["Esforco_Tarefas_h"].mean() if not df_com_esforco.empty else 0
        
        t1, t2 = st.columns(2)
        t1.info(f"**Σ Custo Total Faturável:** {formatar_hhmmss(tempo_total)} (HH:MM:SS) trabalhadas pela equipe.")
        t2.info(f"**μ MTTR Real (Média por Chamado):** {formatar_hhmmss(mttr_real)} (HH:MM:SS) de esforço direto.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if "Esforco_Tarefas_h" in df_charts:
                opcao_visao_cli = st.radio("Visão de Consumo:", ["Gráfico (Top 15)", "Tabela Auditável (Todos)"], horizontal=True)
                
                df_agrupado_cli = df_charts.groupby("Cliente")["Esforco_Tarefas_h"].sum().reset_index()
                
                if opcao_visao_cli == "Gráfico (Top 15)":
                    df_tempo_cli = df_agrupado_cli.nlargest(15, "Esforco_Tarefas_h")
                    df_tempo_cli["Tempo Texto"] = df_tempo_cli["Esforco_Tarefas_h"].apply(formatar_hhmmss)
                    
                    fig_t1 = px.bar(df_tempo_cli, x='Cliente', y='Esforco_Tarefas_h', title="Maiores Consumidores de Horas (Top 15)", text='Tempo Texto')
                    fig_t1.update_layout(yaxis_title="Volume de Horas (Escala Dec)")
                    plot_interativo(fig_t1, df_charts, "Cliente", "graf_esforco_cli", eixo_alvo="x")
                
                else:
                    st.markdown("**Matriz Completa de Clientes (Selecione uma linha)**")
                    
                    df_tabela_cli = df_agrupado_cli.sort_values(by="Esforco_Tarefas_h", ascending=False).copy()
                    df_tabela_cli["Tempo Faturável (Total)"] = df_tabela_cli["Esforco_Tarefas_h"].apply(formatar_hhmmss)
                    df_show_tabela = df_tabela_cli[["Cliente", "Tempo Faturável (Total)"]]
                    
                    evento_tabela = st.dataframe(
                        df_show_tabela, 
                        use_container_width=True, 
                        hide_index=True, 
                        on_select="rerun", 
                        selection_mode="single-row",
                        key="tabela_cli_todos",
                        height=350 
                    )
                    
                    if evento_tabela and "selection" in evento_tabela and "rows" in evento_tabela["selection"] and len(evento_tabela["selection"]["rows"]) > 0:
                        indice_selecionado = evento_tabela["selection"]["rows"][0]
                        cliente_selecionado = df_show_tabela.iloc[indice_selecionado]["Cliente"]
                        
                        df_filtro_cli = df_charts[df_charts["Cliente"] == cliente_selecionado].copy()
                        st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtro_cli)} chamado(s) localizado(s) para '{cliente_selecionado}'.")
                        
                        cols_cli = ["ID", "Responsável", "Fase Nome", "Esforco_Formatado", "Data Formatada"]
                        df_chamados_cli = df_filtro_cli[[c for c in cols_cli if c in df_filtro_cli.columns]].copy()
                        if "Esforco_Formatado" in df_chamados_cli.columns:
                            df_chamados_cli.rename(columns={"Esforco_Formatado": "Tempo Trabalhado"}, inplace=True)
                            
                        st.dataframe(df_chamados_cli, use_container_width=True, hide_index=True)
            
        with col_t2:
            if "Esforco_Tarefas_h" in df_charts:
                df_tempo_ana = df_charts.groupby("Responsável")["Esforco_Tarefas_h"].sum().reset_index().sort_values("Esforco_Tarefas_h", ascending=True)
                df_tempo_ana["Tempo Texto"] = df_tempo_ana["Esforco_Tarefas_h"].apply(formatar_hhmmss)
                
                fig_t2 = px.bar(df_tempo_ana, y='Responsável', x='Esforco_Tarefas_h', orientation='h', 
                                title="Alocação de Tempo por Analista", text='Tempo Texto', color='Responsável')
                fig_t2.update_layout(xaxis_title="Volume de Horas", yaxis_title="", showlegend=False)
                plot_interativo(fig_t2, df_charts, "Responsável", "graf_esforco_ana", eixo_alvo="y")

    st.markdown("---")

    # --- 3. CAUSA RAIZ (PARETO) ---
    st.subheader("🔍 Estocástica de Causa-Raiz (Diagrama de Pareto)")

    with st.expander("ℹ️ Como utilizar esta análise (Regra 80/20)"):
        st.markdown("""
        **Para que serve:** Aplicação do Princípio de Pareto para identificar as causas-raiz vitais que geram o maior volume de chamados na operação de suporte.
        
        **Cálculo Matemático:** O sistema agrupa a frequência absoluta dos campos 'Motivo de Abertura' e 'Motivo de Fechamento', ordenando de forma decrescente para isolar os maiores ofensores.
        
        *Dica da Gestão:* Focar treinamentos e resoluções sistêmicas nos 3 primeiros motivos da esquerda reduzirá drasticamente o volume de chamados futuros.
        """)

    l3_g1, l3_g2 = st.columns(2)

    def gerar_dados_pareto(df_p, coluna):
        df_freq = df_p[coluna].value_counts().reset_index()
        df_freq.columns = [coluna, 'Frequência Absoluta']
        return df_freq

    with l3_g1:
        st.markdown("**Matriz de Motivos de Abertura (Entrada)**")
        if "Motivo Abertura" in df_charts.columns and not df_charts["Motivo Abertura"].dropna().empty:
            opcao_visao_abertura = st.radio("Visão de Entrada:", ["Gráfico (Top 10)", "Tabela Auditável (Todos)"], horizontal=True, key="rad_abert")
            df_abertura_full = gerar_dados_pareto(df_charts, "Motivo Abertura")
            
            if opcao_visao_abertura == "Gráfico (Top 10)":
                df_abertura_top = df_abertura_full.head(10)
                fig_abertura = px.bar(df_abertura_top, y='Motivo Abertura', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Blues')
                fig_abertura.update_layout(xaxis_title="Σ Volume", yaxis_title="")
                plot_interativo(fig_abertura, df_charts, "Motivo Abertura", "graf_motivo_abertura", eixo_alvo="y")
            else:
                st.markdown("**Lista Completa de Motivos (Selecione uma linha)**")
                evento_abert = st.dataframe(
                    df_abertura_full, 
                    use_container_width=True, 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row",
                    key="tab_abert_todos",
                    height=350
                )
                
                if evento_abert and "selection" in evento_abert and "rows" in evento_abert["selection"] and len(evento_abert["selection"]["rows"]) > 0:
                    idx_abert = evento_abert["selection"]["rows"][0]
                    motivo_abert_sel = df_abertura_full.iloc[idx_abert]["Motivo Abertura"]
                    
                    df_filtro_abert = df_charts[df_charts["Motivo Abertura"] == motivo_abert_sel].copy()
                    st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtro_abert)} chamados abertos por '{motivo_abert_sel}'.")
                    
                    cols_abert = ["ID", "Cliente", "Responsável", "Esforco_Formatado", "Data Formatada"]
                    df_show_abert = df_filtro_abert[[c for c in cols_abert if c in df_filtro_abert.columns]].copy()
                    if "Esforco_Formatado" in df_show_abert.columns:
                        df_show_abert.rename(columns={"Esforco_Formatado": "Tempo Trabalhado"}, inplace=True)
                        
                    st.dataframe(df_show_abert, use_container_width=True, hide_index=True)

    with l3_g2:
        st.markdown("**Matriz de Resoluções (Fechamento)**")
        if "Motivo Fechamento" in df_charts.columns and not df_charts["Motivo Fechamento"].dropna().empty:
            df_solucionados = df_charts[df_charts["Status"] == "Solucionado"]
            if not df_solucionados.empty:
                opcao_visao_fechamento = st.radio("Visão de Resolução:", ["Gráfico (Top 10)", "Tabela Auditável (Todos)"], horizontal=True, key="rad_fecham")
                df_fechamento_full = gerar_dados_pareto(df_solucionados, "Motivo Fechamento")
                
                if opcao_visao_fechamento == "Gráfico (Top 10)":
                    df_fechamento_top = df_fechamento_full.head(10)
                    fig_fechamento = px.bar(df_fechamento_top, y='Motivo Fechamento', x='Frequência Absoluta', orientation='h', text_auto='.0f', color='Frequência Absoluta', color_continuous_scale='Greens')
                    fig_fechamento.update_layout(xaxis_title="Σ Volume", yaxis_title="")
                    plot_interativo(fig_fechamento, df_charts, "Motivo Fechamento", "graf_motivo_fechamento", eixo_alvo="y")
                else:
                    st.markdown("**Lista Completa de Motivos (Selecione uma linha)**")
                    evento_fecham = st.dataframe(
                        df_fechamento_full, 
                        use_container_width=True, 
                        hide_index=True, 
                        on_select="rerun", 
                        selection_mode="single-row",
                        key="tab_fecham_todos",
                        height=350
                    )
                    
                    if evento_fecham and "selection" in evento_fecham and "rows" in evento_fecham["selection"] and len(evento_fecham["selection"]["rows"]) > 0:
                        idx_fecham = evento_fecham["selection"]["rows"][0]
                        motivo_fecham_sel = df_fechamento_full.iloc[idx_fecham]["Motivo Fechamento"]
                        
                        df_filtro_fecham = df_solucionados[df_solucionados["Motivo Fechamento"] == motivo_fecham_sel].copy()
                        st.success(f"🔎 **Auditoria Drill-Down:** {len(df_filtro_fecham)} chamados solucionados por '{motivo_fecham_sel}'.")
                        
                        cols_fecham = ["ID", "Cliente", "Responsável", "Esforco_Formatado", "Data Formatada"]
                        df_show_fecham = df_filtro_fecham[[c for c in cols_fecham if c in df_filtro_fecham.columns]].copy()
                        if "Esforco_Formatado" in df_show_fecham.columns:
                            df_show_fecham.rename(columns={"Esforco_Formatado": "Tempo Trabalhado"}, inplace=True)
                            
                        st.dataframe(df_show_fecham, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 4. VISÃO MACRO E QUALIDADE SLA ---
    st.subheader("🌐 Visão Macroeconômica e Produtividade")
    
    with st.expander("ℹ️ Como ler a Visão Macro e Qualidade"):
        st.markdown("""
        **Para que serve:** Monitorar a estabilidade da entrada de demandas e medir a conformidade das entregas com os Acordos de Nível de Serviço (SLA).
        
        **Cálculo Matemático:** A Evolução Diária interpola os dias sem chamados com o valor estático `0` para manter a integridade do eixo temporal de data. O SLA cruza o tempo decorrido desde a abertura contra a meta da fase atual configurada no código.
        
        *Dica da Gestão:* Picos acentuados no gráfico de linhas indicam anomalias no sistema que devem ser investigados imediatamente.
        """)

    l1_g1, l1_g2 = st.columns(2)
    with l1_g1:
        st.markdown("**Evolução Diária de Demandas**")
        if not df_charts.empty:
            todas_datas = pd.date_range(start=d_ini, end=d_fim).strftime('%Y-%m-%d')
            df_trend_base = df_charts.groupby('Data_Ref_Str').size().reset_index(name="Quantidade")
            
            df_trend_completo = pd.DataFrame({'Data_Ref_Str': todas_datas})
            df_trend = df_trend_completo.merge(df_trend_base, on='Data_Ref_Str', how='left').fillna(0)
            
            df_trend['Data Exibicao'] = pd.to_datetime(df_trend['Data_Ref_Str']).dt.strftime('%d/%m/%y')
            
            fig_trend = px.line(df_trend, x='Data_Ref_Str', y="Quantidade", markers=True, text="Quantidade")
            
            fig_trend.update_xaxes(type='category', tickangle=-45, title="")
            fig_trend.update_yaxes(title="Volume")
            fig_trend.update_traces(textposition="top center")
            fig_trend.update_layout(margin=dict(t=10))
            
            plot_interativo(fig_trend, df_charts, "Data_Ref_Str", "graf_evolucao_diaria", eixo_alvo="x") 

    with l1_g2:
        st.markdown("**Qualidade de Entrega (SLA por Analista)**")
        if not df_charts.empty:
            df_sla_ana = df_charts.groupby(['Responsável', 'Status_SLA']).size().reset_index(name='Total')
            
            # ⚠️ VÍNCULO DA CHAVE COMPOSTA: Prepara a variável analítica que intercepta (Analista + Status)
            df_sla_ana['Chave_SLA'] = df_sla_ana['Responsável'].astype(str) + "|" + df_sla_ana['Status_SLA'].astype(str)
            
            cores_sla = {'No Prazo ✅': '#2e7d32', 'Estourado 🚨': '#c62828'}
            
            # custom_data injeta a chave composta no clique do usuário
            fig_sla = px.bar(df_sla_ana, x='Responsável', y='Total', color='Status_SLA', barmode='stack', text_auto='.0f', color_discrete_map=cores_sla, custom_data=['Chave_SLA'])
            fig_sla.update_layout(xaxis_title="", yaxis_title="Chamados", margin=dict(t=10))
            
            # eixo_alvo="customdata" diz ao Streamlit para ler a chave composta em vez do eixo X ou Y simples
            plot_interativo(fig_sla, df_charts, "Chave_SLA", "graf_sla_qualidade", eixo_alvo="customdata")

    # --- RELATÓRIO DETALHADO ---
    with st.expander("📄 Visualizar Matriz Bruta (Auditoria)"):
        if not df_charts.empty:
            cols_view = ["ID", "Responsável", "Cliente", "Fase Nome", "Lead_Time_Bruto", "Esforco_Formatado", "Motivo Abertura", "Motivo Fechamento", "Data Formatada"]
            cols_view_present = [col for col in cols_view if col in df_charts.columns]
            
            df_export = df_charts[cols_view_present].copy()
            if "Esforco_Formatado" in df_export.columns:
                df_export.rename(columns={"Esforco_Formatado": "Tempo Trabalhado"}, inplace=True)
                
            st.dataframe(df_export, width="stretch", hide_index=True)
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Relatório para CSV", csv, f"auditoria_completa_{d_ini}.csv", "text/csv")
