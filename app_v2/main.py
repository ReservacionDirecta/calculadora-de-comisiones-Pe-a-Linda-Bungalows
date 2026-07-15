#!/usr/bin/env python3
# Panel de Control v2 — Peña Linda Bungalows
# Optimizado: lazy imports, caching, movil
import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Peña Linda · Panel v2", page_icon="🏝️", layout="wide")

# ─── Imports lazy (solo lo esencial al inicio) ───
from config import get_theme, inject_css
from data import load_all, calc_kpis

# ─── Sesión ───
if "is_dark" not in st.session_state:
    st.session_state.is_dark = False
if "active_page" not in st.session_state:
    st.session_state.active_page = "Calculadora"

def toggle_theme():
    st.session_state.is_dark = not st.session_state.is_dark

t = get_theme(st.session_state.is_dark)
inject_css(t)

# ─── Carga de datos (cacheada) ───
df, cobros_df, db_status = load_all()
if df.empty:
    st.error("No se pudieron cargar datos de MongoDB.")
    st.stop()

# ─── Sidebar compacto ───
with st.sidebar:
    st.markdown("## 🏝️ Panel v2")
    st.caption(f"{db_status}")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.button("🌙/☀️", on_click=toggle_theme, use_container_width=True, key="theme_btn")
    with col_t2:
        if st.button("🔄", use_container_width=True, key="refresh_btn"):
            st.cache_data.clear()
            st.rerun()

    # Fechas
    fecha_min = df["date_pe"].min().date()
    fecha_max = df["date_pe"].max().date()

    with st.expander("📅 Período", expanded=True):
        modo = st.radio("Modo:", ["Rango", "Día", "Semana", "Mes", "Todo"], key="modo", horizontal=True)
        if modo == "Rango":
            r = st.date_input("Fechas:", [fecha_min, fecha_max])
            fi, ff = r if len(r) == 2 else (r[0], r[0])
        elif modo == "Día":
            fi = ff = st.date_input("Fecha:", fecha_max)
        elif modo == "Semana":
            s = st.selectbox("Semana:", sorted(df["sem_key"].unique(), reverse=True))
            fi = df[df["sem_key"] == s]["date_pe"].min().date()
            ff = df[df["sem_key"] == s]["date_pe"].max().date()
        elif modo == "Mes":
            m = st.selectbox("Mes:", sorted(df["mes_label"].unique(), reverse=True))
            fi = df[df["mes_label"] == m]["date_pe"].min().date()
            ff = df[df["mes_label"] == m]["date_pe"].max().date()
        else:
            fi, ff = fecha_min, fecha_max

    ts = st.multiselect("Métodos",
                        ["Tarjeta", "Transferencia", "Efectivo", "Otros"],
                        default=["Tarjeta", "Transferencia", "Efectivo"])

    st.caption(f"v2 · {datetime.now().strftime('%d/%m/%Y')}")

# ─── Variables globales ───
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")
show_usd = st.session_state.get("show_usd", False)
usd_rate = st.session_state.get("usd_rate", 3.6)

# ─── KPIs (calculados por rango) ───
k = calc_kpis(df, cobros_df, fi, ff, ts)

# ─── Header ───
st.markdown(f"""
<div class="shad-header">
    <h1>🏝️ Peña Linda Bungalows</h1>
    <p>{fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}</p>
</div>
""", unsafe_allow_html=True)

# ─── Navegación (preserva pestaña) ───
page_options = {
    "🧮 Calculadora": "Calculadora",
    "🏠 Dashboard": "Dashboard",
    "📊 Ventas": "Ventas",
    "💸 Costos": "Costos",
    "🔄 Conciliar": "Conciliar",
    "📤 POS": "POS",
    "📋 Historial": "Historial",
    "📤 Exportar": "Exportar",
    "🤖 Agente": "Agente",
}

current_idx = list(page_options.values()).index(st.session_state.active_page) if st.session_state.active_page in page_options.values() else 0

selected = st.radio(
    "Nav:", list(page_options.keys()),
    index=current_idx, horizontal=True,
    key="nav_radio", label_visibility="collapsed",
)

new_page = page_options[selected]
if new_page != st.session_state.active_page:
    st.session_state.active_page = new_page

# ─── Lazy render por página ───
page = st.session_state.active_page

if page == "Calculadora":
    from views.calculadora_deuda import render as r
    r(df, k, t, fi, ff, MONGO_URL)
elif page == "Dashboard":
    from views.dashboard import render as r
    r(k, t)
elif page == "Ventas":
    from views.ventas import render as r
    r(df, k, t, fi, ff, st.session_state.get("escala_log", False))
elif page == "Costos":
    from views.costos import render as r
    r(df, k, t, fi, ff, MONGO_URL)
elif page == "Conciliar":
    from views.conciliacion import render as r
    r(df, k, t, fi, ff, MONGO_URL)
elif page == "POS":
    from views.pos_upload import render as r
    r(MONGO_URL)
elif page == "Historial":
    from views.historial import render as r
    r(df, k, fi, ff, MONGO_URL)
elif page == "Exportar":
    from views.exportar import render as r
    r(df, k, fi, ff, sv=df, sv_date_filtered=k["df_f"])
elif page == "Agente":
    from views.agente import render as r
    r(df, k, t, fi, ff, MONGO_URL)
