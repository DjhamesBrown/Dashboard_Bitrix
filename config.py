# config.py
import streamlit as st

# 1. SEGURANÇA E CONEXÃO
WEBHOOK_URL = st.secrets["BITRIX_WEBHOOK_URL"]

# Matriz de Autenticação para a Diretoria
CREDENCIAIS = {
    "user": st.secrets.get("DIR_USER", "admin"),
    "password": st.secrets.get("DIR_PASS", "1234")
}

# 2. MAPEAMENTO DA EQUIPE
EQUIPE = {
    "815": "Djhames Moraes", 
    "249": "Luciana Scabini",
    "1729": "Thaísa Castilho", 
    "1219": "Ana Beatriz", 
    "1": "Admin"
}

# 3. MAPEAMENTO DE FASES E STATUS
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

# 4. MAPEAMENTO DE CAMPOS DA API DO BITRIX24 (Com Vetores Confirmados)
CAMPOS_BITRIX = {
    "ID": "ID", 
    "TITLE": "Título Completo", 
    "ASSIGNED_BY_ID": "ID_Resp",
    "STAGE_ID": "Fase_Cod", 
    "DATE_CREATE": "Data Abertura",
    "DATE_MODIFY": "Data Modificacao", 
    "UF_CRM_1616006980001": "Último Follow-up",
    
    # Vetores de Causa-Raiz (Análise de Pareto)
    "UF_CRM_1685489465": "Motivo Abertura",
    "UF_CRM_1636030396": "Motivo Fechamento"
}
