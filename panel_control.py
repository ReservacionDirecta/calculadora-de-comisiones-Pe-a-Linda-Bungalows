#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panel de Control — Peña Linda Bungalows
Diseño Shadcn/Premium + Tema Claro/Oscuro + Corrección de Costos y Saldos
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient
from reportlab.lib import colors as rc
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm
import os, sys, warnings, hashlib, io

warnings.filterwarnings('ignore')
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Conexión a MongoDB (local / Railway)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")

st.set_page_config(page_title="Peña Linda — Panel de Control", layout="wide", page_icon="🏝️")

# ═══ TEMA ═══
if 'theme' not in st.session_state: 
    st.session_state.theme = 'light'

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

is_dark = st.session_state.theme == 'dark'
bg = '#0f0f0f' if is_dark else '#fafafa'
bg_card = '#1a1a1a' if is_dark else '#ffffff'
text = '#fafafa' if is_dark else '#0f0f0f'
text2 = '#a1a1aa' if is_dark else '#71717a'
border = '#27272a' if is_dark else '#e4e4e7'
primary = '#3b82f6'
primary_bg = '#1e3a5f' if is_dark else '#eff6ff'

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* {{ font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{ background: {bg}; }}
h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {text}; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ 
    background: {'#111' if is_dark else '#f8f9fa'} !important; 
    border-right: 1px solid {border}; 
}}
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{
    padding-top: 3.5rem !important;
}}

/* Dataframe */
div[data-testid="stDataFrame"] {{ border: 1px solid {border}; border-radius: 12px; overflow: hidden; }}
.stDataFrame {{ font-size: 0.85rem; }}

/* Ocultar elementos predeterminados molestos */
[data-testid="stSidebarHeader"], [data-testid="stLogoSpacer"], 
[data-testid="stSidebarCollapseButton"], [data-testid="stNotification"] {{ display: none !important; }}

/* Expanders */
details summary {{ color: {text} !important; font-weight: 600 !important; font-size: 0.9rem !important; }}
details summary * {{ color: {text} !important; fill: {text} !important; }}
summary::marker {{ color: {text} !important; }}

/* Bento Grid */
.bento-grid {{ 
    display: grid; 
    grid-template-columns: repeat(4, 1fr); 
    gap: 0.75rem; 
    margin: 1rem 0; 
}}
@media (max-width: 768px) {{
    .bento-grid {{ grid-template-columns: 1fr; }}
}}
.bento-item {{ 
    background: {bg_card}; 
    border: 1px solid {border}; 
    border-radius: 14px; 
    padding: 1.2rem; 
    display: flex; 
    flex-direction: column; 
    justify-content: center;
    transition: all 0.2s; 
}}
.bento-label {{ font-size: 0.85rem; color: {text2}; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
.bento-value {{ font-size: 1.8rem; font-weight: 700; line-height: 1.2; margin: 0.25rem 0; }}
.bento-sub {{ font-size: 0.78rem; color: {text2}; margin-top: 0.1rem; }}

/* Header */
.shad-header {{ 
    background: linear-gradient(135deg, #1e3a5f 0%, {primary} 50%, #1d4ed8 100%); 
    color: white; 
    padding: 1.5rem 2rem; 
    border-radius: 16px; 
    margin-bottom: 1.5rem;
}}
.shad-header h1 {{ color: white !important; margin: 0; }}
.shad-header p {{ color: rgba(255,255,255,0.8) !important; margin: 0.2rem 0 0 0; }}

/* Card layout */
.shad-card {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}}
</style>
""", unsafe_allow_html=True)


# --- AUTOMATED DATABASE SEEDING ---
try:
    from bson import json_util
    cli_seed = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
    db_seed = cli_seed.get_database()
    if 'pagos' not in db_seed.list_collection_names() or db_seed['pagos'].count_documents({}) == 0:
        seed_path = os.path.join(CARPETA, 'data', 'seed_db.json')
        if os.path.exists(seed_path):
            with open(seed_path, 'r', encoding='utf-8') as f:
                docs_seed = json_util.loads(f.read())
            if docs_seed:
                db_seed['pagos'].insert_many(docs_seed)
                db_seed['pagos'].create_index('hash', unique=True)
    cli_seed.close()
except Exception as e:
    pass

# ═══ CARGA DE DATOS ═══
@st.cache_data(ttl=300)
def load_data():
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        cli.admin.command('ping')
        docs = list(cli['pena_linda']['pagos'].find({}, {'hash':0}))
        cli.close()
        if not docs: raise Exception("Base de datos vacía")
        df = pd.DataFrame(docs)
        df['date'] = pd.to_datetime(df['fecha'], errors='coerce')
        
        is_cost_or_abono = df['tipo_pago'].isin(['Costo', 'Abono']) | df['fuente'].isin(['Abono Chamba', 'Saldo Base'])
        df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')
        df.loc[is_cost_or_abono, 'date_pe'] = df.loc[is_cost_or_abono, 'date'].dt.tz_localize('America/Lima', ambiguous='NaT')
        
        df['amount'] = pd.to_numeric(df['monto'], errors='coerce')
        df = df.dropna(subset=['date_pe']).sort_values('date_pe').reset_index(drop=True)
        df['sem_key'] = df['date_pe'].dt.strftime('%Y-S%V')
        df['mes_label'] = df['date_pe'].dt.strftime('%Y-%m')
        df['tipo_pago'] = df['tipo_pago'].fillna('Otros')
        df['es_link'] = df['es_link'].fillna(False)
        df['method'] = df['metodo'].fillna('')
        if 'referencia' in df.columns:
            df['referencia'] = df['referencia'].fillna('')
        elif 'reference' in df.columns:
            df['referencia'] = df['reference'].fillna('')
        elif 'transaction_id' in df.columns:
            df['referencia'] = df['transaction_id'].fillna('')
        else:
            df['referencia'] = ''
        return df, f"MongoDB ({len(df):,} docs)"
    except Exception as e:
        return pd.DataFrame(), f"Error conexión: {e}"

sv, db_status = load_data()
if sv.empty: 
    st.error("No se pudo cargar ningún dato de MongoDB.")
    st.stop()

# Helper fechas
fecha_min, fecha_max = sv['date_pe'].min().date(), sv['date_pe'].max().date()

# ═══ SIDEBAR ═══
with st.sidebar:
    st.button("🌙/☀️ Toggle Theme", on_click=toggle_theme, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 🔄 Botón de actualización de datos
    if st.button("🔄 Actualizar datos", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.session_state.ultima_actualizacion = datetime.now()
        st.rerun()
    
    if 'ultima_actualizacion' in st.session_state:
        st.caption(f"Última actualización: {st.session_state.ultima_actualizacion.strftime('%H:%M:%S')}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📅 Período de Consulta", expanded=True):
        modo = st.radio("Modalidad:", ['Rango','Día','Semana','Mes','Todo'], key="modo")
        if modo == 'Rango':
            r = st.date_input("Fechas:", [fecha_min, fecha_max])
            fi, ff = r if len(r)==2 else (r[0], r[0])
        elif modo == 'Día':
            fi = ff = st.date_input("Fecha:", fecha_max)
        elif modo == 'Semana':
            s = st.selectbox("Semana:", sorted(sv['sem_key'].unique(), reverse=True))
            fi = sv[sv['sem_key']==s]['date_pe'].min().date()
            ff = sv[sv['sem_key']==s]['date_pe'].max().date()
        elif modo == 'Mes':
            m = st.selectbox("Mes:", sorted(sv['mes_label'].unique(), reverse=True))
            fi = sv[sv['mes_label']==m]['date_pe'].min().date()
            ff = sv[sv['mes_label']==m]['date_pe'].max().date()
        else:
            fi, ff = fecha_min, fecha_max
            
    ts = st.multiselect("Métodos de Pago (Ventas)", ['Tarjeta','Transferencia','Efectivo','Otros'], default=['Tarjeta','Transferencia','Efectivo'])
    escala_log = st.checkbox("Escala logarítmica (Gráficos)")

# ═══ FILTRADO DE DATOS ═══
# Ventas e ingresos en el periodo filtrado
sv_date_filtered = sv[(sv['date_pe'].dt.date >= fi) & (sv['date_pe'].dt.date <= ff)]
is_sale = ~sv_date_filtered['tipo_pago'].isin(['Costo']) & ~sv_date_filtered['fuente'].isin(['Abono Chamba', 'Saldo Base'])
sv_sales_f = sv_date_filtered[is_sale & sv_date_filtered['tipo_pago'].isin(ts)]
sv_sales_sirvoy = sv_sales_f[sv_sales_f['fuente']=='Sirvoy']

tb_sirvoy = float(sv_sales_sirvoy['amount'].sum())
tb_plataformas = float(sv_sales_f[sv_sales_f['fuente'].isin(['Izipay','Culqi','Openpay'])]['amount'].sum())
sv_transf_efect = sv_sales_sirvoy[sv_sales_sirvoy['tipo_pago'].isin(['Transferencia','Efectivo'])]['amount'].sum()
tb_recibido = tb_plataformas + float(sv_transf_efect)

# Links en periodo
la = sv_date_filtered[sv_date_filtered['es_link']].copy()
# Determinar estado
if 'estado_deposito' not in la.columns:
    la['estado_deposito'] = la['date'].apply(lambda d: 'pendiente' if d >= pd.Timestamp('2026-06-22') else 'depositado')
else:
    la['estado_deposito'] = la['estado_deposito'].fillna('depositado')

pendientes_link = la[la['estado_deposito']=='pendiente']
total_ret = float(pendientes_link['amount'].sum())

# Links en sirvoy para contraste de tarjeta
lk = max(0.0, float(sv_sales_sirvoy[sv_sales_sirvoy['tipo_pago']=='Tarjeta']['amount'].sum()) - tb_plataformas)

# Comisión Chamba Digital del periodo (5% sobre bruto de Sirvoy)
comision = tb_sirvoy * 0.05

# Costos operativos en el periodo (excluyendo el Saldo Base para sumas de periodos)
costos = sv_date_filtered[sv_date_filtered['tipo_pago']=='Costo']
total_costos = float(costos[costos['fuente'] != 'Saldo Base']['amount'].sum())
costo_fb = float(costos[costos['fuente']=='Costo FB Ads']['amount'].sum())
costo_sv = float(costos[costos['fuente']=='Costo Sirvoy']['amount'].sum())
costo_as = float(costos[costos['fuente']=='Costo Asistente']['amount'].sum())
costo_saldo = float(costos[costos['fuente']=='Saldo Base']['amount'].sum())

# Ticket promedio y conteo de transacciones
prom = float(sv_sales_sirvoy['amount'].mean()) if not sv_sales_sirvoy.empty else 0.0
tx = len(sv_sales_sirvoy)

# ═══ CÁLCULOS ACUMULADOS DE DEUDA (DESDE 03/03/2026) ═══
fecha_base = pd.Timestamp("2026-03-03").date()
sv_desde_mar = sv[(sv['date_pe'].dt.date >= fecha_base) & (sv['fuente']=='Sirvoy')]
comision_desde_mar = float(sv_desde_mar['amount'].sum() * 0.05)

costos_desde_mar = sv[(sv['date_pe'].dt.date >= fecha_base) & (sv['tipo_pago']=='Costo')]
# Excluimos 'Saldo Base' para evitar sumarlo dos veces, ya que se agrega como constante de 9654.83
adeudado = comision + total_costos

# Pagos recibidos de Peña Linda (abonos a deuda) - desde tabla cobros
try:
    cli_aux = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    # Filtrar por fecha del sidebar (fi, ff)
    cobros_data = list(cli_aux['pena_linda']['cobros'].find({
        'fecha': {'$gte': pd.Timestamp(fi), '$lte': pd.Timestamp(ff) + pd.Timedelta(days=1)}
    }))
    cli_aux.close()
    total_abonos = sum(c['monto'] for c in cobros_data if c.get('tipo') == 'abono')
    total_comision = sum(c['monto'] for c in cobros_data if c.get('tipo') == 'comision')
    total_costos_cobros = sum(c['monto'] for c in cobros_data if c.get('tipo') in ['costo','saldo_inicial'])
    adeudado = total_comision + total_costos_cobros
    saldo_pendiente = max(0, adeudado - total_abonos)
except:
    pagos_recibidos = sv[sv['fuente']=='Abono Chamba']
    total_abonos = float(pagos_recibidos['amount'].sum()) if not pagos_recibidos.empty else 0
    saldo_pendiente = max(0, adeudado - total_abonos)

# Asegurar que pagos_recibidos siempre este definido (filtrado por fecha)
if 'pagos_recibidos' not in dir() or pagos_recibidos is None:
    pagos_recibidos = sv[(sv['fuente']=='Abono Chamba') & (sv['date_pe'].dt.date >= fi) & (sv['date_pe'].dt.date <= ff)]

# ═══ HEADER PRINCIPAL ═══
st.markdown(f"""
<div class="shad-header">
    <h1>Peña Linda Bungalows 🏝️</h1>
    <p>Período: {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')} | Estado de Conexión: {db_status}</p>
</div>
""", unsafe_allow_html=True)

# ═══ BENTO GRID KPI ═══
st.markdown(f"""
<div class="bento-grid">
    <div class="bento-item" style="border-top:3px solid #3b82f6;">
        <div class="bento-label">📈 Ventas Sirvoy (Bruto)</div>
        <div class="bento-value" style="color:#3b82f6;">S/ {tb_sirvoy:,.2f}</div>
        <div class="bento-sub">{tx} transacciones en Sirvoy</div>
    </div>
    <div class="bento-item" style="border-top:3px solid #10b981;">
        <div class="bento-label">✅ Recibido Confirmado</div>
        <div class="bento-value" style="color:#10b981;">S/ {tb_recibido:,.2f}</div>
        <div class="bento-sub">Plataformas + Transf. / Efectivo</div>
    </div>
    <div class="bento-item" style="border-top:3px solid #f97316;">
        <div class="bento-label">💸 Costos Operativos</div>
        <div class="bento-value" style="color:#f97316;">S/ {total_costos:,.2f}</div>
        <div class="bento-sub">FB Ads S/ {costo_fb:,.0f} · Sirvoy S/ {costo_sv:,.0f} · Asistente S/ {costo_as:,.0f}</div>
    </div>
    <div class="bento-item" style="border-top:3px solid #ef4444;">
        <div class="bento-label">💰 Saldo Pendiente CD</div>
        <div class="bento-value" style="color:#ef4444;">S/ {saldo_pendiente:,.2f}</div>
        <div class="bento-sub">Deuda histórica acumulada</div>
    </div>
    <div class="bento-item" style="border-top:3px solid #8b5cf6;">
        <div class="bento-label">📊 Comisión Acumulada (desde 03/03)</div>
        <div class="bento-value" style="color:#8b5cf6;">S/ {comision_desde_mar:,.2f}</div>
        <div class="bento-sub">5% sobre ventas Sirvoy históricas</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Helper yscale
def get_yscale():
    return dict(type="log") if escala_log else {}

# ═══ MÓDULOS DEL DASHBOARD (TABS PRINCIPALES) ═══
tabs = st.tabs([
    "📊 Ventas Generadas", 
    "💸 Costos Operativos", 
    "🔄 Conciliación de Pagos",
    "📋 Historial y Conciliación",
    "📤 Exportar y Reportes"
])

# ================= HELPER: Exportar a CSV/Excel =================
def df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def df_to_excel(df):
    output = io.BytesIO()
    # Remove timezone info from datetime columns (Excel doesn't support tz-aware datetimes)
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            if df_clean[col].dt.tz is not None:
                df_clean[col] = df_clean[col].dt.tz_localize(None)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Reporte')
    return output.getvalue()

# ================= TAB 1: VENTAS GENERADAS =================
with tabs[0]:
    v_tab1, v_tab2, v_tab3 = st.tabs(["📈 Resumen y Gráficos", "📄 Detalle de Transacciones", "💰 Comisiones CD (5%)"])
    
    with v_tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="shad-card"><h3>📈 Ventas Diarias</h3>', unsafe_allow_html=True)
            if not sv_sales_f.empty:
                d = sv_sales_f.set_index('date').resample('D')['amount'].sum().reset_index()
                fig = px.bar(d, x='date', y='amount', color_discrete_sequence=['#3b82f6'], labels={'date':'Fecha','amount':'S/'})
                fig.update_layout(height=320, margin=dict(l=10,r=10,t=10,b=10), showlegend=False, plot_bgcolor=bg, paper_bgcolor=bg_card, font_color=text)
                fig.update_yaxes(tickprefix="S/ ", **get_yscale())
                fig.update_xaxes(gridcolor=border)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin ventas en el período")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<div class="shad-card"><h3>🥧 Distribución de Métodos</h3>', unsafe_allow_html=True)
            if not sv_sales_f.empty:
                pt = sv_sales_f.groupby('tipo_pago')['amount'].sum().reset_index()
                cmap = {'Tarjeta':'#3b82f6','Transferencia':'#10b981','Efectivo':'#f59e0b','Otros':'#a1a1aa'}
                fig = px.pie(pt, values='amount', names='tipo_pago', color='tipo_pago', color_discrete_map=cmap)
                fig.update_traces(textposition='inside', textinfo='label+percent', marker=dict(line=dict(color=bg_card, width=2)))
                fig.update_layout(height=320, margin=dict(l=10,r=10,t=10,b=10), plot_bgcolor=bg, paper_bgcolor=bg_card, font_color=text)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin ventas en el período")
            st.markdown('</div>', unsafe_allow_html=True)
            
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="shad-card"><h3>📊 Top 10 Métodos de Pago</h3>', unsafe_allow_html=True)
            if not sv_sales_f.empty:
                met = sv_sales_f.groupby('method')['amount'].sum().sort_values(ascending=False).head(10).reset_index()
                fig = px.bar(met, x='amount', y='method', orientation='h', color='amount', color_continuous_scale='Blues', labels={'amount':'S/','method':''})
                fig.update_layout(height=350, margin=dict(l=10,r=10,t=10,b=10), showlegend=False, plot_bgcolor=bg, paper_bgcolor=bg_card, font_color=text)
                fig.update_xaxes(tickprefix="S/ ", **get_yscale())
                fig.update_yaxes(gridcolor=border)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin transacciones")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c4:
            st.markdown('<div class="shad-card"><h3>💳 Ticket Promedio y Transacciones</h3>', unsafe_allow_html=True)
            st.markdown(f"""
            - **Ticket Promedio Sirvoy**: S/ {prom:,.2f}
            - **Número de Reservas/Ventas**: {tx}
            - **Mayor Venta Registrada**: S/ {sv_sales_sirvoy['amount'].max() if not sv_sales_sirvoy.empty else 0:,.2f}
            - **Menor Venta Registrada**: S/ {sv_sales_sirvoy['amount'].min() if not sv_sales_sirvoy.empty else 0:,.2f}
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            
    with v_tab2:
        st.markdown("### 📄 Transacciones del Periodo")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search = st.text_input("🔍 Buscar por método, comentario o ID", "", placeholder="Ej: VISA, transferencia, link...")
        with col_f2:
            solo_lk = st.checkbox("Solo Link de Pago (Tarjetas)", False)
            
        det = sv_sales_f.copy()
        if solo_lk:
            det = det[det['es_link'] == True]
        if search:
            det = det[det['method'].str.contains(search, case=False, na=False) | 
                      det['referencia'].astype(str).str.contains(search, case=False, na=False) |
                      det['metodo'].astype(str).str.contains(search, case=False, na=False)]
                      
        st.markdown(f"**Total en Vista:** {len(det)} registros | **Monto total:** S/ {det['amount'].sum():,.2f}")
        
        # 📤 Botones de exportación
        exp_c1, exp_c2 = st.columns(2)
        with exp_c1:
            st.download_button(
                "📥 Descargar CSV (Transacciones filtradas)",
                data=df_to_csv(det),
                file_name=f"transacciones_{fi}_{ff}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with exp_c2:
            st.download_button(
                "📥 Descargar Excel (Transacciones filtradas)",
                data=df_to_excel(det),
                file_name=f"transacciones_{fi}_{ff}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # Paginador
        limit = st.selectbox("Filas por página", [25, 50, 100], index=0)
        total_p = max(1, (len(det) + limit - 1) // limit)
        if 'v_page' not in st.session_state: st.session_state.v_page = 0
        if st.session_state.v_page >= total_p: st.session_state.v_page = 0
        
        col_n1, col_n2, col_n3 = st.columns([1,3,1])
        with col_n1:
            if st.button("◀ Ant", disabled=(st.session_state.v_page==0), key="v_ant"):
                st.session_state.v_page = max(0, st.session_state.v_page - 1)
        with col_n2:
            st.markdown(f"<div style='text-align:center;padding:5px;'>Página {st.session_state.v_page+1} de {total_p}</div>", unsafe_allow_html=True)
        with col_n3:
            if st.button("Sig ▶", disabled=(st.session_state.v_page>=total_p-1), key="v_sig"):
                st.session_state.v_page = min(total_p-1, st.session_state.v_page + 1)
                
        start_idx = st.session_state.v_page * limit
        end_idx = min(start_idx + limit, len(det))
        page_df = det.iloc[start_idx:end_idx].copy()
        
        if not page_df.empty:
            page_df['Fecha'] = page_df['date_pe'].dt.strftime('%d/%m/%Y %H:%M')
            page_df['Monto'] = page_df['amount'].apply(lambda x: f"S/ {x:,.2f}")
            page_df['Tipo'] = page_df['tipo_pago']
            page_df['Método'] = page_df['method']
            page_df['Origen'] = page_df['fuente']
            page_df['Es Link'] = page_df['es_link'].apply(lambda x: "Sí 🚫" if x else "No")
            page_df['estado'] = page_df['estado_deposito'].fillna('—') if 'estado_deposito' in page_df.columns else '—'
            
            st.data_editor(
                page_df[['Fecha', 'Origen', 'Monto', 'Tipo', 'Método', 'Es Link', 'referencia', 'estado']].rename(
                    columns={'estado': 'Estado'}),
                column_config={
                    'Método': st.column_config.TextColumn(disabled=True),
                    'Monto': st.column_config.TextColumn(disabled=True),
                    'Estado': st.column_config.SelectboxColumn(
                        options=['depositado', 'pendiente', 'revisado'],
                        help="Estado del depósito"
                    ),
                    'referencia': st.column_config.TextColumn('Referencia', help="Editar referencia")
                },
                hide_index=True, use_container_width=True, key=f"editor_det_{st.session_state.v_page}"
            )
        else:
            st.info("Sin registros para mostrar con los filtros actuales")

    with v_tab3:
        st.markdown("### 💰 Comisiones Chamba Digital (5%)")
        st.write("Cálculo y detalle de la comisión del 5% sobre las ventas brutas registradas en Sirvoy.")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.metric("Ventas Sirvoy (Periodo)", f"S/ {tb_sirvoy:,.2f}")
        with col_c2:
            st.metric("Comisión Generada (Periodo)", f"S/ {comision:,.2f}")
        with col_c3:
            st.metric("Comisión Acumulada Histórica (desde 03/03)", f"S/ {comision_desde_mar:,.2f}")
            
        st.markdown("---")
        
        # 📊 GRÁFICOS DE COMISIÓN - Vistas Diaria/Semanal/Mensual/Anual
        st.markdown("#### 📈 Evolución de Comisión (5% sobre Sirvoy)")
        com_vista = st.radio(
            "Vista:",
            ["📅 Diaria", "📆 Semanal", "📊 Mensual", "📈 Anual"],
            horizontal=True,
            key="comision_vista"
        )
        
        if not sv_sales_sirvoy.empty:
            sv_com = sv_sales_sirvoy.copy()
            sv_com['Comisión'] = sv_com['amount'] * 0.05
            
            if com_vista == "📅 Diaria":
                com_grp = sv_com.set_index('date_pe').resample('D')['Comisión'].sum().reset_index()
                com_grp.columns = ['Fecha', 'Comisión']
                x_col = 'Fecha'
            elif com_vista == "📆 Semanal":
                sv_com['sem_key'] = sv_com['date_pe'].dt.strftime('%Y-W%U')
                com_grp = sv_com.groupby('sem_key')['Comisión'].sum().reset_index()
                com_grp.columns = ['Semana', 'Comisión']
                x_col = 'Semana'
            elif com_vista == "📊 Mensual":
                sv_com['mes_key'] = sv_com['date_pe'].dt.strftime('%Y-%m')
                com_grp = sv_com.groupby('mes_key')['Comisión'].sum().reset_index()
                com_grp.columns = ['Mes', 'Comisión']
                x_col = 'Mes'
            else:  # Anual
                sv_com['año_key'] = sv_com['date_pe'].dt.strftime('%Y')
                com_grp = sv_com.groupby('año_key')['Comisión'].sum().reset_index()
                com_grp.columns = ['Año', 'Comisión']
                x_col = 'Año'
            
            fig_com = px.bar(
                com_grp, x=x_col, y='Comisión',
                color_discrete_sequence=['#3b82f6'],
                labels={x_col: com_vista.replace('📅 ', '').replace('📆 ', '').replace('📊 ', '').replace('📈 ', ''), 'Comisión': 'Comisión (S/)'}
            )
            fig_com.update_layout(
                height=350, margin=dict(l=10,r=10,t=30,b=10),
                plot_bgcolor=bg, paper_bgcolor=bg_card, font_color=text,
                title=f"Comisión 5% - {com_vista}"
            )
            fig_com.update_yaxes(tickprefix="S/ ", gridcolor=border, **get_yscale())
            fig_com.update_xaxes(gridcolor=border)
            st.plotly_chart(fig_com, use_container_width=True)
            
            # Métricas resumen
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                st.metric(f"Total {com_vista.split()[1]}", f"S/ {com_grp['Comisión'].sum():,.2f}")
            with c_m2:
                st.metric("Promedio", f"S/ {com_grp['Comisión'].mean():,.2f}")
            with c_m3:
                st.metric("Máximo", f"S/ {com_grp['Comisión'].max():,.2f}")
        else:
            st.info("Sin ventas Sirvoy en el período para mostrar evolución de comisión.")
        
        st.markdown("---")
        st.markdown("#### 📋 Detalle de Comisiones por Transacción")
        
        # Filtro de comisiones
        sv_sirvoy_c = sv_sales_sirvoy.copy()
        if not sv_sirvoy_c.empty:
            sv_sirvoy_c['Comisión 5%'] = sv_sirvoy_c['amount'] * 0.05
            
            # Buscador específico de comisiones
            search_c = st.text_input("Buscar transacción de comisión:", "", placeholder="Ej: comprador, ID, método...", key="search_comisiones")
            if search_c:
                sv_sirvoy_c = sv_sirvoy_c[
                    sv_sirvoy_c['metodo'].astype(str).str.contains(search_c, case=False, na=False) |
                    sv_sirvoy_c['transaction_id'].astype(str).str.contains(search_c, case=False, na=False) |
                    (sv_sirvoy_c['comprador'].astype(str).str.contains(search_c, case=False, na=False) if 'comprador' in sv_sirvoy_c.columns else False)
                ]
            
            st.markdown(f"**Ventas en Vista:** {len(sv_sirvoy_c)} transacciones | **Comisión Total en Vista:** S/ {sv_sirvoy_c['Comisión 5%'].sum():,.2f}")
            
            # Paginador para comisiones
            limit_c = st.selectbox("Filas por página (Comisiones)", [25, 50, 100], index=0, key="limit_c")
            total_pc = max(1, (len(sv_sirvoy_c) + limit_c - 1) // limit_c)
            if 'c_page' not in st.session_state: st.session_state.c_page = 0
            if st.session_state.c_page >= total_pc: st.session_state.c_page = 0
            
            col_nc1, col_nc2, col_nc3 = st.columns([1,3,1])
            with col_nc1:
                if st.button("◀ Ant", disabled=(st.session_state.c_page==0), key="c_ant"):
                    st.session_state.c_page = max(0, st.session_state.c_page - 1)
            with col_nc2:
                st.markdown(f"<div style='text-align:center;padding:5px;'>Página {st.session_state.c_page+1} de {total_pc}</div>", unsafe_allow_html=True)
            with col_nc3:
                if st.button("Sig ▶", disabled=(st.session_state.c_page>=total_pc-1), key="c_sig"):
                    st.session_state.c_page = min(total_pc-1, st.session_state.c_page + 1)
                    
            start_idx = st.session_state.c_page * limit_c
            end_idx = min(start_idx + limit_c, len(sv_sirvoy_c))
            page_c_df = sv_sirvoy_c.iloc[start_idx:end_idx].copy()
            
            if not page_c_df.empty:
                page_c_df['Fecha'] = page_c_df['date_pe'].dt.strftime('%d/%m/%Y %H:%M')
                page_c_df['Bruto (S/)'] = page_c_df['amount'].apply(lambda x: f"S/ {x:,.2f}")
                page_c_df['Comisión 5% (S/)'] = page_c_df['Comisión 5%'].apply(lambda x: f"S/ {x:,.2f}")
                page_c_df['Cliente'] = page_c_df['comprador'] if 'comprador' in page_c_df.columns else 'Cliente Sirvoy'
                page_c_df['Cliente'] = page_c_df['Cliente'].fillna('Cliente Sirvoy')
                
                st.dataframe(page_c_df[['Fecha', 'transaction_id', 'Cliente', 'metodo', 'Bruto (S/)', 'Comisión 5% (S/)']].rename(
                    columns={'transaction_id': 'ID Pago', 'metodo': 'Método / Detalle'}
                ), hide_index=True, use_container_width=True)
            else:
                st.info("Sin registros en este sub-rango")
        else:
            st.info("No hay ventas registradas en Sirvoy para calcular comisiones en este período.")

# ================= TAB 2: COSTOS OPERATIVOS =================
with tabs[1]:
    c_tab1, c_tab2, c_tab3 = st.tabs(["📋 Detalle de Costos", "➕ Registrar Costo Extra", "🔧 Costos Extra"])
    
    with c_tab1:
        # Mostramos los costos sin filtro por método de pago de venta (ts)
        costos_df = sv_date_filtered[sv_date_filtered['tipo_pago']=='Costo'].copy()
        # Excluimos Saldo Base de las métricas visuales del periodo
        costos_periodo = costos_df[costos_df['fuente'] != 'Saldo Base']
        
        st.markdown("### 📋 Desglose de Costos del Periodo")
        
        col_cm1, col_cm2, col_cm3, col_cm4 = st.columns(4)
        with col_cm1:
            st.metric("📱 Facebook Ads", f"S/ {costos_periodo[costos_periodo['fuente']=='Costo FB Ads']['amount'].sum():,.2f}")
        with col_cm2:
            st.metric("🖥️ Sirvoy Software", f"S/ {costos_periodo[costos_periodo['fuente']=='Costo Sirvoy']['amount'].sum():,.2f}")
        with col_cm3:
            st.metric("👤 Asistente Comercial", f"S/ {costos_periodo[costos_periodo['fuente']=='Costo Asistente']['amount'].sum():,.2f}")
        with col_cm4:
            st.metric("📊 Total Costos", f"S/ {costos_periodo['amount'].sum():,.2f}")
            
        # 📤 Botones de exportación Costos
        exp_cc1, exp_cc2 = st.columns(2)
        with exp_cc1:
            st.download_button(
                "📥 Descargar CSV (Costos filtrados)",
                data=df_to_csv(costos_periodo),
                file_name=f"costos_{fi}_{ff}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with exp_cc2:
            st.download_button(
                "📥 Descargar Excel (Costos filtrados)",
                data=df_to_excel(costos_periodo),
                file_name=f"costos_{fi}_{ff}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        
        if not costos_periodo.empty:
            df_c = costos_periodo.sort_values('date_pe', ascending=False).copy()
            df_c['Fecha'] = df_c['date_pe'].dt.strftime('%d/%m/%Y')
            df_c['Categoría'] = df_c['fuente'].str.replace('Costo ', '')
            df_c['Monto'] = df_c['amount'].apply(lambda x: f"S/ {x:,.2f}")
            df_c['Concepto'] = df_c['method']
            
            st.data_editor(
                df_c[['Fecha', 'transaction_id', 'Categoría', 'Concepto', 'Monto', 'referencia']].rename(
                    columns={'transaction_id': 'ID', 'referencia': 'Ref'}),
                column_config={
                    'Monto': st.column_config.NumberColumn('Monto', format="S/ %.2f"),
                    'Concepto': st.column_config.TextColumn('Concepto', help="Editar concepto"),
                    'Ref': st.column_config.TextColumn('Referencia', help="Editar referencia")
                },
                hide_index=True, use_container_width=True, key="editor_costos"
            )
            
            st.markdown("### 📈 Costos por Mes")
            costos_mensuales = costos_periodo.groupby('mes_label')['amount'].sum().reset_index()
            fig_c = px.bar(costos_mensuales, x='mes_label', y='amount', color_discrete_sequence=['#f97316'], labels={'mes_label':'Mes','amount':'Monto S/'})
            fig_c.update_layout(height=300, plot_bgcolor=bg, paper_bgcolor=bg_card, font_color=text, margin=dict(l=10,r=10,t=10,b=10))
            fig_c.update_yaxes(tickprefix="S/ ", gridcolor=border)
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.info("No hay costos registrados en este período.")
    
    with c_tab2:
        st.markdown("**➕ Registrar Nuevo Costo**")
        with st.form("form_nuevo_costo", clear_on_submit=True):
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                nueva_fecha = st.date_input("Fecha", datetime.now(), key="costo_fecha2")
                nueva_cat = st.selectbox("Categoría", ["Facebook Ads", "Sirvoy", "Asistente", "Otro"], key="costo_cat2")
            with col_n2:
                nuevo_monto = st.number_input("Monto S/", min_value=0.0, step=50.0, format="%.2f", key="costo_monto2")
                nuevo_ref = st.text_input("Concepto", placeholder="Descripción", key="costo_ref2")
            
            submitted = st.form_submit_button("💾 Guardar costo", type="primary", use_container_width=True)
            
            if submitted and nuevo_monto > 0:
                try:
                    cli_c = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                    cat_map = {"Facebook Ads":"Costo FB Ads", "Sirvoy":"Costo Sirvoy", "Asistente":"Costo Asistente", "Otro":"Costo Extra"}
                    doc = {
                        "fuente": cat_map.get(nueva_cat, "Costo Extra"),
                        "fecha": datetime.combine(nueva_fecha, datetime.min.time()),
                        "monto": nuevo_monto,
                        "moneda": "PEN",
                        "metodo": nuevo_ref or f"Costo {nueva_cat}",
                        "categoria": nueva_cat,
                        "tipo_pago": "Costo"
                    }
                    import hashlib
                    doc['hash'] = hashlib.md5(f"COSTO|{nueva_fecha}|{nuevo_monto}|{nuevo_ref}".encode()).hexdigest()
                    cli_c['pena_linda']['pagos'].insert_one(doc)
                    # Tambien insertar en cobros
                    import hashlib as hl
                    doc_cobro = {
                        "fecha": datetime.combine(nueva_fecha, datetime.min.time()),
                        "monto": nuevo_monto, "moneda": "PEN", "tipo": "costo",
                        "categoria": nueva_cat, "concepto": nuevo_ref or f"Costo {nueva_cat}",
                        "detalle": nuevo_ref or "", 
                        "hash": hl.md5(f"COBRO_COSTO|{nueva_fecha}|{nuevo_monto}|{nuevo_ref}".encode()).hexdigest()
                    }
                    cli_c['pena_linda']['cobros'].insert_one(doc_cobro)
                    cli_c.close()
                    st.success(f"✅ Costo de S/ {nuevo_monto:,.2f} registrado")
                    st.cache_data.clear()
                    st.session_state.ultima_actualizacion = datetime.now()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with c_tab3:
        st.markdown("**🔧 Desglose de Costos Extra**")
        st.caption("Costos categoría 'Otro' registrados manualmente")
        
        extra_df = costos_df[costos_df['fuente'] == 'Costo Extra'].copy() if not costos_df.empty and 'fuente' in costos_df.columns else pd.DataFrame()
        
        if not extra_df.empty:
            extra_df['Fecha'] = extra_df['date_pe'].dt.strftime('%d/%m/%Y')
            extra_df['Monto'] = extra_df['amount'].apply(lambda x: f"S/ {x:,.2f}")
            extra_df['Concepto'] = extra_df['method']
            
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                st.metric("📦 Costos Extra", f"{len(extra_df)} docs")
            with col_ex2:
                st.metric("💰 Total", f"S/ {extra_df['amount'].sum():,.0f}")

            # 📤 Botones de exportación Costos Extra
            exp_ec1, exp_ec2 = st.columns(2)
            with exp_ec1:
                st.download_button(
                    "📥 Descargar CSV (Costos Extra filtrados)",
                    data=df_to_csv(extra_df),
                    file_name=f"costos_extra_{fi}_{ff}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with exp_ec2:
                st.download_button(
                    "📥 Descargar Excel (Costos Extra filtrados)",
                    data=df_to_excel(extra_df),
                    file_name=f"costos_extra_{fi}_{ff}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.data_editor(
                extra_df[['Fecha','Concepto','Monto','categoria','transaction_id']].rename(
                    columns={'categoria':'Categoría','transaction_id':'ID'}),
                column_config={
                    'Concepto': st.column_config.TextColumn('Concepto', help="Editar concepto"),
                    'Monto': st.column_config.NumberColumn('Monto', format="S/ %.2f"),
                    'Categoría': st.column_config.TextColumn('Categoría', help="Editar categoría")
                },
                hide_index=True, use_container_width=True, key="editor_extras"
            )
        else:
            st.info("No hay costos extra registrados. Usa la pestaña '➕ Registrar Costo Extra' con categoría 'Otro' para agregar.")

# ================= TAB 3: CONCILIACIÓN DE PAGOS =================
with tabs[2]:
    con_tab1, con_tab2, con_tab3 = st.tabs(["🔄 Contraste de Tarjeta", "🚫 Links de Pago", "💳 Abonos a Chamba Digital"])
    
    with con_tab1:
        st.markdown("### 🔄 Contraste: Sirvoy Tarjeta vs Plataformas Digitales")
        st.write("Solo los cobros registrados con tarjeta en Sirvoy requieren contraste contra los depósitos reales en pasarelas.")
        
        c_1, c_2, c_3 = st.columns(3)
        with c_1:
            sirv_tarj = float(sv_sales_sirvoy[sv_sales_sirvoy['tipo_pago']=='Tarjeta']['amount'].sum())
            st.metric("Sirvoy Tarjetas (Bruto)", f"S/ {sirv_tarj:,.2f}")
        with c_2:
            st.metric("Plataformas Digitales", f"S/ {tb_plataformas:,.2f}")
        with c_3:
            st.metric("Pendiente de Contraste", f"S/ {lk:,.2f}", delta=f"{lk:,.2f}", delta_color="inverse")
            
        st.markdown("---")
        
        st.markdown("#### 📋 Coincidencias de Transacciones (Misma Fecha & Monto Similar)")
        match_rows = []
        plat_sv = sv_date_filtered[sv_date_filtered['fuente'].isin(['Izipay','Culqi','Openpay'])]
        for _, r in sv_sales_sirvoy[sv_sales_sirvoy['tipo_pago']=='Tarjeta'].iterrows():
            monto = r['amount']
            fecha = r['date_pe']
            match = plat_sv[
                (abs(plat_sv['amount'] - monto) < 2) &
                (plat_sv['date_pe'].dt.date == fecha.date())
            ] if not plat_sv.empty else pd.DataFrame()
            if not match.empty:
                match_rows.append({
                    "Fecha": fecha.strftime('%d/%m/%Y'),
                    "Monto Sirvoy": f"S/ {monto:,.2f}",
                    "Cobrado en Pasarela": f"S/ {match.iloc[0]['amount']:,.2f} ({match.iloc[0]['fuente']})",
                    "Estado": "✅ Conciliado"
                })
        if match_rows:
            st.dataframe(pd.DataFrame(match_rows[:30]), hide_index=True, use_container_width=True)
            st.caption(f"Mostrando {min(len(match_rows),30)} coincidencias encontradas.")
        else:
            st.info("No se encontraron coincidencias directas por fecha y monto en este rango.")
            
    with con_tab2:
        st.markdown("### 🚫 Gestión de Links de Pago Retenidos (Embargos)")
        st.write("Reporte de depósitos de links pendientes de abono en cuenta bancaria.")
        
        cl1, cl2, cl3 = st.columns(3)
        with cl1:
            st.metric("Monto Retenido / Pendiente", f"S/ {total_ret:,.2f}")
        with cl2:
            st.metric("Cantidad de Links Pendientes", len(pendientes_link))
        with cl3:
            total_links_per = len(la)
            st.metric("Total Links en Rango", total_links_per)
            
        # 📤 Botones de exportación Links
        exp_lc1, exp_lc2 = st.columns(2)
        with exp_lc1:
            st.download_button(
                "📥 Descargar CSV (Links filtrados)",
                data=df_to_csv(la),
                file_name=f"links_{fi}_{ff}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with exp_lc2:
            st.download_button(
                "📥 Descargar Excel (Links filtrados)",
                data=df_to_excel(la),
                file_name=f"links_{fi}_{ff}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        
        sub_l1, sub_l2 = st.columns([3, 2])
        
        with sub_l1:
            st.markdown("#### 📋 Listado de Links Pendientes")
            if not pendientes_link.empty:
                p_l = pendientes_link.copy()
                p_l['Fecha'] = p_l['date_pe'].dt.strftime('%d/%m/%Y %H:%M')
                p_l['Monto'] = p_l['amount'].apply(lambda x: f"S/ {x:,.2f}")
                p_l['Pasarela'] = p_l['fuente']
                p_l['Ref'] = p_l['method']
                st.dataframe(p_l[['Fecha', 'Monto', 'Pasarela', 'Ref']], hide_index=True, use_container_width=True)
            else:
                st.success("✅ ¡Perfecto! No hay links pendientes en este rango.")
                
        with sub_l2:
            st.markdown("#### ⚙️ Validar Depósitos de Links")
            st.caption("Marca los links como depositados una vez que los verifiques en tu cuenta bancaria.")
            
            if not pendientes_link.empty:
                p_opts = pendientes_link.sort_values('date_pe').copy()
                p_opts['label'] = p_opts.apply(
                    lambda r: f"{r['date_pe'].strftime('%d/%m %H:%M')} - S/ {r['amount']:,.2f} ({r['fuente']})", axis=1
                )
                p_opts['str_id'] = p_opts['_id'].apply(str)
                id_to_label = dict(zip(p_opts['str_id'], p_opts['label']))
                
                seleccionados_ids = st.multiselect(
                    "Seleccionar pagos depositados:", 
                    options=p_opts['str_id'].tolist(), 
                    format_func=lambda x: id_to_label.get(x, x),
                    key="select_val_links"
                )
                
                if seleccionados_ids and st.button("✅ Marcar como Depositados", type="primary", use_container_width=True):
                    try:
                        from bson import ObjectId
                        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                        object_ids = [ObjectId(sid) for sid in seleccionados_ids]
                        res = cli['pena_linda']['pagos'].update_many(
                            {"_id": {"$in": object_ids}},
                            {"$set": {"estado_deposito": "depositado", "fecha_depositado": pd.Timestamp.now().to_pydatetime(), "conciliado": True}}
                        )
                        cli.close()
                        st.success(f"✅ Se actualizaron {res.modified_count} pagos a estado depositado.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                        
                if st.button("📌 Marcar TODOS como depositados", use_container_width=True):
                    try:
                        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                        res = cli['pena_linda']['pagos'].update_many(
                            {"es_link": True, "estado_deposito": "pendiente"},
                            {"$set": {"estado_deposito": "depositado", "fecha_depositado": pd.Timestamp.now().to_pydatetime(), "conciliado": True}}
                        )
                        cli.close()
                        st.success(f"✅ Se actualizaron {res.modified_count} pagos a depositados.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("Sin acciones disponibles (0 links pendientes).")
                
    with con_tab3:
        st.markdown("### 💳 Registro de Abonos a Chamba Digital")
        st.write("Verifica y registra los abonos de saldo que realiza Peña Linda para amortizar la deuda de comisiones y costos.")
        
        # Leer cobros extra desde MongoDB
        try:
            cli_cob = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
            cobros_all = list(cli_cob['pena_linda']['cobros'].find({}))
            cli_cob.close()
            cobros_df = pd.DataFrame(cobros_all)
            cobros_extra = cobros_df[cobros_df['categoria'] == 'Extra'].copy() if not cobros_df.empty else pd.DataFrame()
            total_extra = float(cobros_extra['monto'].sum()) if not cobros_extra.empty else 0
        except:
            cobros_extra = pd.DataFrame()
            total_extra = 0

        ca1, ca2, ca3, ca4 = st.columns(4)
        with ca1:
            st.metric("Total Adeudado Histórico", f"S/ {adeudado:,.2f}")
        with ca2:
            st.metric("Total Abonado", f"S/ {total_abonos:,.2f}")
        with ca3:
            st.metric("Saldo Deudor Actual", f"S/ {saldo_pendiente:,.2f}", delta=f"{saldo_pendiente:,.2f}", delta_color="inverse")
        with ca4:
            st.metric("📌 Costos Extra (detalle)", f"S/ {total_extra:,.2f}", help="Costos categoria 'Extra' en tabla cobros")

        # 📤 Botones de exportación Abonos / Conciliación
        exp_ac1, exp_ac2 = st.columns(2)
        with exp_ac1:
            st.download_button(
                "📥 Descargar CSV (Abonos filtrados)",
                data=df_to_csv(pagos_recibidos) if not pagos_recibidos.empty else df_to_csv(pd.DataFrame()),
                file_name=f"abonos_{fi}_{ff}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with exp_ac2:
            st.download_button(
                "📥 Descargar Excel (Abonos filtrados)",
                data=df_to_excel(pagos_recibidos) if not pagos_recibidos.empty else df_to_excel(pd.DataFrame()),
                file_name=f"abonos_{fi}_{ff}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        
        # Desglose de Costos Extra
        if not cobros_extra.empty:
            st.markdown("#### 🔍 Desglose de Costos Extra (Categoría 'Extra')")
            cobros_extra['Fecha'] = pd.to_datetime(cobros_extra['fecha']).dt.strftime('%d/%m/%Y')
            cobros_extra['Monto'] = cobros_extra['monto'].apply(lambda x: f"S/ {x:,.2f}")
            
            st.data_editor(
                cobros_extra[['Fecha', 'concepto', 'Monto', 'detalle', 'tipo']].rename(
                    columns={'concepto': 'Concepto', 'detalle': 'Detalle', 'tipo': 'Tipo'}),
                column_config={
                    'Concepto': st.column_config.TextColumn('Concepto', help="Editar concepto"),
                    'Monto': st.column_config.NumberColumn('Monto', format="S/ %.2f"),
                    'Detalle': st.column_config.TextColumn('Detalle', help="Editar detalle")
                },
                hide_index=True, use_container_width=True, key="editor_cobros_extra"
            )
        
        sa1, sa2 = st.columns([3, 2])
        
        with sa1:
            st.markdown("#### 📋 Historial de Abonos Registrados")
            if not pagos_recibidos.empty:
                ab_df = pagos_recibidos.sort_values('date_pe', ascending=False).copy()
                ab_df['Fecha'] = ab_df['date_pe'].dt.strftime('%d/%m/%Y')
                ab_df['Monto'] = ab_df['amount'].apply(lambda x: f"S/ {x:,.2f}")
                ab_df['Referencia / Método'] = ab_df['method']
                st.data_editor(
                    ab_df[['Fecha', 'Monto', 'Referencia / Método', 'transaction_id']].rename(
                        columns={'transaction_id': 'ID'}),
                    column_config={
                        'Monto': st.column_config.NumberColumn('Monto', format="S/ %.2f"),
                        'Referencia / Método': st.column_config.TextColumn('Referencia', help="Editar referencia")
                    },
                    hide_index=True, use_container_width=True, key="editor_abonos"
                )
            else:
                st.info("No hay abonos registrados aún.")
                
        with sa2:
            st.markdown("#### 📝 Registrar Nuevo Abono")
            ab_fecha = st.date_input("Fecha del Abono", datetime.now(), key="reg_abono_date")
            ab_monto = st.number_input("Monto Abonado (S/)", min_value=0.0, step=100.0, format="%.2f", key="reg_abono_monto")
            ab_ref = st.text_input("Referencia bancaria / Canal", placeholder="Ej: Transf. BCP...", key="reg_abono_ref")
            
            if st.button("💾 Guardar Abono", type="primary", use_container_width=True, disabled=(ab_monto <= 0)):
                try:
                    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                    doc = {
                        "fuente": "Abono Chamba",
                        "fecha": datetime.combine(ab_fecha, datetime.min.time()),
                        "monto": ab_monto,
                        "moneda": "PEN",
                        "metodo": ab_ref or "Abono manual",
                        "tipo_pago": "Abono",
                        "categoria": "Abono"
                    }
                    raw = f"ABONO|{ab_fecha}|{ab_monto}|{ab_ref}"
                    doc['hash'] = hashlib.md5(raw.encode()).hexdigest()
                    cli['pena_linda']['pagos'].insert_one(doc)
                    # Tambien insertar en cobros
                    doc_cobro = {
                        "fecha": datetime.combine(ab_fecha, datetime.min.time()),
                        "monto": ab_monto, "moneda": "PEN", "tipo": "abono",
                        "categoria": "Abono", "concepto": "Pago recibido de Peña Linda",
                        "detalle": ab_ref or "Abono manual",
                        "hash": hashlib.md5(f"COBRO_ABONO|{ab_fecha}|{ab_monto}|{ab_ref}".encode()).hexdigest()
                    }
                    cli['pena_linda']['cobros'].insert_one(doc_cobro)
                    cli.close()
                    st.success(f"✅ Abono de S/ {ab_monto:,.2f} registrado correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    if "duplicate key error" in str(e).lower():
                        st.error("⚠️ Este abono ya está registrado (evitando duplicado).")
                    else:
                        st.error(f"Error al registrar abono: {e}")
            
            st.markdown("---")
            st.markdown("#### 🗑️ Eliminar Abono")
            if not pagos_recibidos.empty:
                ab_opts = pagos_recibidos.sort_values('date_pe', ascending=False).copy()
                ab_opts['label'] = ab_opts.apply(
                    lambda r: f"S/ {r['amount']:,.2f} - {r['date_pe'].strftime('%d/%m/%Y')} ({r['method']})", axis=1
                )
                ab_opts['str_id'] = ab_opts['_id'].apply(str)
                ab_id_to_label = dict(zip(ab_opts['str_id'], ab_opts['label']))
                
                abono_a_eliminar_id = st.selectbox(
                    "Selecciona abono a eliminar:",
                    options=ab_opts['str_id'].tolist(),
                    format_func=lambda x: ab_id_to_label.get(x, x),
                    key="select_del_abono"
                )
                
                if st.button("🗑️ Eliminar Abono Seleccionado", type="secondary", use_container_width=True):
                    try:
                        from bson import ObjectId
                        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                        res = cli['pena_linda']['pagos'].delete_one({"_id": ObjectId(abono_a_eliminar_id)})
                        cli.close()
                        st.success(f"✅ Se eliminó el abono correctamente.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")
            else:
                st.caption("No hay abonos registrados para eliminar.")

# ================= TAB 4: HISTORIAL Y CONCILIACIÓN =================
with tabs[3]:
    st.markdown("### 📋 Historial y Conciliación de Operaciones")
    st.write("Cruce entre facturas QuickBooks (comisiones + costos) y abonos registrados. Identifica coincidencias y discrepancias para consolidar.")
    
    # Cargar datos de cobros (facturas + abonos) desde MongoDB
    try:
        cli_hist = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        cobros_all = list(cli_hist['pena_linda']['cobros'].find({}))
        cli_hist.close()
        cobros_df = pd.DataFrame(cobros_all)
        
        if not cobros_df.empty:
            cobros_df['fecha_dt'] = pd.to_datetime(cobros_df['fecha'], errors='coerce')
            cobros_df = cobros_df.sort_values('fecha_dt', ascending=False)
            
            # Separar por tipo
            facturas_qb = cobros_df[cobros_df['origen_importacion'] == 'QuickBooks'].copy()
            abonos_qb = cobros_df[(cobros_df['tipo'] == 'abono') & (cobros_df['origen_importacion'] == 'QuickBooks')].copy()
            facturas_manual = cobros_df[(cobros_df['tipo'] == 'comision') & (cobros_df['origen_importacion'] != 'QuickBooks')].copy()
            costos_manual = cobros_df[(cobros_df['tipo'] == 'costo') & (cobros_df['origen_importacion'] != 'QuickBooks')].copy()
            abonos_manual = cobros_df[(cobros_df['tipo'] == 'abono') & (cobros_df['origen_importacion'] != 'QuickBooks')].copy()
            
            # KPIs resumen
            h1, h2, h3, h4 = st.columns(4)
            with h1:
                st.metric("📄 Facturas QB (Comisión)", f"S/ {facturas_qb[facturas_qb['tipo']=='comision']['monto'].sum():,.2f}", 
                         help=f"{len(facturas_qb[facturas_qb['tipo']=='comision'])} facturas")
            with h2:
                st.metric("📄 Facturas QB (Costos)", f"S/ {facturas_qb[facturas_qb['tipo']=='costo']['monto'].sum():,.2f}",
                         help=f"{len(facturas_qb[facturas_qb['tipo']=='costo'])} facturas")
            with h3:
                st.metric("💰 Abonos QB", f"S/ {abonos_qb['monto'].sum():,.2f}",
                         help=f"{len(abonos_qb)} abonos (nov 2025 - mar 2026)")
            with h4:
                st.metric("💰 Abonos Manuales (desde 03/03)", f"S/ {abonos_manual['monto'].sum():,.2f}",
                         help=f"{len(abonos_manual)} abonos")
            
            st.markdown("---")
            
            # === CRUCE: Facturas vs Abonos ===
            st.markdown("#### 🔍 Cruce Facturas QuickBooks ↔ Abonos")
            
            # Mostrar facturas de comisión con estado de pago
            com_qb = facturas_qb[facturas_qb['tipo'] == 'comision'].copy()
            cost_qb = facturas_qb[facturas_qb['tipo'] == 'costo'].copy()
            
            tab_c1, tab_c2 = st.tabs(["💼 Comisión (Chamba → Peña Linda)", "💸 Costos Operativos (Chamba → Peña Linda)"])
            
            with tab_c1:
                st.markdown("**Facturas de Comisión emitidas por Chamba Digital a Peña Linda**")
                if not com_qb.empty:
                    com_qb['Fecha'] = com_qb['fecha_dt'].dt.strftime('%d/%m/%Y')
                    com_qb['Monto'] = com_qb['monto'].apply(lambda x: f"S/ {x:,.2f}")
                    com_qb['Estado QB'] = com_qb['qbo_estado']
                    com_qb['Referencia'] = com_qb['qbo_ref']
                    
                    st.dataframe(
                        com_qb[['Fecha', 'Referencia', 'Monto', 'Estado QB']].rename(
                            columns={'Referencia': 'Factura', 'Estado QB': 'Estado en QB'}
                        ),
                        hide_index=True, use_container_width=True
                    )
                    
                    # Export
                    exp_fc1, exp_fc2 = st.columns(2)
                    with exp_fc1:
                        st.download_button("📥 CSV Facturas Comisión", df_to_csv(com_qb), 
                                         file_name=f"facturas_comision_{fi}_{ff}.csv", mime="text/csv")
                    with exp_fc2:
                        st.download_button("📥 Excel Facturas Comisión", df_to_excel(com_qb),
                                         file_name=f"facturas_comision_{fi}_{ff}.xlsx",
                                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info("No hay facturas de comisión importadas de QuickBooks.")
            
            with tab_c2:
                st.markdown("**Facturas de Costos Operativos emitidas por Chamba Digital a Peña Linda**")
                if not cost_qb.empty:
                    cost_qb['Fecha'] = cost_qb['fecha_dt'].dt.strftime('%d/%m/%Y')
                    cost_qb['Monto'] = cost_qb['monto'].apply(lambda x: f"S/ {x:,.2f}")
                    cost_qb['Estado QB'] = cost_qb['qbo_estado']
                    cost_qb['Referencia'] = cost_qb['qbo_ref']
                    
                    st.dataframe(
                        cost_qb[['Fecha', 'Referencia', 'Monto', 'Estado QB']].rename(
                            columns={'Referencia': 'Factura', 'Estado QB': 'Estado en QB'}
                        ),
                        hide_index=True, use_container_width=True
                    )
                    
                    exp_fco1, exp_fco2 = st.columns(2)
                    with exp_fco1:
                        st.download_button("📥 CSV Facturas Costos", df_to_csv(cost_qb),
                                         file_name=f"facturas_costos_{fi}_{ff}.csv", mime="text/csv")
                    with exp_fco2:
                        st.download_button("📥 Excel Facturas Costos", df_to_excel(cost_qb),
                                         file_name=f"facturas_costos_{fi}_{ff}.xlsx",
                                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info("No hay facturas de costos importadas de QuickBooks.")
            
            st.markdown("---")
            
            # === ABONOS RECIBIDOS ===
            st.markdown("#### 💳 Abonos Recibidos de Peña Linda")
            
            tab_a1, tab_a2 = st.tabs(["📥 Abonos QuickBooks (históricos)", "✏️ Abonos Manuales (desde 03/03)"])
            
            with tab_a1:
                if not abonos_qb.empty:
                    abonos_qb['Fecha'] = abonos_qb['fecha_dt'].dt.strftime('%d/%m/%Y')
                    abonos_qb['Monto'] = abonos_qb['monto'].apply(lambda x: f"S/ {x:,.2f}")
                    abonos_qb['Referencia'] = abonos_qb['metodo']
                    
                    st.dataframe(
                        abonos_qb[['Fecha', 'Referencia', 'Monto']].rename(
                            columns={'Referencia': 'Ref. / Método'}
                        ),
                        hide_index=True, use_container_width=True
                    )
                    st.caption(f"Total histórico: S/ {abonos_qb['monto'].sum():,.2f} ({len(abonos_qb)} abonos)")
                else:
                    st.info("Sin abonos históricos de QuickBooks.")
            
            with tab_a2:
                if not abonos_manual.empty:
                    abonos_manual['Fecha'] = pd.to_datetime(abonos_manual['fecha']).dt.strftime('%d/%m/%Y')
                    abonos_manual['Monto'] = abonos_manual['monto'].apply(lambda x: f"S/ {x:,.2f}")
                    abonos_manual['Referencia'] = abonos_manual['metodo']
                    
                    st.dataframe(
                        abonos_manual[['Fecha', 'Referencia', 'Monto']].rename(
                            columns={'Referencia': 'Ref. / Método'}
                        ),
                        hide_index=True, use_container_width=True
                    )
                    st.caption(f"Total desde 03/03: S/ {abonos_manual['monto'].sum():,.2f} ({len(abonos_manual)} abonos)")
                else:
                    st.info("Sin abonos manuales registrados.")
            
            st.markdown("---")
            
            # === DISCREPANCIAS / REVISIÓN PENDIENTE ===
            st.markdown("#### ⚠️ Discrepancias y Pendientes de Revisión")
            
            # Facturas QB con estado "Vencido" (no pagadas en QB)
            vencidas = facturas_qb[facturas_qb['qbo_estado'].str.contains('Vencido', na=False)]
            if not vencidas.empty:
                st.warning(f"⚠️ **{len(vencidas)} facturas en estado 'Vencido' en QuickBooks** — revisar si fueron pagadas fuera de QB o quedan pendientes:")
                vencidas['Fecha'] = vencidas['fecha_dt'].dt.strftime('%d/%m/%Y')
                vencidas['Monto'] = vencidas['monto'].apply(lambda x: f"S/ {x:,.2f}")
                vencidas['Tipo'] = vencidas['tipo'].apply(lambda x: 'Comisión' if x == 'comision' else 'Costo')
                st.dataframe(
                    vencidas[['Fecha', 'qbo_ref', 'Tipo', 'Monto', 'qbo_estado']].rename(
                        columns={'qbo_ref': 'Factura', 'qbo_estado': 'Estado QB', 'Tipo': 'Categoría'}
                    ),
                    hide_index=True, use_container_width=True
                )
            
            # Facturas QB pagadas en QB pero sin abono correspondiente en MongoDB
            pagadas_qb = facturas_qb[facturas_qb['qbo_estado'] == 'Pagada']
            if not pagadas_qb.empty:
                st.info(f"ℹ️ **{len(pagadas_qb)} facturas marcadas 'Pagada' en QuickBooks** — verificar si cada una tiene su abono correspondiente en la tabla de abonos (manual o QB).")
            
            # Diferencia total facturado vs abonado (solo comisión)
            total_fact_comision = facturas_qb[facturas_qb['tipo'] == 'comision']['monto'].sum()
            total_abonado_todo = abonos_qb['monto'].sum() + abonos_manual['monto'].sum()
            diff = total_fact_comision - total_abonado_todo
            
            if diff > 0:
                st.error(f"🔴 **Diferencia por cubrir: S/ {diff:,.2f}** — Total facturado en comisión (QB) supera a lo abonado (QB + manuales).")
            elif diff < 0:
                st.success(f"🟢 **Sobrante abonado: S/ {abs(diff):,.2f}** — Se ha abonado más de lo facturado en comisión QB. Verificar costos.")
            else:
                st.success("✅ **Cuadrado perfecto** — Facturación de comisión = Abonos totales.")
                
    except Exception as e:
        st.error(f"Error cargando historial: {e}")

# ================= TAB 5: EXPORTAR Y REPORTES =================
with tabs[4]:
    st.markdown("### 📤 Exportación de Reportes del Periodo")
    st.write("Genera y descarga informes consolidados listos para imprimir o compartir.")
    
    rep1, rep2, rep3 = st.columns(3)
    
    with rep1:
        st.markdown('<div class="shad-card"><h4>📄 Reporte PDF</h4>', unsafe_allow_html=True)
        st.write("Genera un documento PDF formateado con el desglose del periodo filtrado.")
        if st.button("Construir PDF", use_container_width=True):
            with st.spinner("Generando PDF..."):
                pdf_p = os.path.join(CARPETA, f"Reporte_{ff.strftime('%Y%m%d')}.pdf")
                doc = SimpleDocTemplate(pdf_p, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
                styles = getSampleStyleSheet()
                
                # Check if custom styles exist or add them
                try: styles.add(ParagraphStyle('T', parent=styles['Title'], fontSize=20, textColor=rc.HexColor('#1B365D'), spaceAfter=4))
                except: pass
                try: styles.add(ParagraphStyle('S', parent=styles['Normal'], fontSize=11, textColor=rc.HexColor('#666'), spaceAfter=15, alignment=TA_CENTER))
                except: pass
                try: styles.add(ParagraphStyle('C', fontSize=9, alignment=TA_CENTER))
                except: pass
                
                def at(d, cw=None):
                    t = Table(d, colWidths=cw, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                        ('FONTSIZE',(0,0),(-1,-1),9),
                        ('TEXTCOLOR',(0,0),(-1,0),rc.white),
                        ('BACKGROUND',(0,0),(-1,0),rc.HexColor('#1B365D')),
                        ('ALIGN',(1,0),(-1,-1),'CENTER'),
                        ('GRID',(0,0),(-1,-1),0.3,rc.HexColor('#DDD')),
                        ('ROWBACKGROUNDS',(0,1),(-1,-1),[rc.white,rc.HexColor('#F5F8FC')]),
                        ('TOPPADDING',(0,0),(-1,-1),5),
                        ('BOTTOMPADDING',(0,0),(-1,-1),5)
                    ]))
                    elems.append(t)
                    
                elems = []
                elems.append(Spacer(1,10))
                elems.append(Paragraph("Peña Linda Bungalows — Reporte de Conciliación", styles.get('T', styles['Title'])))
                elems.append(Paragraph(f"Período: {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}", styles.get('S', styles['Normal'])))
                elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
                elems.append(Spacer(1,6))
                
                at([
                    ['Indicador', 'Valor'],
                    ['Ventas Sirvoy (Bruto)', f'S/ {tb_sirvoy:,.2f}'],
                    ['Número de Tx', str(tx)],
                    ['Recibido Confirmado', f'S/ {tb_recibido:,.2f}'],
                    ['Comisión 5%', f'S/ {comision:,.2f}'],
                    ['Costos del Periodo', f'S/ {total_costos:,.2f}']
                ], [180, 180])
                
                elems.append(Spacer(1,15))
                elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
                elems.append(Paragraph("Chamba Digital — Gestión e Ingeniería", styles.get('C', styles['Normal'])))
                doc.build(elems)
                
                with open(pdf_p, "rb") as f:
                    st.download_button("⬇️ Descargar Reporte PDF", f.read(), f"Reporte_{ff.strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with rep2:
        st.markdown('<div class="shad-card"><h4>🌐 Reporte HTML</h4>', unsafe_allow_html=True)
        st.write("Genera una vista HTML estática y descargable para navegadores.")
        if st.button("Construir HTML", use_container_width=True):
            html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Reporte Peña Linda</title>
<style>body{{font-family:'Inter','Segoe UI',Arial;margin:20px;background:#fafafa;color:#0f0f0f}}
.header{{background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;padding:1.5rem;border-radius:14px;text-align:center}}
.section{{background:white;border-radius:12px;padding:1.2rem;margin:1rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.1);border:1px solid #e4e4e7}}
table{{width:100%;border-collapse:collapse;margin:0.5rem 0}}
th{{background:#3b82f6;color:white;padding:8px;font-weight:600}}
td{{padding:6px 8px;border-bottom:1px solid #e4e4e7;text-align:center}}
tr:nth-child(even){{background:#f8fafc}}
.metric{{display:inline-block;margin:0.5rem;padding:1rem;background:white;border-radius:10px;border:1px solid #e4e4e7;border-top:3px solid #3b82f6;text-align:center;min-width:130px}}
.metric h3{{margin:0;font-size:1.4rem;color:#3b82f6}}.metric p{{margin:0;color:#71717a;font-size:0.75rem;text-transform:uppercase}}
.footer{{text-align:center;color:#a1a1aa;padding:1rem;font-size:0.85rem}}</style></head><body>
<div class="header"><h1>🏝️ Peña Linda Bungalows</h1><p>{fi.strftime('%d/%m/%Y')} → {ff.strftime('%d/%m/%Y')}</p></div>
<div style="text-align:center">
<div class="metric"><p>Sirvoy Bruto</p><h3>S/ {tb_sirvoy:,.2f}</h3></div>
<div class="metric"><p>Tx</p><h3>{tx}</h3></div>
<div class="metric"><p>Recibido</p><h3>S/ {tb_recibido:,.2f}</h3></div>
<div class="metric"><p>Comisión 5%</p><h3>S/ {comision:,.2f}</h3></div>
</div>
<div class="section">
<h2>📋 Resumen de Costos y Saldos</h2>
<p><strong>Total Costos del Periodo:</strong> S/ {total_costos:,.2f}</p>
<p><strong>Saldo Deudor Total:</strong> S/ {saldo_pendiente:,.2f}</p>
</div>
<div class="footer">🏢 Chamba Digital</div></body></html>"""
            st.download_button("⬇️ Descargar Reporte HTML", html.encode(), f"Reporte_{ff.strftime('%Y%m%d')}.html", "text/html", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with rep3:
        st.markdown('<div class="shad-card"><h4>📊 Datos CSV</h4>', unsafe_allow_html=True)
        st.write("Descarga los datos crudos filtrados del período en formato plano CSV.")
        if not sv_sales_f.empty:
            sv_exp = sv_sales_f.sort_values('date_pe', ascending=False).copy()
            sv_exp['Fecha'] = sv_exp['date_pe'].dt.strftime('%d/%m/%Y %H:%M')
            sv_exp['Monto'] = sv_exp['amount']
            csv_data = sv_exp[['Fecha', 'fuente', 'Monto', 'tipo_pago', 'method', 'referencia']].to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV", csv_data, f"Datos_Filtrados_{ff.strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        else:
            st.button("Descargar CSV (Vacío)", disabled=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- NUEVO: REPORTES SEMANALES ---
    st.markdown("---")
    st.markdown("### 📅 Reportes Semanales Consolidados (Martes a Lunes)")
    st.write("Genera y descarga el reporte consolidado semanal de ventas brutas, comisiones, costos y abonos.")
    
    start_date_w = date(2026, 3, 3)
    end_date_w = datetime.now().date()
    
    # Encontrar las semanas de martes a lunes
    current_w = start_date_w
    weeks_list = []
    while current_w <= end_date_w:
        w_start = current_w
        w_end = current_w + timedelta(days=6)
        label = f"Semana: {w_start.strftime('%d/%m/%Y')} al {w_end.strftime('%d/%m/%Y')}"
        weeks_list.append((w_start, w_end, label))
        current_w = current_w + timedelta(days=7)
        
    weeks_list.reverse()
    
    selected_week_opt = st.selectbox(
        "Seleccionar período semanal:",
        options=range(len(weeks_list)),
        format_func=lambda idx: weeks_list[idx][2],
        key="weekly_report_select_box"
    )
    
    if selected_week_opt is not None:
        w_start, w_end, w_label = weeks_list[selected_week_opt]
        
        # Filtrar los datos en el dataframe global sv
        df_week = sv[
            (sv['date_pe'].dt.date >= w_start) &
            (sv['date_pe'].dt.date <= w_end)
        ]
        
        # Ventas Sirvoy Bruto (excluyendo Costos, Abonos o Saldo Base)
        is_sale_w = (df_week['fuente'] == 'Sirvoy') & (~df_week['tipo_pago'].isin(['Costo', 'Abono'])) & (~df_week['fuente'].isin(['Abono Chamba', 'Saldo Base']))
        sales_sirvoy_w = df_week[is_sale_w]
        v_sirvoy_monto = float(sales_sirvoy_w['amount'].sum())
        v_sirvoy_tx = len(sales_sirvoy_w)
        
        # Comisión 5%
        comision_w = v_sirvoy_monto * 0.05
        
        # Gastos y Costos
        costos_w = df_week[df_week['tipo_pago'] == 'Costo']
        v_costos_monto = float(costos_w['amount'].sum())
        
        # Abonos Chamba
        abonos_w = df_week[df_week['fuente'] == 'Abono Chamba']
        v_abonos_monto = float(abonos_w['amount'].sum())
        
        # Tarjetas de Resumen
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1:
            st.metric("Ventas Sirvoy Bruto", f"S/ {v_sirvoy_monto:,.2f}", f"{v_sirvoy_tx} tx")
        with col_w2:
            st.metric("Comisión Chamba (5%)", f"S/ {comision_w:,.2f}")
        with col_w3:
            st.metric("Gastos / Costos", f"S/ {v_costos_monto:,.2f}")
        with col_w4:
            st.metric("Abonos Registrados", f"S/ {v_abonos_monto:,.2f}")
            
        # Desgloses en Pantalla (UI)
        dec_col1, dec_col2 = st.columns(2)
        with dec_col1:
            st.markdown("##### 💸 Gastos de la Semana")
            if not costos_w.empty:
                c_disp = costos_w.sort_values('date_pe').copy()
                c_disp['Fecha'] = c_disp['date_pe'].dt.strftime('%d/%m/%Y')
                c_disp['Monto'] = c_disp['amount'].apply(lambda x: f"S/ {x:,.2f}")
                c_disp['Concepto'] = c_disp['fuente']
                c_disp['Referencia'] = c_disp['metodo']
                st.dataframe(c_disp[['Fecha', 'Concepto', 'Referencia', 'Monto']], hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron gastos en esta semana.")
                
        with dec_col2:
            st.markdown("##### 💳 Abonos de la Semana")
            if not abonos_w.empty:
                a_disp = abonos_w.sort_values('date_pe').copy()
                a_disp['Fecha'] = a_disp['date_pe'].dt.strftime('%d/%m/%Y')
                a_disp['Monto'] = a_disp['amount'].apply(lambda x: f"S/ {x:,.2f}")
                a_disp['Referencia / Canal'] = a_disp['metodo']
                st.dataframe(a_disp[['Fecha', 'Referencia / Canal', 'Monto']], hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron abonos en esta semana.")
                
        st.markdown("<br>", unsafe_allow_html=True)
            
        # Generar en memoria y preparar descarga
        pdf_filename = f"Reporte_Semanal_{w_start.strftime('%Y%m%d')}_{w_end.strftime('%Y%m%d')}.pdf"
        
        buffer = io.BytesIO()
        doc_w = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=1.5*cm, bottomMargin=1.5*cm,
            leftMargin=2*cm, rightMargin=2*cm
        )
        styles_w = getSampleStyleSheet()
        
        cell_style = ParagraphStyle(
            'WCell',
            parent=styles_w['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        )
        cell_left = ParagraphStyle(
            'WCellL',
            parent=styles_w['Normal'],
            fontSize=8,
            alignment=TA_LEFT
        )
        
        elems_w = []
        
        # --- 1. Cabecera (Izquierda Info, Centro Título, Derecha Logo) ---
        info_chamba = """<b>Chamba Digital SAC</b><br/>
Alameda del Premio Real Mz. K, Lt. 34C, La Encantada de Villa, Chorrillos<br/>
Lima, Lima 15067 PE<br/>
+51932164892<br/>
hola@chambadigital.la<br/>
chambadigital.la<br/>
N.° de registro de IGV: 20604661476"""
        p_chamba = Paragraph(info_chamba, ParagraphStyle('ChInfo', fontSize=7, leading=9, textColor=rc.HexColor('#333')))
        
        p_title = Paragraph("<b>Factura De<br/>Impuestos</b>", ParagraphStyle('ChTitle', fontSize=15, leading=17, textColor=rc.HexColor('#111'), alignment=TA_CENTER))
        
        # Logo simulado azul
        logo_data = [
            [Paragraph("<font color='white'><b>CHA</b></font>", ParagraphStyle('L1', fontName='Helvetica-Bold', fontSize=12, leading=12, alignment=TA_CENTER))],
            [Paragraph("<font color='white'><b>MBA</b></font>", ParagraphStyle('L2', fontName='Helvetica-Bold', fontSize=12, leading=12, alignment=TA_CENTER))],
            [Paragraph("<font color='#D6D6FF'><b>• DIGITAL</b></font>", ParagraphStyle('L3', fontName='Helvetica-Bold', fontSize=6, leading=7, alignment=TA_CENTER))]
        ]
        t_logo = Table(logo_data, colWidths=[70])
        t_logo.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), rc.HexColor('#0000FF')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        t_header = Table([[p_chamba, p_title, t_logo]], colWidths=[200, 180, 100])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        elems_w.append(t_header)
        elems_w.append(Spacer(1, 5))
        
        # --- 2. FACTURAR A ---
        facturar_a_data = [
            [Paragraph("<b>FACTURAR A</b>", ParagraphStyle('FHead', fontSize=7, leading=8, textColor=rc.HexColor('#1B365D')))],
            [Paragraph("Peña Linda Bungalows Sac", ParagraphStyle('FBody', fontSize=9, leading=11, textColor=rc.HexColor('#333')))]
        ]
        t_facturar = Table(facturar_a_data, colWidths=[200])
        t_facturar.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
            ('BOX', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        elems_w.append(t_facturar)
        elems_w.append(Spacer(1, 8))
        
        # --- 3. Tabla de Metadatos ---
        invoice_num = f"INV{int(w_start.strftime('%y%m%d')) % 1000:03d}"
        fecha_emision = w_end.strftime('%d/%m/%Y')
        fecha_venc = (w_end + timedelta(days=7)).strftime('%d/%m/%Y')
        total_p_val = comision_w + v_costos_monto
        total_a_pagar_formatted = f"S/. {total_p_val:,.2f}"
        
        meta_headers = [Paragraph(f"<b>{c}</b>", ParagraphStyle('MH', fontSize=7, leading=8, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER)) for c in 
                        ["FACTURA N.º", "FECHA", "TOTAL A PAGAR", "FECHA DE VENCIMIENTO", "CONDICIONES", "ADJUNTO"]]
        meta_values = [Paragraph(v, ParagraphStyle('MV', fontSize=8, leading=9, alignment=TA_CENTER)) for v in 
                       [invoice_num, fecha_emision, total_a_pagar_formatted, fecha_venc, "7 Días", ""]]
        
        t_metadata = Table([meta_headers, meta_values], colWidths=[80, 80, 80, 100, 80, 60])
        t_metadata.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
            ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elems_w.append(t_metadata)
        
        # Línea divisoria punteada
        elems_w.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC'), spaceBefore=8, spaceAfter=2, dash=(2,2)))
        elems_w.append(Paragraph("<font color='#666' size='6'>SEPARE LA PARTE SUPERIOR Y REGRÉSELA JUNTO CON EL PAGO.</font>", ParagraphStyle('Sep', alignment=TA_CENTER)))
        elems_w.append(Spacer(1, 10))
        
        # --- 4. Tabla Principal de Conceptos ---
        main_items = [
            [Paragraph(f"<b>{c}</b>", ParagraphStyle('MTH', fontSize=7, leading=8, textColor=rc.HexColor('#1B365D'), alignment=TA_LEFT if i==1 else TA_CENTER))
             for i, c in enumerate(["FECHA", "DESCRIPCIÓN", "CANT.", "TASA", "IMPORTE"])]
        ]
        
        # Agregar Comisión
        comision_desc = f"<b>Comisión del 5% por ventas generadas</b><br/>Ventas generadas del {w_start.strftime('%d-%m')} al {w_end.strftime('%d-%m')}<br/>S/. {v_sirvoy_monto:,.2f}"
        main_items.append([
            Paragraph(w_end.strftime('%d/%m/%Y'), cell_style),
            Paragraph(comision_desc, cell_left),
            Paragraph("1", cell_style),
            Paragraph(f"{comision_w:,.2f}", cell_style),
            Paragraph(f"{comision_w:,.2f}", cell_style)
        ])
        
        # Agregar Costos
        for _, r in costos_w.sort_values('date_pe').iterrows():
            c_desc = f"<b>{r['fuente']}</b><br/>Peña Linda Bungalows hasta el {r['date_pe'].strftime('%d %b %Y').lower()}<br/>Pagado {r['metodo'] or 'Manual'}"
            main_items.append([
                Paragraph(r['date_pe'].strftime('%d/%m/%Y'), cell_style),
                Paragraph(c_desc, cell_left),
                Paragraph("1", cell_style),
                Paragraph(f"{r['amount']:,.2f}", cell_style),
                Paragraph(f"{r['amount']:,.2f}", cell_style)
            ])
            
        t_main = Table(main_items, colWidths=[70, 240, 30, 70, 70])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
            ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elems_w.append(t_main)
        elems_w.append(Spacer(1, 5))
        
        # --- 5. Totales y Saldo Pendiente ---
        subtotal_val = comision_w + v_costos_monto
        saldo_pend_val = subtotal_val - v_abonos_monto
        
        totals_data = [
            [Paragraph("SUBTOTAL", cell_left), Paragraph(f"{subtotal_val:,.2f}", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
            [Paragraph("IMPUESTO", cell_left), Paragraph("0,00", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
            [Paragraph("TOTAL", cell_left), Paragraph(f"{subtotal_val:,.2f}", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
            [Paragraph("<b>SALDO PENDIENTE</b>", cell_left), Paragraph(f"<b>S/. {saldo_pend_val:,.2f}</b>", ParagraphStyle('TRB', alignment=TA_RIGHT, fontSize=11, fontName='Helvetica-Bold'))]
        ]
        t_totals = Table(totals_data, colWidths=[110, 110])
        t_totals.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-2), 0.3, rc.HexColor('#EEE')),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        
        summary_layout = [
            [Paragraph("Gracias por elegirnos como tus aliados tecnológicos.", ParagraphStyle('Thx', fontSize=9, textColor=rc.HexColor('#555'))),
             t_totals]
        ]
        t_summary = Table(summary_layout, colWidths=[260, 220])
        t_summary.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        elems_w.append(t_summary)
        elems_w.append(Spacer(1, 10))
        
        # --- 6. Resumen de Impuestos ---
        impuestos_headers = [Paragraph(f"<b>{c}</b>", ParagraphStyle('IH', fontSize=7, leading=8, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER)) for c in 
                             ["TASA", "IMPUESTOS DE", "BASE IMPONIBLE"]]
        impuestos_values = [Paragraph(v, ParagraphStyle('IV', fontSize=8, leading=9, alignment=TA_CENTER)) for v in 
                            ["IGV de 0%", "0,00", f"{subtotal_val:,.2f}"]]
        
        t_impuestos = Table([impuestos_headers, impuestos_values], colWidths=[120, 180, 180])
        t_impuestos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
            ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        elems_w.append(Paragraph("<b>RESUMEN DE IMPUESTOS</b>", ParagraphStyle('RITitle', fontSize=8, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=3)))
        elems_w.append(t_impuestos)
        elems_w.append(Spacer(1, 10))
        
        # --- 7. Detalle de Abonos Amortizados ---
        if not abonos_w.empty:
            elems_w.append(Paragraph("<b>ABONOS RECIBIDOS EN LA SEMANA</b>", ParagraphStyle('ABTitle', fontSize=8, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=3)))
            abonos_headers = [Paragraph(f"<b>{c}</b>", ParagraphStyle('AH', fontSize=7, leading=8, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER)) for c in 
                              ["FECHA", "REFERENCIA / CANAL BANCARIO", "IMPORTE"]]
            abonos_rows = [abonos_headers]
            for _, r in abonos_w.sort_values('date_pe').iterrows():
                abonos_rows.append([
                    Paragraph(r['date_pe'].strftime('%d/%m/%Y'), cell_style),
                    Paragraph(str(r['metodo']), cell_left),
                    Paragraph(f"S/. {r['amount']:,.2f}", cell_style)
                ])
            t_abonos_pdf = Table(abonos_rows, colWidths=[100, 260, 120])
            t_abonos_pdf.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            elems_w.append(t_abonos_pdf)
            elems_w.append(Spacer(1, 15))
        else:
            elems_w.append(Spacer(1, 10))
        
        # --- 7. Footer Pago ---
        elems_w.append(Paragraph("Enviar comprobante de pago a hola@chambadigital.la", ParagraphStyle('FInstr', fontSize=9, alignment=TA_CENTER, textColor=rc.HexColor('#555'))))
        
        doc_w.build(elems_w)
        pdf_bytes = buffer.getvalue()
        
        st.download_button(
            label="⬇️ Descargar Reporte Semanal PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
            key=f"dl_pdf_{w_start.strftime('%Y%m%d')}"
        )

# ═══ FOOTER ═══
st.markdown(f"""
<div style="text-align:center;padding:1.5rem;color:{text2};font-size:0.8rem;border-top:1px solid {border};margin-top:2rem;">
    🏢 Chamba Digital — No vendemos humo, vendemos Ingeniería &nbsp;·&nbsp; {db_status}
</div>
""", unsafe_allow_html=True)
