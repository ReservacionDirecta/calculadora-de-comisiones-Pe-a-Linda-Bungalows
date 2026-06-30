# config.py - Tema, paleta, CSS global
import streamlit as st

# ─── PALETA PEÑA LINDA ───
OCEAN = "#1a3a5c"
SAND = "#f5e6d0"
CORAL = "#e8644a"
SEAFOAM = "#47b881"
SUN = "#f0c040"
WHITE = "#ffffff"
DARK = "#0f172a"
MUTED = "#94a3b8"

def get_theme(is_dark: bool):
    """Devuelve colores según modo oscuro/claro."""
    if is_dark:
        return {
            "bg": "#0f172a",
            "bg_card": "#1e293b",
            "text": "#f1f5f9",
            "text2": "#94a3b8",
            "border": "#334155",
            "primary": "#3b82f6",
            "ocean": OCEAN,
            "sand": SAND,
            "coral": CORAL,
            "seafoam": SEAFOAM,
            "sun": SUN,
        }
    return {
        "bg": "#f8fafc",
        "bg_card": "#ffffff",
        "text": "#0f172a",
        "text2": "#64748b",
        "border": "#e2e8f0",
        "primary": "#2563eb",
        "ocean": OCEAN,
        "sand": SAND,
        "coral": CORAL,
        "seafoam": SEAFOAM,
        "sun": SUN,
    }

def inject_css(t):
    """Inyecta CSS global."""
    bg = t["bg"]
    bg_card = t["bg_card"]
    text = t["text"]
    text2 = t["text2"]
    border = t["border"]

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
.stApp {{ background: {bg}; }}
h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {text}; }}

/* ─── SIDEBAR completo (fondo + todos los widgets) ─── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {{
    background: {bg} !important;
}}
section[data-testid="stSidebar"] .st-emotion-cache-1wrcr25,  /* sidebar content */
section[data-testid="stSidebar"] section[data-testid="stSidebarContent"] {{
    background: {bg} !important;
}}
/* Expander dentro del sidebar */
section[data-testid="stSidebar"] .streamlit-expanderHeader {{
    background: {bg_card} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .streamlit-expanderContent {{
    background: {bg_card} !important;
    border: 1px solid {border} !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 8px 12px !important;
}}
/* Radio buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] {{
    background: transparent !important;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
    background: transparent !important;
    color: {text} !important;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
    background-color: {bg_card} !important;
}}
/* Date input */
section[data-testid="stSidebar"] div[data-baseweb="input"] {{
    background-color: {bg_card} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="input"] input {{
    background-color: {bg_card} !important;
    color: {text} !important;
}}
/* Select / dropdown */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background-color: {bg_card} !important;
    border: 1px solid {border} !important;
}}
/* Multiselect */
section[data-testid="stSidebar"] div[data-baseweb="tag"] {{
    background-color: {t["primary"]}22 !important;
    color: {text} !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background-color: {bg_card} !important;
}}
/* Checkbox */
section[data-testid="stSidebar"] .stCheckbox label {{
    color: {text} !important;
}}
section[data-testid="stSidebar"] .stCheckbox label > div:first-child {{
    background-color: {bg_card} !important;
    border: 1px solid {border} !important;
}}
/* Selectbox */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {{
    background-color: {bg_card} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
}}
/* Buttons in sidebar */
section[data-testid="stSidebar"] .stButton button {{
    background: {bg_card} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
}}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
    background: {t["seafoam"]} !important;
    color: white !important;
}}
/* Caption / muted text */
section[data-testid="stSidebar"] .stCaption, 
section[data-testid="stSidebar"] .st-emotion-cache-1aeihzq {{
    color: {text2} !important;
}}
/* Sidebar hr */
section[data-testid="stSidebar"] hr {{
    border-color: {border} !important;
}}

/* ─── Bento Grid - 5 cards responsive ─── */
.bento-grid {{ 
    display: grid; 
    grid-template-columns: repeat(5, 1fr); 
    gap: 0.6rem; 
    margin: 1rem 0; 
}}
@media (max-width: 768px) {{ .bento-grid {{ grid-template-columns: 1fr 1fr; }} }}
.bento-item {{ 
    background: {bg_card}; 
    border: 1px solid {border}; 
    border-radius: 14px; 
    padding: 1rem 1.2rem; 
    transition: all 0.2s; 
}}
.bento-label {{ font-size: 0.72rem; color: {text2}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }}
.bento-value {{ font-size: 1.5rem; font-weight: 700; line-height: 1.2; margin: 0.2rem 0; }}
.bento-sub {{ font-size: 0.7rem; color: {text2}; }}

/* ─── Alerta / Acción ─── */
.alert-box {{
    background: {bg_card};
    border: 1px solid {border};
    border-left: 4px solid {CORAL};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.75rem 0;
}}
.alert-title {{ font-size: 0.85rem; font-weight: 600; color: {text}; margin-bottom: 0.3rem; }}
.alert-body {{ font-size: 0.8rem; color: {text2}; }}
.alert-action {{ margin-top: 0.5rem; }}

/* ─── Header ─── */
.shad-header {{ 
    background: linear-gradient(135deg, #1e3a5f 0%, {t["primary"]} 50%, #1d4ed8 100%); 
    color: white; 
    padding: 1.2rem 1.5rem; 
    border-radius: 16px; 
    margin-bottom: 1rem;
}}
.shad-header h1 {{ color: white !important; margin: 0; font-size: 1.6rem; }}
.shad-header p {{ color: rgba(255,255,255,0.8) !important; margin: 0.1rem 0 0 0; font-size: 0.85rem; }}

/* ─── Cards de contenido ─── */
.shad-card {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}}

/* ─── Tablas y dataframes ─── */
div[data-testid="stDataFrame"] {{ border: 1px solid {border}; border-radius: 12px; overflow: hidden; }}
.stDataFrame {{ font-size: 0.8rem; }}

/* ─── Ocultar ruido visual ─── */
[data-testid="stSidebarHeader"], [data-testid="stLogoSpacer"], 
[data-testid="stSidebarCollapseButton"], [data-testid="stNotification"] {{ display: none !important; }}

/* ─── Botón de acción principal ─── */
.stButton > button[kind="primary"] {{
    background: {t["seafoam"]} !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
}}
</style>
""", unsafe_allow_html=True)
