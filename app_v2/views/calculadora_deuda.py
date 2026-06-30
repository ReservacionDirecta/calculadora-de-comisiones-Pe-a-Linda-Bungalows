# views/calculadora_deuda.py - Calculadora de Deuda v3
# Muestra de forma clara: Ventas → Comisión + Costos - Abonos = Deuda Vigente
# Consulta MongoDB directamente (evita bug timezone de data.py)
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, date

DEBT_START = date(2026, 3, 3)

def render(df, k, t, fi, ff, MONGO_URL):
    """Calculadora de deuda: datos vivos desde MongoDB."""
    st.markdown("## 🧮 Calculadora de Deuda Vigente")
    st.caption("Acumulado desde el **03/03/2026** — Datos calculados en vivo desde MongoDB")

    # ─── Cargar datos frescos desde MongoDB ───
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db = cli['pena_linda']

        # Sirvoy desde 03/03
        sirvoy_docs = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'fecha': {'$gte': datetime(2026, 3, 3, 0, 0, 0)}
        }))
        # Costos desde 03/03 (excluye Saldo Base)
        costos_docs = list(db['pagos'].find({
            'fuente': {'$in': ['Costo FB Ads', 'Costo Sirvoy', 'Costo Asistente', 'Costo Extra']},
            'fecha': {'$gte': datetime(2026, 3, 3, 0, 0, 0)}
        }))
        # Saldo Base
        saldo_docs = list(db['pagos'].find({'fuente': 'Saldo Base'}))
        # Cobros (abonos)
        cobros_docs = list(db['cobros'].find({'tipo': 'abono'}))
        cli.close()
    except Exception as e:
        st.error(f"❌ Error conectando a MongoDB: {e}")
        return

    # ─── Calcular montos ───
    # Sirvoy
    montos_sv = [d['monto'] for d in sirvoy_docs]
    bruto = sum(m for m in montos_sv if m > 0)
    reversiones = sum(m for m in montos_sv if m < 0)
    neto = bruto + reversiones

    # Comisión
    comision = neto * 0.05

    # Costos
    costo_fb = sum(d['monto'] for d in costos_docs if d['fuente'] == 'Costo FB Ads')
    costo_sv = sum(d['monto'] for d in costos_docs if d['fuente'] == 'Costo Sirvoy')
    costo_as = sum(d['monto'] for d in costos_docs if d['fuente'] == 'Costo Asistente')
    costo_ex = sum(d['monto'] for d in costos_docs if d['fuente'] == 'Costo Extra')
    total_costos = costo_fb + costo_sv + costo_as + costo_ex

    # Saldo Base
    saldo_base = sum(d['monto'] for d in saldo_docs)

    # Abonos
    abonos_total = sum(d['monto'] for d in cobros_docs)
    abonos_count = len(cobros_docs)
    # Últimos 5 abonos
    cobros_ordenados = sorted(cobros_docs, key=lambda x: x.get('fecha', datetime.min), reverse=True)
    ultimos_abonos = cobros_ordenados[:5]

    # Deuda
    adeudado = saldo_base + comision + total_costos
    saldo = max(0.0, adeudado - abonos_total)

    # ─── Tema ───
    is_dark = st.session_state.get('is_dark', False)
    if is_dark:
        bg = "#1e1e2e"
        card_bg = "#2a2a3e"
        text = "#f0f0f0"
        muted = "#a0a0b0"
        accent = "#f59e0b"
        num_color = "#e0e0f0"
    else:
        bg = "#f8f9fa"
        card_bg = "#ffffff"
        text = "#1e293b"
        muted = "#64748b"
        accent = "#dc2626"
        num_color = "#1e293b"

    line_style = f"border: none; border-top: 1px solid {'#444' if is_dark else '#ddd'}; margin: 8px 0;"

    # ─── LAYOUT: Calculadora tipo recibo ───
    st.markdown(f"""
    <style>
    .calc-card {{
        background: {card_bg};
        border-radius: 16px;
        padding: 32px 40px;
        max-width: 520px;
        margin: 0 auto;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
        color: {text};
    }}
    .calc-card h2 {{
        font-family: system-ui, -apple-system, sans-serif;
        text-align: center;
        margin: 0 0 4px 0;
        font-size: 1.3rem;
        color: {accent};
    }}
    .calc-card .sub {{
        text-align: center;
        font-size: 0.75rem;
        color: {muted};
        margin-bottom: 20px;
        font-family: system-ui, -apple-system, sans-serif;
    }}
    .calc-row {{
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 0.92rem;
    }}
    .calc-row .label {{
        color: {muted};
    }}
    .calc-row .value {{
        color: {num_color};
        font-weight: 500;
    }}
    .calc-row.total {{
        font-weight: 700;
        font-size: 1.2rem;
        padding: 8px 0;
    }}
    .calc-row.total .value {{
        color: {accent};
    }}
    .calc-row.highlight {{
        background: {accent if not is_dark else '#3a3a5e'};
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px -12px;
        color: {'#fff' if not is_dark else text};
    }}
    .calc-row.highlight .label {{
        color: {'rgba(255,255,255,0.85)' if not is_dark else muted};
    }}
    .calc-row.highlight .value {{
        color: {'#fff' if not is_dark else text};
        font-size: 1.3rem;
    }}
    .calc-section {{
        margin: 12px 0;
    }}
    .calc-section-title {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: {accent};
        font-weight: 600;
        margin-bottom: 4px;
        font-family: system-ui, -apple-system, sans-serif;
    }}
    .abono-list {{
        font-size: 0.8rem;
        color: {muted};
        margin-top: 4px;
    }}
    .tag {{
        display: inline-block;
        background: {accent if not is_dark else '#444'};
        color: {'#fff' if not is_dark else text};
        font-size: 0.65rem;
        padding: 1px 6px;
        border-radius: 4px;
        margin-left: 6px;
        font-weight: 600;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Título
    st.markdown(f"""
    <div class="calc-card">
        <h2>🏝️ Peña Linda → Chamba Digital</h2>
        <div class="sub">Deuda Vigente · Acumulado 03/03/2026 → {datetime.now().strftime('%d/%m/%Y')}</div>
    """, unsafe_allow_html=True)

    # ─── SECCIÓN 1: Ventas Sirvoy ───
    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">📊 Ventas Sirvoy</div>
        <div class="calc-row">
            <span class="label">Bruto (solo positivos)</span>
            <span class="value">S/ {bruto:,.2f}</span>
        </div>
        <div class="calc-row">
            <span class="label">Reversiones (negativos)</span>
            <span class="value" style="color:#ef4444;">−S/ {abs(reversiones):,.2f}</span>
        </div>
        <hr style="{line_style}">
        <div class="calc-row" style="font-weight:600;">
            <span class="label">Neto Real</span>
            <span class="value">S/ {neto:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── SECCIÓN 2: Comisión ───
    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">💰 Comisión Chamba Digital (5%)</div>
        <div class="calc-row">
            <span class="label">5% × S/ {neto:,.2f}</span>
            <span class="value" style="color:#8b5cf6;font-weight:700;">S/ {comision:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── SECCIÓN 3: Costos ───
    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">💸 Costos Operativos</div>
        <div class="calc-row">
            <span class="label">📱 Facebook Ads</span>
            <span class="value">S/ {costo_fb:,.2f}</span>
        </div>
        <div class="calc-row">
            <span class="label">🖥️ Plataforma Sirvoy</span>
            <span class="value">S/ {costo_sv:,.2f}</span>
        </div>
        <div class="calc-row">
            <span class="label">👤 Asistente Virtual</span>
            <span class="value">S/ {costo_as:,.2f}</span>
        </div>
        <div class="calc-row">
            <span class="label">➕ Costos Extra</span>
            <span class="value">S/ {costo_ex:,.2f}</span>
        </div>
        <hr style="{line_style}">
        <div class="calc-row" style="font-weight:600;">
            <span class="label">Total Costos</span>
            <span class="value" style="color:#eab308;">S/ {total_costos:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── SECCIÓN 4: Saldo Base ───
    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">📋 Saldo Heredado (al 03/03/2026)</div>
        <div class="calc-row">
            <span class="label">Saldo Base QuickBooks</span>
            <span class="value">S/ {saldo_base:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── LÍNEA FINAL: Deuda Total ───
    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">🧮 Total Adeudado</div>
        <div class="calc-row total" style="padding-top:4px;">
            <span class="label">Saldo Base + Comisión + Costos</span>
            <span class="value">S/ {adeudado:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── SECCIÓN 5: Abonos ───
    abono_rows = ""
    for ab in ultimos_abonos:
        f = ab.get('fecha', '')
        if isinstance(f, datetime):
            f = f.strftime('%d/%m/%Y')
        m = ab.get('monto', 0)
        ref = ab.get('detalle', ab.get('concepto', ''))[:30]
        abono_rows += f'<div class="calc-row" style="font-size:0.82rem;"><span class="label">{f} {ref}</span><span class="value">S/ {m:,.2f}</span></div>'

    st.markdown(f"""
    <div class="calc-section">
        <div class="calc-section-title">💳 Abonos de Peña Linda ({abonos_count} registros)</div>
        <div class="calc-row">
            <span class="label">Total Abonado</span>
            <span class="value" style="color:#22c55e;">S/ {abonos_total:,.2f}</span>
        </div>
        <div class="abono-list">
            <div style="margin-top:6px;font-size:0.75rem;color:{muted};font-weight:500;">Últimos abonos:</div>
            {abono_rows}
        </div>
    </div>
    <hr style="{line_style}">
    """, unsafe_allow_html=True)

    # ─── RESULTADO FINAL ───
    resto = adeudado - abonos_total
    color_saldo = "#22c55e" if saldo == 0 else (accent if not is_dark else "#f87171")
    estado = "✅ DEUDA SALDADA" if saldo == 0 else "⚠️ DEUDA PENDIENTE" if resto > 0 else "💰 SALDO A FAVOR"

    st.markdown(f"""
    <div class="calc-section" style="margin-top:16px;">
        <div class="calc-section-title" style="font-size:0.85rem;">🔴 RESULTADO FINAL</div>
        <div class="calc-row highlight">
            <span class="label">Adeudado − Abonos</span>
            <span class="value" style="font-size:1.4rem;">S/ {resto:,.2f}</span>
        </div>
        <div style="text-align:center;margin-top:10px;font-size:1.1rem;font-weight:700;color:{color_saldo};">
            {estado}
        </div>
        <div style="text-align:center;margin-top:6px;font-size:0.8rem;color:{muted};">
            S/ {adeudado:,.2f} − S/ {abonos_total:,.2f} = S/ {resto:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Resumen ejecutivo ───
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Ventas Netas", f"S/ {neto:,.2f}")
    with col2:
        st.metric("💰 Comisión 5%", f"S/ {comision:,.2f}")
    with col3:
        st.metric("💸 Costos", f"S/ {total_costos:,.2f}")
    with col4:
        st.metric("💳 Abonos", f"S/ {abonos_total:,.2f}")

    # Desglose de costos extra (si hay)
    if costo_ex > 0:
        with st.expander("➕ Detalle de Costos Extra"):
            try:
                cli2 = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                extra_docs = list(cli2['pena_linda']['pagos'].find({
                    'fuente': 'Costo Extra',
                    'fecha': {'$gte': datetime(2026, 3, 3)}
                }))
                cli2.close()
                if extra_docs:
                    extra_df = pd.DataFrame(extra_docs)
                    extra_df['fecha_str'] = pd.to_datetime(extra_df['fecha']).dt.strftime('%d/%m/%Y')
                    extra_df['monto_str'] = extra_df['monto'].apply(lambda x: f"S/ {x:,.2f}")
                    st.dataframe(extra_df[['fecha_str', 'monto_str', 'concepto', 'detalle']].rename(
                        columns={'fecha_str': 'Fecha', 'monto_str': 'Monto', 'concepto': 'Concepto', 'detalle': 'Detalle'}
                    ), hide_index=True, use_container_width=True)
            except:
                pass
