# styles.py
import streamlit as st

def aplicar_css(tema='dark'):
    # Matriz de cores baseada na probabilidade binária do tema
    bg_color = "#0E1117" if tema == 'dark' else "#F0F2F6"
    card_bg = "#1E1E1E" if tema == 'dark' else "#FFFFFF"
    text_color = "white" if tema == 'dark' else "black"
    border_color = "#333" if tema == 'dark' else "#CCC"
    
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 3.5rem !important; }}
            [data-testid="stHeader"] {{ background-color: rgba(0,0,0,0); }}
            footer {{visibility: hidden;}} 
            .stDeployButton {{display:none;}}
            
            /* Background Geral */
            .stApp {{ background-color: {bg_color}; color: {text_color}; }}
            
            /* KPIs do Operacional */
            div.stButton > button {{
                width: 100%; height: 85px; border-radius: 8px;
                border: 1px solid {border_color}; background-color: {card_bg};
                color: {text_color}; font-size: 15px !important; transition: 0.3s;
            }}
            div.stButton > button:hover {{ transform: scale(1.02); }}
            
            .info-card {{
                background-color: {card_bg}; border: 1px solid {border_color};
                border-radius: 8px; padding: 10px; text-align: center; color: {text_color};
                height: 80px; display: flex; flex-direction: column; justify-content: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
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
    num_cols = 10 # Aumentado para prever novas colunas gerenciais
    sla = str(row.get("SLA Restante", ""))
    fase = str(row.get("Fase Nome", ""))
    if "🚨" in sla: return ['background-color: #521c1c; color: white; font-weight: bold'] * num_cols
    if "Solucionado" in fase: return ['background-color: #0d3311; color: white'] * num_cols
    return [''] * num_cols
