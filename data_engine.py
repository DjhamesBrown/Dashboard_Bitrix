# data_engine.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import config

@st.cache_data(ttl=55)
def buscar_dados():
    try:
        hoje_str = datetime.now().strftime("%Y-%m-%d")

        response_ativos = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={"filter": {"CATEGORY_ID": 8, "STAGE_ID": config.FASES_ATIVAS}, "select": list(config.CAMPOS_BITRIX.keys())}
        )
        lista_ativos = response_ativos.json().get("result", [])
        
        response_criados = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={"filter": {"CATEGORY_ID": 8, ">=DATE_CREATE": f"{hoje_str}T00:00:00"}, "select": list(config.CAMPOS_BITRIX.keys())}
        )
        lista_criados = response_criados.json().get("result", [])

        # Para garantir que vamos pegar qualquer movimentação de hoje, usamos DATE_MODIFY na chamada da API
        response_hoje = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={"filter": {"CATEGORY_ID": 8, ">=DATE_MODIFY": f"{hoje_str}T00:00:00"}, "select": list(config.CAMPOS_BITRIX.keys())}
        )
        lista_hoje = response_hoje.json().get("result", [])
        
        todos_dados = lista_ativos + lista_criados + lista_hoje
        df = pd.DataFrame(todos_dados)
        
        if df.empty: return pd.DataFrame()
        
        df.drop_duplicates(subset="ID", inplace=True)
        df.rename(columns=config.CAMPOS_BITRIX, inplace=True)
        
        df["Fase Nome"] = df["Fase_Cod"].map(config.NOMES_FASES).fillna(df["Fase_Cod"])
        
        # ⚠️ TRATAMENTO DE DATAS E FUSO HORÁRIO
        df["Data Abertura"] = pd.to_datetime(df["Data Abertura"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Modificacao"] = pd.to_datetime(df["Data Modificacao"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Movimentacao"] = pd.to_datetime(df["Data Movimentacao"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Encerramento"] = pd.to_datetime(df["Data Encerramento"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        
        df["Data Formatada"] = df["Data Abertura"].dt.strftime('%d/%m %H:%M')
        
        agora = datetime.now()
        df["Horas Passadas"] = (agora - df["Data Abertura"]).dt.total_seconds() / 3600
        
        def definir_status(row):
            cod = row["Fase_Cod"]
            if cod == "C8:WON": return "Solucionado"
            if cod == "C8:UC_N5RGUL": return "Em Pausa"
            if cod == "C8:LOSE": return "Cancelado"
            return "Em Aberto"
        df["Status"] = df.apply(definir_status, axis=1)

        def definir_meta(cod):
            if cod == "C8:UC_O0PER6": return 2
            if cod == "C8:UC_OKYBJK": return 2
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
        print(f"Erro API: {e}")
        return pd.DataFrame()

def calcular_kpis_extras(df):
    pass
