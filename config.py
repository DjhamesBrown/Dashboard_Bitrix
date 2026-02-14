# config.py
import datetime

# ⚠️ SEU WEBHOOK
WEBHOOK_URL = "https://microribrp.bitrix24.com.br/rest/815/aumglyo134ssst28/"

# MAPA DA EQUIPE
EQUIPE = {
    "815": "Djhames Moraes",
    "249": "Luciana Scabini",
    "1729": "Thaísa Castilho",
    "1219": "Ana Beatriz",
    "1": "Admin"
}

# MAPA DE FASES E NOMES
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

# FASES ATIVAS (Para busca no Bitrix)
FASES_ATIVAS = [
    "C8:NEW", "C8:UC_OKYBJK", "C8:UC_O0PER6", 
    "C8:UC_3RMJ6E", "C8:UC_LQG67P", "C8:UC_N5RGUL"
]

# CAMPOS PARA BUSCA
CAMPOS_BITRIX = {
    "ID": "ID",
    "TITLE": "Título Completo",
    "ASSIGNED_BY_ID": "ID_Resp",
    "STAGE_ID": "Fase_Cod",
    "DATE_CREATE": "Data Abertura",
    "DATE_MODIFY": "Data Modificacao", # Adicionado para cálculo de reabertos
    "UF_CRM_1616006980001": "Último Follow-up",
    "UF_CRM_1620908402461": "Classificação"
}