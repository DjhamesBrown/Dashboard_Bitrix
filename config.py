# config.py
import streamlit as st

WEBHOOK_URL = st.secrets["BITRIX_WEBHOOK_URL"]

CREDENCIAIS = {
    "diretoria": {"user": st.secrets.get("DIR_USER", "Mcrb"), "pass": st.secrets.get("DIR_PASS", "Mc@2026#$"), "role": "gestor"},
    "suporte": {"user": st.secrets.get("SUP_USER", "999"), "pass": st.secrets.get("SUP_PASS", "2937"), "role": "operador"}
}

EQUIPE = {
    "815": "Djhames Moraes", 
    "249": "Luciana Scabini",
    "1729": "Thaísa Castilho", 
    "1219": "Ana Beatriz", 
    "1": "Admin",
    "20": "Saulo Bevilacqua"
}

NOMES_FASES = {
    "C8:NEW": "Novo 🆕", 
    "C8:UC_OKYBJK": "Triagem 📥",
    "C8:UC_O0PER6": "P1 🔥", 
    "C8:UC_3RMJ6E": "P2 ⚠️",
    "C8:UC_LQG67P": "P3 💤", 
    "C8:UC_N5RGUL": "Em Pausa ⏸️",
    "C8:WON": "Solucionado ✅", 
    "C8:LOSE": "Cancelado ❌"
}

FASES_ATIVAS = [
    "C8:NEW", "C8:UC_OKYBJK", "C8:UC_O0PER6", 
    "C8:UC_3RMJ6E", "C8:UC_LQG67P", "C8:UC_N5RGUL"
]

# ⚠️ ADICIONADO MOVED_TIME E CLOSEDATE
CAMPOS_BITRIX = {
    "ID": "ID", 
    "TITLE": "Título Completo", 
    "ASSIGNED_BY_ID": "ID_Resp",
    "STAGE_ID": "Fase_Cod", 
    "DATE_CREATE": "Data Abertura",
    "DATE_MODIFY": "Data Modificacao",
    "MOVED_TIME": "Data Movimentacao", 
    "CLOSEDATE": "Data Encerramento", 
    "UF_CRM_1616006980001": "Último Follow-up",
    "UF_CRM_1685489465": "Motivo Abertura",
    "UF_CRM_1636030396": "Motivo Fechamento"
}
