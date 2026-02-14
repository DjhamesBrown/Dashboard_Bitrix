# data_engine_rel.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import config

@st.cache_data(ttl=300) # Cache de 5 minutos (Gestão não precisa de 60s)
def buscar_dados_historico(data_inicio, data_fim):
    """Motor dedicado para relatórios, busca dados sob demanda com paginação."""
    try:
        # Formata datas para o padrão da API do Bitrix
        inicio_str = data_inicio.strftime("%Y-%m-%d") + "T00:00:00"
        fim_str = data_fim.strftime("%Y-%m-%d") + "T23:59:59"

        todos_dados = []
        
        # Fazemos duas buscas para garantir que pegamos tudo:
        # 1. O que foi CRIADO neste período
        # 2. O que foi MODIFICADO/FECHADO neste período
        filtros_api = [
            {">=DATE_CREATE": inicio_str, "<=DATE_CREATE": fim_str, "CATEGORY_ID": 8},
            {">=DATE_MODIFY": inicio_str, "<=DATE_MODIFY": fim_str, "CATEGORY_ID": 8}
        ]
        
        for filtro in filtros_api:
            start = 0
            while True: # Loop de Paginação (Resolve o problema de limites do Bitrix)
                payload = {
                    "filter": filtro,
                    "select": list(config.CAMPOS_BITRIX.keys()),
                    "start": start
                }
                
                resp = requests.post(f"{config.WEBHOOK_URL}/crm.deal.list", json=payload).json()
                
                if "result" in resp and resp["result"]:
                    todos_dados.extend(resp["result"])
                
                # O Bitrix retorna "next" se houver mais páginas de dados
                if "next" in resp:
                    start = resp["next"]
                else:
                    break # Sai do loop se não houver mais páginas
                    
        df = pd.DataFrame(todos_dados)
        
        if df.empty: return pd.DataFrame()
        
        # Limpeza de duplicatas geradas pela dupla busca
        df.drop_duplicates(subset="ID", inplace=True)
        df.rename(columns=config.CAMPOS_BITRIX, inplace=True)
        
        # --- PROCESSAMENTO (Igual ao Operacional para manter padrão) ---
        df["Fase Nome"] = df["Fase_Cod"].map(config.NOMES_FASES).fillna(df["Fase_Cod"])
        
        df["Data Abertura"] = pd.to_datetime(df["Data Abertura"]).dt.tz_convert(None) - timedelta(hours=3)
        df["Data Modificacao"] = pd.to_datetime(df["Data Modificacao"]).dt.tz_convert(None) - timedelta(hours=3)
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
        print(f"Erro API Relatórios: {e}")
        return pd.DataFrame()