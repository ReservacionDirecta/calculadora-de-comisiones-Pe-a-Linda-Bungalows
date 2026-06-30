# views/dashboard.py - Bento KPIs + Alertas de atención
import streamlit as st
from components import bento_kpi, alert_box

def render(k, t):
    """k = dict de KPIs de data.calc_kpis(), t = theme dict"""
    st.markdown("## 🏝️ Resumen del Período")

    # ─── Bento Grid (5 cards) ───
    st.markdown('<div class="bento-grid">', unsafe_allow_html=True)

    cols = st.columns(5)
    with cols[0]:
        bento_kpi("📈 Vendido", k["tb_sirvoy"], f"{k['tx']} transacciones Sirvoy", t["primary"])
    with cols[1]:
        bento_kpi("✅ Recibido", k["tb_recibido"], "Plataformas + Transf/Efectivo", t["seafoam"])
    with cols[2]:
        pend = k["tb_sirvoy"] - k["tb_recibido"]
        bento_kpi("⏳ Pendiente", pend, f"Incluye S/ {k['lk']:,.0f} tarjeta por confirmar", t["coral"] if pend > 0 else t["seafoam"])
    with cols[3]:
        bento_kpi("💸 Costos", k["total_costos"], f"FB {k['costo_fb']:,.0f} · SV {k['costo_sv']:,.0f} · Asis {k['costo_as']:,.0f}", t["sun"])
    with cols[4]:
        bento_kpi("📊 Comisión Acum.", k["comision_desde_mar"], "5% desde 03/03/2026", "#8b5cf6")

    st.markdown("</div>", unsafe_allow_html=True)

    # ─── Saldo Pendiente ───
    saldo = k["saldo_pendiente"]
    if saldo > 0:
        bento_kpi("💰 SALDO PENDIENTE (Deuda)", saldo, f"Adeudado S/ {k['adeudado']:,.2f} - Abonos S/ {k['total_abonos']:,.2f}", t["coral"])
    else:
        st.success(f"✅ **Deuda saldada** — Abonos cubren el total adeudado ({k['total_abonos']:,.2f} ≥ {k['adeudado']:,.2f})")

    # ─── Alertas de atención ───
    st.markdown("---")
    st.markdown("### ⚠️ ¿Qué necesita atención?")

    # Alerta 1: POS / Tarjeta pendiente
    if k["lk"] > 0:
        alert_box(
            "📌 PAGOS CON TARJETA POR CONFIRMAR",
            f"""
            **S/ {k['lk']:,.2f}** en ventas con tarjeta Sirvoy aún no tienen respaldo en plataformas 
            (Izipay, Culqi, Openpay).<br>
            <small>Estos montos suelen estar en los reportes POS del hotel.
            Si ya los recibiste por correo, súbelos en la pestaña <b>📤 POS</b>.</small>
            """,
        )

    # Alerta 2: Links pendientes
    if k["total_ret"] > 0:
        pend_count = len(k["pendientes_link"])
        alert_box(
            "🔗 LINKS DE PAGO PENDIENTES",
            f"""
            **{pend_count} links** por S/ {k['total_ret']:,.2f} están marcados como 'pendiente'.
            <br><small>Verifica en tu banco y márcalos como depositados en la pestaña Conciliación.</small>
            """,
        )

    # Alerta 3: Sin alertas
    if k["lk"] == 0 and k["total_ret"] == 0:
        st.success("✅ Todo al día — No hay pendientes de atención urgente.")
