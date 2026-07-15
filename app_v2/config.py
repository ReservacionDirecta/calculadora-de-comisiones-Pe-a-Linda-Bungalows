# config.py - Tema, paleta, CSS global optimizado
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
    if is_dark:
        return {
            "bg": "#0f172a", "bg_card": "#1e293b", "text": "#f1f5f9",
            "text2": "#94a3b8", "border": "#334155", "primary": "#3b82f6",
            "ocean": OCEAN, "sand": SAND, "coral": CORAL, "seafoam": SEAFOAM, "sun": SUN,
        }
    return {
        "bg": "#f8fafc", "bg_card": "#ffffff", "text": "#0f172a",
        "text2": "#64748b", "border": "#e2e8f0", "primary": "#2563eb",
        "ocean": OCEAN, "sand": SAND, "coral": CORAL, "seafoam": SEAFOAM, "sun": SUN,
    }

def inject_css(t):
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
h1, h2, h3, h4, h5, h6 {{ color: {text} !important; }}
.stMarkdown p, .stText p {{ color: {text} !important; }}

/* ─── Sidebar ─── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {{
    background: {bg} !important;
}}
section[data-testid="stSidebar"] .st-emotion-cache-1wrcr25,
section[data-testid="stSidebar"] section[data-testid="stSidebarContent"] {{
    background: {bg} !important;
}}
section[data-testid="stSidebar"] .stCaption {{ color: {text2} !important; }}
section[data-testid="stSidebar"] hr {{ border-color: {border} !important; }}

/* ─── Bento Grid responsive ─── */
.bento-grid {{ 
    display: grid; 
    grid-template-columns: repeat(5, 1fr); 
    gap: 0.6rem; 
    margin: 1rem 0; 
}}
@media (max-width: 1200px) {{ .bento-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 768px) {{ .bento-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 480px) {{ .bento-grid {{ grid-template-columns: 1fr; }} }}
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

/* ─── Alerta ─── */
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

/* ─── Cards ─── */
.shad-card {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}}

/* ─── Tablas ─── */
div[data-testid="stDataFrame"] {{ border: 1px solid {border}; border-radius: 12px; overflow: hidden; }}
.stDataFrame {{ font-size: 0.8rem; }}

/* ─── Ocultar ruido ─── */
[data-testid="stSidebarHeader"], [data-testid="stLogoSpacer"], 
[data-testid="stSidebarCollapseButton"], [data-testid="stNotification"] {{ display: none !important; }}

/* ─── Botones ─── */
.stButton > button[kind="primary"] {{
    background: {t["seafoam"]} !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
}}

/* ─── Navegación horizontal ─── */
div[data-testid="stHorizontalBlock"] > div {{ min-width: 0 !important; }}

/* ─── Móvil: métricas apiladas ─── */
@media (max-width: 768px) {{
    .stMetric {{ padding: 0.5rem !important; }}
    [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; }}
    [data-testid="stHorizontalBlock"] > div {{ flex: 1 1 45% !important; min-width: 45% !important; }}
}}

/* ─── Calculadora receipt ─── */
.calc-card {{
    background: {bg_card};
    border-radius: 16px;
    padding: 24px 32px;
    max-width: 520px;
    margin: 0 auto;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    color: {text};
}}
@media (max-width: 520px) {{
    .calc-card {{ padding: 16px; margin: 0 8px; border-radius: 12px; }}
}}
</style>
""", unsafe_allow_html=True)
