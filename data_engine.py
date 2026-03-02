# data_engine.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import config

@st.cache_data(ttl=55) # Cache de 55 segundos
def buscar_dados():
    try:
        hoje_str = datetime.now().strftime("%Y-%m-%d")

        # 1. BUSCA ATIVOS
        response_ativos = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={
                "filter": {"CATEGORY_ID": 8, "STAGE_ID": config.FASES_ATIVAS},
                "select": list(config.CAMPOS_BITRIX.keys()),
                "order": {"DATE_CREATE": "ASC"} 
            }
        )
        lista_ativos = response_ativos.json().get("result", [])
        
        # 2. BUSCA CRIADOS HOJE
        response_criados = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={
                "filter": {"CATEGORY_ID": 8, ">=DATE_CREATE": f"{hoje_str}T00:00:00"},
                "select": list(config.CAMPOS_BITRIX.keys())
            }
        )
        lista_criados = response_criados.json().get("result", [])

        # 3. BUSCA SOLUCIONADOS/MODIFICADOS HOJE
        response_hoje = requests.post(
            f"{config.WEBHOOK_URL}/crm.deal.list", 
            json={
                "filter": {"CATEGORY_ID": 8, ">=DATE_MODIFY": f"{hoje_str}T00:00:00"},
                "select": list(config.CAMPOS_BITRIX.keys())
            }
        )
        lista_hoje = response_hoje.json().get("result", [])
        
        # Consolidação
        todos_dados = lista_ativos + lista_criados + lista_hoje
        df = pd.DataFrame(todos_dados)
        
        if df.empty: 
            return pd.DataFrame()
        
        df.drop_duplicates(subset="ID", inplace=True)
        df.rename(columns=config.CAMPOS_BITRIX, inplace=True)
        
        # --- PROCESSAMENTO ---
        df["Fase Nome"] = df["Fase_Cod"].map(config.NOMES_FASES).fillna(df["Fase_Cod"])
        
        # Datas
        df["Data Abertura"] = pd.to_datetime(df["Data Abertura"]).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Modificacao"] = pd.to_datetime(df["Data Modificacao"]).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Formatada"] = df["Data Abertura"].dt.strftime('%d/%m %H:%M')
        
        # Cálculos de Tempo
        agora = datetime.now()
        df["Horas Passadas"] = (agora - df["Data Abertura"]).dt.total_seconds() / 3600
        
        # Lógica de Status
        def definir_status(row):
            cod = row["Fase_Cod"]
            if cod == "C8:WON": return "Solucionado"
            if cod == "C8:UC_N5RGUL": return "Em Pausa"
            if cod == "C8:LOSE": return "Cancelado"
            return "Em Aberto"
        df["Status"] = df.apply(definir_status, axis=1)

        # SLA Meta
        def definir_meta(cod):
            if cod == "C8:UC_O0PER6": return 2    # P1
            if cod == "C8:UC_OKYBJK": return 2    # Triagem
            if cod == "C8:UC_3RMJ6E": return 4    # P2
            if cod == "C8:UC_LQG67P": return 24   # P3
            return 9999
        df["SLA_Meta"] = df["Fase_Cod"].apply(definir_meta)

        # SLA Restante
        def calcular_regressiva(row):
            if row["Status"] != "Em Aberto": return "---"
            saldo = row["SLA_Meta"] - row["Horas Passadas"]
            if saldo < 0: return f"🚨 {saldo:.1f}h" 
            return f"🕒 {saldo:.1f}h"
        df["SLA Restante"] = df.apply(calcular_regressiva, axis=1)
        
        df["Estourado"] = (df["Status"] == "Em Aberto") & (df["Horas Passadas"] > df["SLA_Meta"])

        # Mapeamentos
        df["Cliente"] = df["Título Completo"].apply(lambda x: str(x).split("|")[0].strip() if "|" in str(x) else "Cliente Diversos")
        df["Responsável"] = df["ID_Resp"].map(config.EQUIPE).fillna(df["ID_Resp"])
        
        return df

    except Exception as e:
        print(f"Erro API: {e}")
        return pd.DataFrame()

def calcular_kpis_extras(df):
    """Calcula as porcentagens solicitadas"""
    if df.empty: return 0, 0
    
    hoje = datetime.now().date()
    
    # 1. Eficiência (% Concluído vs Aberto no dia)
    criados_hoje = len(df[df["Data Abertura"].dt.date == hoje])
    solucionados_hoje = len(df[(df["Fase_Cod"] == "C8:WON") & (df["Data Modificacao"].dt.date == hoje)])
    
    taxa_eficiencia = 0
    if criados_hoje > 0:
        taxa_eficiencia = int((solucionados_hoje / criados_hoje) * 100)
    
    # 2. Reabertos/Movimentados (% de chamados antigos mexidos hoje)
    # Lógica: Status Aberto HOJE, mas criado ANTES de hoje e modificado HOJE.
    abertos_ativos = df[(df["Status"] == "Em Aberto")]
    reabertos = len(abertos_ativos[
        (abertos_ativos["Data Abertura"].dt.date < hoje) & 
        (abertos_ativos["Data Modificacao"].dt.date == hoje)
    ])
    
    total_ativos = len(abertos_ativos)
    taxa_reabertura = 0
    if total_ativos > 0:
        taxa_reabertura = int((reabertos / total_ativos) * 100)
        
    return taxa_eficiencia, taxa_reabertura
