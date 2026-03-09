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
        # Usamos DATE_MODIFY aqui pois um chamado reaberto e fechado hoje terá a data de modificação = hoje
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
        
        # ⚠️ TRATAMENTO DAS DATAS (Incluindo a nova Data de Encerramento)
        # O parâmetro utc=True impede quebras no código caso a data venha vazia
        df["Data Abertura"] = pd.to_datetime(df["Data Abertura"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Modificacao"] = pd.to_datetime(df["Data Modificacao"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        
        if "Data Encerramento" in df.columns:
            df["Data Encerramento"] = pd.to_datetime(df["Data Encerramento"], errors='coerce', utc=True).dt.tz_convert(None) - timedelta(hours=3)
        else:
            df["Data Encerramento"] = pd.NaT

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

# A função calcular_kpis_extras foi mantida, mas não está mais sendo usada no app.py,
# pois nós migramos esse cálculo com as regras exatas de reabertos direto para o app.py na etapa anterior.
def calcular_kpis_extras(df):
    pass
