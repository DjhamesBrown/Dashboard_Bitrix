# data_engine_rel.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import config

@st.cache_data(ttl=3600)
def obter_dicionario_campo(nome_campo_uf):
    try:
        resp = requests.post(f"{config.WEBHOOK_URL}/crm.deal.userfield.list", json={"filter": {"FIELD_NAME": nome_campo_uf}}).json()
        if "result" in resp and len(resp["result"]) > 0:
            itens = resp["result"][0].get("LIST", [])
            return {str(item["ID"]): item["VALUE"] for item in itens}
    except Exception as e:
        print(f"Erro dicionário: {e}")
    return {}

@st.cache_data(ttl=300)
def buscar_esforco_tarefas(lista_ids_deals):
    """Mapeamento de tarefas cruzando chaves primárias do CRM com expurgo de clones da API"""
    if not lista_ids_deals: return pd.DataFrame()
    
    todas_tarefas = []
    chunk_size = 50 
    
    for i in range(0, len(lista_ids_deals), chunk_size):
        chunk = lista_ids_deals[i:i + chunk_size]
        chaves_crm = [f"D_{id}" for id in chunk]
        
        start = 0
        while True:
            payload = {
                "filter": {"UF_CRM_TASK": chaves_crm},
                "select": ["ID", "TIME_SPENT_IN_LOGS", "UF_CRM_TASK"],
                "start": start
            }
            resp = requests.post(f"{config.WEBHOOK_URL}/tasks.task.list", json=payload).json()
            
            if "result" in resp and "tasks" in resp["result"]: 
                todas_tarefas.extend(resp["result"]["tasks"])
            
            if "next" in resp: start = resp["next"]
            else: break
            
    df_tasks = pd.DataFrame(todas_tarefas)
    if df_tasks.empty: return pd.DataFrame()
    
    # ⚠️ BARREIRA MATEMÁTICA: Expurga tarefas duplicadas geradas por falha de paginação do Bitrix
    col_id = "id" if "id" in df_tasks.columns else ("ID" if "ID" in df_tasks.columns else None)
    if col_id:
        df_tasks.drop_duplicates(subset=col_id, inplace=True)
    
    # Tratamento de Polimorfismo
    def extrair_id(val):
        if not val: return ""
        if isinstance(val, list):
            for item in val:
                if str(item).startswith("D_"): return str(item).replace("D_", "")
        elif isinstance(val, str) and val.startswith("D_"):
            return val.replace("D_", "")
        return ""
        
    col_crm = "ufCrmTask" if "ufCrmTask" in df_tasks.columns else ("UF_CRM_TASK" if "UF_CRM_TASK" in df_tasks.columns else None)
    if col_crm:
        df_tasks["Deal_ID"] = df_tasks[col_crm].apply(extrair_id)
    else:
        df_tasks["Deal_ID"] = ""
        
    col_time = "timeSpentInLogs" if "timeSpentInLogs" in df_tasks.columns else ("TIME_SPENT_IN_LOGS" if "TIME_SPENT_IN_LOGS" in df_tasks.columns else None)
    if col_time:
        df_tasks["Tempo_Horas"] = pd.to_numeric(df_tasks[col_time], errors='coerce').fillna(0) / 3600
    else:
        df_tasks["Tempo_Horas"] = 0
    
    # Agrupa e soma garantindo apenas 2 casas decimais
    df_agrupado = df_tasks.groupby("Deal_ID")["Tempo_Horas"].sum().reset_index()
    df_agrupado["Tempo_Horas"] = df_agrupado["Tempo_Horas"].round(2)
    return df_agrupado

@st.cache_data(ttl=300) 
def buscar_dados_historico(data_inicio, data_fim):
    try:
        inicio_str = data_inicio.strftime("%Y-%m-%d") + "T00:00:00"
        fim_str = data_fim.strftime("%Y-%m-%d") + "T23:59:59"
        todos_dados = []
        filtros_api = [
            {">=DATE_CREATE": inicio_str, "<=DATE_CREATE": fim_str, "CATEGORY_ID": 8},
            {">=DATE_MODIFY": inicio_str, "<=DATE_MODIFY": fim_str, "CATEGORY_ID": 8}
        ]
        for filtro in filtros_api:
            start = 0
            while True: 
                payload = {"filter": filtro, "select": list(config.CAMPOS_BITRIX.keys()), "start": start}
                resp = requests.post(f"{config.WEBHOOK_URL}/crm.deal.list", json=payload).json()
                if "result" in resp and resp["result"]: todos_dados.extend(resp["result"])
                if "next" in resp: start = resp["next"]
                else: break 
                    
        df = pd.DataFrame(todos_dados)
        if df.empty: return pd.DataFrame()
        
        df.drop_duplicates(subset="ID", inplace=True)
        
        # Merge Matemático com o Motor de Tarefas
        df_tarefas = buscar_esforco_tarefas(df["ID"].tolist())
        if not df_tarefas.empty:
            df = df.merge(df_tarefas, left_on="ID", right_on="Deal_ID", how="left")
            df["Esforco_Tarefas_h"] = df["Tempo_Horas"].fillna(0)
        else:
            df["Esforco_Tarefas_h"] = 0
        
        # Tradução Estatística
        for campo_uf, nome_legivel in config.CAMPOS_BITRIX.items():
            if "Motivo" in nome_legivel and campo_uf in df.columns:
                dic = obter_dicionario_campo(campo_uf)
                df[campo_uf] = df[campo_uf].astype(str).map(dic).fillna("Não Classificado")

        df.rename(columns=config.CAMPOS_BITRIX, inplace=True)
        df["Fase Nome"] = df["Fase_Cod"].map(config.NOMES_FASES).fillna(df["Fase_Cod"])
        
        df["Data Abertura"] = pd.to_datetime(df["Data Abertura"]).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Modificacao"] = pd.to_datetime(df["Data Modificacao"]).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Formatada"] = df["Data Abertura"].dt.strftime('%d/%m %H:%M')
        
        agora = datetime.now()
        df["Lead_Time_Bruto"] = df.apply(lambda row: (row["Data Modificacao"] if row["Fase_Cod"] == "C8:WON" else agora) - row["Data Abertura"], axis=1).dt.total_seconds() / 3600
        df["Horas Passadas"] = (agora - df["Data Abertura"]).dt.total_seconds() / 3600
        
        def definir_status(row):
            cod = row["Fase_Cod"]
            if cod == "C8:WON": return "Solucionado"
            if cod == "C8:UC_N5RGUL": return "Em Pausa"
            if cod == "C8:LOSE": return "Cancelado"
            return "Em Aberto"
        df["Status"] = df.apply(definir_status, axis=1)

        def definir_meta(cod):
            if cod in ["C8:UC_O0PER6", "C8:UC_OKYBJK"]: return 2
            if cod == "C8:UC_3RMJ6E": return 4
            if cod == "C8:UC_LQG67P": return 24
            return 9999
        df["SLA_Meta"] = df["Fase_Cod"].apply(definir_meta)

        def calcular_regressiva(row):
            if row["Status"] != "Em Aberto": return "---"
            saldo = row["SLA_Meta"] - row["Horas Passadas"]
            if saldo < 0: return f"🚨 {saldo:.1f}h" 
            return f"🕒 {saldo:.1f}h"
        df["SLA Restante"] = df.apply(calcular_regressiva, axis=1)
        df["Estourado"] = (df["Status"] == "Em Aberto") & (df["Horas Passadas"] > df["SLA_Meta"])

        df["Cliente"] = df["Título Completo"].apply(lambda x: str(x).split("|")[0].strip() if "|" in str(x) else "Cliente Diversos")
        df["Responsável"] = df["ID_Resp"].map(config.EQUIPE).fillna(df["ID_Resp"])
        
        return df
    except Exception as e:
        print(f"Erro API Relatórios: {e}")
        return pd.DataFrame()
