# views/calculadora_deuda.py - Calculadora de Deuda v3
# Muestra de forma clara: Ventas → Comisión + Costos - Abonos = Deuda Vigente
# Consulta MongoDB directamente (evita bug timezone de data.py)
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, date, timedelta

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

    # ─── SECCIÓN 6: Deuda Futura (reservas confirmadas con pago pendiente) ───
    # Lee la colección comisiones_futuras (reservas futuras con su comisión calculada al 5%).
    try:
        cli_f = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db_f = cli_f['pena_linda']
        res_fut = db_f['comisiones_futuras'].find_one({'tipo': 'resumen'})
        cli_f.close()
        if res_fut:
            fut_monto = float(res_fut.get('monto_pendiente', 0.0))
            fut_comision = float(res_fut.get('comision', 0.0))
            fut_count = int(res_fut.get('reservas', 0))
        else:
            fut_monto = fut_comision = 0.0
            fut_count = 0
    except Exception:
        fut_monto = fut_comision = 0.0
        fut_count = 0

    # Total combinado: deuda vigente (resto) + deuda futura (comisión de reservas pendientes)
    total_pendiente_pagar = max(0.0, resto) + fut_comision

    st.markdown(f"""
    <hr style="{line_style}">
    <div class="calc-section">
        <div class="calc-section-title">🔮 Deuda Futura (Reservas Confirmadas)</div>
        <div class="calc-row">
            <span class="label">Reservas con pago pendiente</span>
            <span class="value">{fut_count} reservas</span>
        </div>
        <div class="calc-row">
            <span class="label">Monto pendiente por cobrar</span>
            <span class="value" style="color:#f59e0b;font-weight:600;">S/ {fut_monto:,.2f}</span>
        </div>
        <div class="calc-row">
            <span class="label">Comisión 5% calculada</span>
            <span class="value" style="color:#8b5cf6;font-weight:700;">S/ {fut_comision:,.2f}</span>
        </div>
    </div>
    <hr style="{line_style}">
    <div class="calc-section" style="margin-top:12px;">
        <div class="calc-section-title" style="font-size:0.85rem;">🧾 TOTAL PENDIENTE POR PAGAR</div>
        <div class="calc-row total" style="padding-top:4px;">
            <span class="label">Deuda Vigente + Deuda Futura</span>
            <span class="value">S/ {total_pendiente_pagar:,.2f}</span>
        </div>
        <div style="text-align:center;margin-top:6px;font-size:0.78rem;color:{muted};">
            S/ {max(0.0, resto):,.2f} (vigente) + S/ {fut_comision:,.2f} (futura)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Resumen ejecutivo ───
    st.markdown("</div>", unsafe_allow_html=True)

    # Métricas de deuda futura (fuera de la tarjeta, junto al resumen ejecutivo)
    if fut_comision > 0 or fut_monto > 0:
        st.markdown("---")
        st.markdown("#### 🔮 Deuda Futura — Reservas Confirmadas")
        st.caption("Comisión 5% sobre el monto pendiente de cobro de reservas futuras (fuente: comisiones_futuras).")
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            st.metric("🏨 Reservas Pendientes", f"{fut_count}")
        with cf2:
            st.metric("💵 Monto por Cobrar", f"S/ {fut_monto:,.2f}")
        with cf3:
            st.metric("💰 Comisión Futura 5%", f"S/ {fut_comision:,.2f}")

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

    # ─── ACUMULADOS DEL PERÍODO SELECCIONADO ───
    st.markdown("---")
    st.markdown(f"### 📅 Acumulados del Período: {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}")

    # Consultar MongoDB para el período seleccionado
    try:
        cli_p = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db_p = cli_p['pena_linda']

        fi_dt = datetime.combine(fi, datetime.min.time())
        ff_dt = datetime.combine(ff, datetime.max.time())

        # Sirvoy del período
        sirvoy_periodo = list(db_p['pagos'].find({
            'fuente': 'Sirvoy',
            'fecha': {'$gte': fi_dt, '$lte': ff_dt}
        }))
        montos_sv_p = [d['monto'] for d in sirvoy_periodo]
        bruto_p = sum(m for m in montos_sv_p if m > 0)
        reversiones_p = sum(m for m in montos_sv_p if m < 0)
        neto_p = bruto_p + reversiones_p
        comision_p = neto_p * 0.05

        # Costos del período
        costos_periodo = list(db_p['pagos'].find({
            'fuente': {'$in': ['Costo FB Ads', 'Costo Sirvoy', 'Costo Asistente', 'Costo Extra']},
            'fecha': {'$gte': fi_dt, '$lte': ff_dt}
        }))
        total_costos_p = sum(d['monto'] for d in costos_periodo)

        # Abonos del período
        abonos_periodo = list(db_p['cobros'].find({
            'tipo': 'abono',
            'fecha': {'$gte': fi_dt, '$lte': ff_dt}
        }))
        total_abonos_p = sum(d['monto'] for d in abonos_periodo)
        abonos_count_p = len(abonos_periodo)

        cli_p.close()

        # Mostrar métricas del período
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            st.metric("📊 Ventas Netas", f"S/ {neto_p:,.2f}", help="Sirvoy neto en el período seleccionado")
        with col_p2:
            st.metric("💰 Comisión 5%", f"S/ {comision_p:,.2f}", help="5% sobre neto del período")
        with col_p3:
            st.metric("💸 Costos", f"S/ {total_costos_p:,.2f}", help="Costos operativos del período")
        with col_p4:
            st.metric("💳 Abonos", f"S/ {total_abonos_p:,.2f}", help=f"{abonos_count_p} registros en el período")

        # Desglose del período
        adeudado_p = comision_p + total_costos_p
        saldo_p = max(0.0, adeudado_p - total_abonos_p)

        col_pd1, col_pd2 = st.columns(2)
        with col_pd1:
            st.markdown("**Resumen Período:**")
            st.write(f"- Comisión + Costos: **S/ {adeudado_p:,.2f}**")
            st.write(f"- Abonos recibidos: **S/ {total_abonos_p:,.2f}**")
            st.write(f"- Saldo período: **S/ {saldo_p:,.2f}**")
        with col_pd2:
            st.markdown("**Comparativa con Histórico:**")
            st.write(f"- Histórico (desde 03/03): **S/ {resto:,.2f}**")
            st.write(f"- Período seleccionado: **S/ {saldo_p:,.2f}**")
            diff = resto - saldo_p
            st.write(f"- Diferencia: **S/ {diff:,.2f}**")

            # ─── Comisiones futuras pendientes (reservas confirmadas con pago pendiente) ───
            try:
                cli_f = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
                res_fut = cli_f['pena_linda']['comisiones_futuras'].find_one({'tipo': 'resumen'})
                cli_f.close()
                if res_fut:
                    fut_monto_p = float(res_fut.get('monto_pendiente', 0.0))
                    fut_comision_p = float(res_fut.get('comision', 0.0))
                    fut_count_p = int(res_fut.get('reservas', 0))
                    st.markdown("**🔮 Comisiones Futuras Pendientes:**")
                    st.write(f"- Reservas con pago pendiente: **{fut_count_p}**")
                    st.write(f"- Monto por cobrar: **S/ {fut_monto_p:,.2f}**")
                    st.write(f"- Comisión 5% calculada: **S/ {fut_comision_p:,.2f}**")
            except Exception:
                pass

    except Exception as e:
        st.error(f"Error calculando período: {e}")

    # ─── Exportar Resumen de Deuda ───
    st.markdown("#### 📤 Exportar Resumen de Deuda")
    resumen = pd.DataFrame([{
        "Concepto": "Ventas Bruto",
        "Monto": bruto
    }, {
        "Concepto": "Reversiones",
        "Monto": reversiones
    }, {
        "Concepto": "Ventas Netas",
        "Monto": neto
    }, {
        "Concepto": "Comisión Chamba 5%",
        "Monto": comision
    }, {
        "Concepto": "Costo Facebook Ads",
        "Monto": costo_fb
    }, {
        "Concepto": "Costo Sirvoy",
        "Monto": costo_sv
    }, {
        "Concepto": "Costo Asistente",
        "Monto": costo_as
    }, {
        "Concepto": "Costo Extra",
        "Monto": costo_ex
    }, {
        "Concepto": "Total Costos",
        "Monto": total_costos
    }, {
        "Concepto": "Saldo Base",
        "Monto": saldo_base
    }, {
        "Concepto": "Total Adeudado",
        "Monto": adeudado
    }, {
        "Concepto": "Total Abonado",
        "Monto": abonos_total
    }, {
        "Concepto": "Saldo Pendiente",
        "Monto": resto
    }])
    from components import export_buttons
    exp1, exp2 = st.columns([1, 3])
    with exp1:
        st.caption(f"Al {datetime.now().strftime('%d/%m/%Y')}")
    with exp2:
        export_buttons("deuda_res", resumen, "20260303", datetime.now().strftime('%Y%m%d'), "Resumen_Deuda")

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

    # ═══════════════════════════════════════════════
    # 📅 REPORTES SEMANALES CONSOLIDADOS
    # ═══════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📅 Reportes Semanales Consolidados (Martes a Lunes)")
    st.caption("Genera y descarga el reporte semanal de ventas, comisiones, costos y abonos.")

    start_w = date(2026, 3, 3)
    end_w = datetime.now().date()

    weeks = []
    cw = start_w
    while cw <= end_w:
        ws, we = cw, cw + timedelta(days=6)
        weeks.append((ws, we, f"Semana: {ws.strftime('%d/%m/%Y')} al {we.strftime('%d/%m/%Y')}"))
        cw += timedelta(days=7)
    weeks.reverse()

    sel = st.selectbox("Seleccionar período semanal:", options=range(len(weeks)),
                        format_func=lambda i: weeks[i][2], index=1, key="w_sel_debt")

    if sel is not None:
        ws, we, wl = weeks[sel]
        # Cargar data de la semana
        try:
            cli_w = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
            dbw = cli_w['pena_linda']
            docs_w = list(dbw['pagos'].find({
                'fuente': 'Sirvoy',
                'fecha': {'$gte': datetime(ws.year, ws.month, ws.day),
                           '$lte': datetime(we.year, we.month, we.day, 23, 59, 59)}
            }))
            costos_w = list(dbw['pagos'].find({
                'fuente': {'$in': ['Costo FB Ads', 'Costo Sirvoy', 'Costo Asistente', 'Costo Extra']},
                'fecha': {'$gte': datetime(ws.year, ws.month, ws.day),
                           '$lte': datetime(we.year, we.month, we.day, 23, 59, 59)}
            }))
            abonos_w = list(dbw['cobros'].find({
                'tipo': 'abono',
                'fecha': {'$gte': datetime(ws.year, ws.month, ws.day),
                           '$lte': datetime(we.year, we.month, we.day, 23, 59, 59)}
            }))
            cli_w.close()
        except Exception as e:
            st.error(f"Error cargando datos semanales: {e}")
            docs_w = costos_w = abonos_w = []

        m_sv = sum(d['monto'] for d in docs_w)
        v_bruto = sum(d['monto'] for d in docs_w if d['monto'] > 0)
        v_neg = sum(d['monto'] for d in docs_w if d['monto'] < 0)
        m_cost = sum(d['monto'] for d in costos_w)
        m_abon = sum(d['monto'] for d in abonos_w)
        m_com = (v_bruto + v_neg) * 0.05

        cw1, cw2, cw3, cw4 = st.columns(4)
        with cw1:
            st.metric("💰 Ventas Bruto", f"S/ {v_bruto:,.2f}", f"{len(docs_w)} tx")
        with cw2:
            st.metric("📋 Comisión 5%", f"S/ {m_com:,.2f}")
        with cw3:
            st.metric("💸 Costos", f"S/ {m_cost:,.2f}")
        with cw4:
            st.metric("💳 Abonos", f"S/ {m_abon:,.2f}")

        v_neto = v_bruto + v_neg
        st.metric("📊 Ventas Netas (Bruto + Reversiones)",
                   f"S/ {v_neto:,.2f}",
                   f"{len([d for d in docs_w if d['monto'] < 0])} rev, S/ {v_neg:,.2f}")

        dw1, dw2 = st.columns(2)
        with dw1:
            st.markdown("##### 💸 Gastos de la Semana")
            if costos_w:
                cdf = pd.DataFrame(costos_w)
                cdf['Fecha'] = pd.to_datetime(cdf['fecha']).dt.strftime('%d/%m/%Y')
                cdf['Monto'] = cdf['monto'].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(cdf[['Fecha', 'fuente', 'monto']].rename(
                    columns={'fuente': 'Concepto', 'monto': 'Monto'}), hide_index=True, use_container_width=True)
            else:
                st.info("Sin gastos en esta semana.")
        with dw2:
            st.markdown("##### 💳 Abonos de la Semana")
            if abonos_w:
                adf = pd.DataFrame(abonos_w)
                adf['Fecha'] = pd.to_datetime(adf['fecha']).dt.strftime('%d/%m/%Y')
                adf['Monto'] = adf['monto'].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(adf[['Fecha', 'Monto', 'detalle']].rename(
                    columns={'detalle': 'Concepto'}), hide_index=True, use_container_width=True)
            else:
                st.info("Sin abonos en esta semana.")

        # Tabla resumen para exportar
        reporte_df = pd.DataFrame([
            {"Concepto": "Ventas Bruto", "Monto": v_bruto},
            {"Concepto": "Reversiones", "Monto": v_neg},
            {"Concepto": "Ventas Netas", "Monto": v_bruto + v_neg},
            {"Concepto": "Comisión Chamba 5%", "Monto": m_com},
            {"Concepto": "Costos Operativos", "Monto": m_cost},
            {"Concepto": "Abonos Recibidos", "Monto": m_abon},
        ])
        from components import generate_weekly_pdf
        pdf_bytes = generate_weekly_pdf(ws, we, v_bruto + v_neg, v_neg, costos_w, abonos_w)
        st.download_button(
            "⬇️ Descargar Reporte Semanal PDF",
            data=pdf_bytes,
            file_name=f"Reporte_Semanal_{ws.strftime('%Y%m%d')}_{we.strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"dl_pdf_sem_{ws.strftime('%Y%m%d')}"
        )
        export_buttons(f"semanal_{ws.strftime('%Y%m%d')}", reporte_df,
                        ws.strftime('%Y%m%d'), we.strftime('%Y%m%d'),
                        f"Reporte_Semanal_{ws.strftime('%Y%m%d')}")
