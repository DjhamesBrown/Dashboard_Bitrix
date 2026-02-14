# styles.py
import streamlit as st

def aplicar_css():
    st.markdown("""
        <style>
            .block-container { padding-top: 3.5rem !important; }
            [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
            footer {visibility: hidden;} 
            .stDeployButton {display:none;}
            
            /* KPIs do Operacional */
            div.stButton > button {
                width: 100%; height: 85px; border-radius: 8px;
                border: 1px solid #333; background-color: #1E1E1E;
                color: white; font-size: 15px !important;
            }
            .info-card {
                background-color: #0E1117; border: 1px solid #333;
                border-radius: 8px; padding: 10px; text-align: center;
                height: 80px; display: flex; flex-direction: column; justify-content: center;
            }
        </style>
    """, unsafe_allow_html=True)

def card_informativo(titulo, valor, subtitulo="", help_text=""):
    st.markdown(f"""
        <div class="info-card" title="{help_text}">
            <div class="info-title" style="font-size:12px; color:#888;">{titulo}</div>
            <div class="info-value" style="font-size:22px; font-weight:bold;">{valor}</div>
            <div style="font-size: 10px; color: #555;">{subtitulo}</div>
        </div>
    """, unsafe_allow_html=True)

def style_rows(row):
    num_cols = 8
    sla = str(row.get("SLA Restante", ""))
    fase = str(row.get("Fase Nome", ""))
    if "🚨" in sla: return ['background-color: #521c1c; color: white; font-weight: bold'] * num_cols
    if "Solucionado" in fase: return ['background-color: #0d3311; color: white'] * num_cols
    return [''] * num_cols