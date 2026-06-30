#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panel de Control v2 — Peña Linda Bungalows
App modular, con vista hotelero/admin y carga de POS.
Corre en puerto separado del original.
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Peña Linda · Panel v2", page_icon="🏝️", layout="wide")

# ─── Imports locales ───
from config import get_theme, inject_css
from data import load_all, calc_kpis
from components import bento_kpi, alert_box, export_buttons, get_yscale

# ─── Sesión: tema ───
if "is_dark" not in st.session_state:
    st.session_state.is_dark = False

def toggle_theme():
    st.session_state.is_dark = not st.session_state.is_dark

t = get_theme(st.session_state.is_dark)

# ─── CSS ───
inject_css(t)

# ─── Carga de datos (cacheada 5 min) ───
df, cobros_df, db_status = load_all()
if df.empty:
    st.error("❌ No se pudieron cargar datos de MongoDB.")
    st.stop()

# ─── Sidebar ───
with st.sidebar:
    st.markdown(f"## 🏝️ Panel v2")
    st.caption(f"Estado: {db_status}")

    st.button("🌙/☀️ Tema", on_click=toggle_theme, use_container_width=True)

    if st.button("🔄 Actualizar datos", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.session_state.ultima_actualizacion = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    if "ultima_actualizacion" in st.session_state:
        st.caption(f"Última: {st.session_state.ultima_actualizacion}")

    # --- Fechas ---
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

    ts = st.multiselect("Métodos de Pago",
                        ["Tarjeta", "Transferencia", "Efectivo", "Otros"],
                        default=["Tarjeta", "Transferencia", "Efectivo"])
    escala_log = st.checkbox("Escala logarítmica")

    st.markdown("---")
    st.caption(f"v2 · {datetime.now().strftime('%d/%m/%Y')}")

# ─── Variable global ───
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")


# ─── Calcular KPIs ───
k = calc_kpis(df, cobros_df, fi, ff, ts)

# ─── HEADER ───
st.markdown(f"""
<div class="shad-header">
    <h1>🏝️ Peña Linda Bungalows</h1>
    <p>Período: {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')} · {db_status}</p>
</div>
""", unsafe_allow_html=True)

from views.exportar import render as r_export

# ─── TABS PRINCIPALES ───
# Orden: primero lo que el hotelero necesita ver
tabs = st.tabs([
    "🧮 Calculadora",
    "🏠 Dashboard",
    "📊 Ventas",
    "💸 Costos",
    "🔄 Conciliar",
    "📤 POS",
    "📋 Historial",
    "📤 Exportar",
])

# ─── TAB 0: Calculadora de Deuda (v3) ───
with tabs[0]:
    from views.calculadora_deuda import render as r_calc
    r_calc(df, k, t, fi, ff, MONGO_URL)

# ─── TAB 1: Dashboard ───
with tabs[1]:
    from views.dashboard import render as r_dash
    r_dash(k, t)

# ─── TAB 2: Ventas ───
with tabs[2]:
    from views.ventas import render as r_ventas
    r_ventas(df, k, t, fi, ff, escala_log)

# ─── TAB 3: Costos ───
with tabs[3]:
    from views.costos import render as r_costos
    r_costos(df, k, t, fi, ff, MONGO_URL)

# ─── TAB 4: Conciliación ───
with tabs[4]:
    from views.conciliacion import render as r_conc
    r_conc(df, k, t, fi, ff, MONGO_URL)

# ─── TAB 5: POS Upload ───
with tabs[5]:
    from views.pos_upload import render as r_pos
    r_pos(MONGO_URL)

# ─── TAB 6: Historial ───
with tabs[6]:
    from views.historial import render as r_hist
    r_hist(df, k, fi, ff, MONGO_URL)

# ─── TAB 7: Exportar ───
with tabs[7]:
    r_export(df, k, fi, ff, df, df)  # last two: sv, sv_date_filtered (same as df for now)
