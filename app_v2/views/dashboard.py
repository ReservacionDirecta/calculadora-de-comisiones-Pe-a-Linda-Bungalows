# views/dashboard.py - Bento KPIs + ROI + Insights + Alertas
import streamlit as st
from components import bento_kpi, alert_box

def render(k, t, show_usd=False, usd_rate=3.6):
    """k = dict de KPIs de data.calc_kpis(), t = theme dict"""
    st.markdown("## 🏝️ Resumen del Período")

    def fmt_pen(val):
        return f"S/ {val:,.2f}"

    def fmt_usd(val):
        return f"$ {val / usd_rate:,.2f}"

    def fmt_both(val):
        if show_usd:
            return f"{fmt_pen(val)} ({fmt_usd(val)})"
        return fmt_pen(val)

    # ─── Bento Grid (5 cards) ───
    st.markdown('<div class="bento-grid">', unsafe_allow_html=True)

    cols = st.columns(5)
    with cols[0]:
        sub_vendido = f"{k['tx']} tx · {fmt_both(k['tb_sirvoy'])}" if show_usd else f"{k['tx']} transacciones Sirvoy"
        bento_kpi("📈 Vendido", k["tb_sirvoy"], sub_vendido, t["primary"])
    with cols[1]:
        confirmado = k["tb_plataformas"]
        sub_confirm = fmt_both(confirmado) if show_usd else f"{confirmado/k['tb_sirvoy']*100:.1f}% del vendido"
        bento_kpi("✅ Confirmado", confirmado, sub_confirm, t["seafoam"])
    with cols[2]:
        pend = max(0, k["tb_sirvoy"] - k["tb_plataformas"])
        sub_pend = fmt_both(pend) if show_usd else f"Tarjeta sin confirmar"
        bento_kpi("⏳ Por Confirmar", pend, sub_pend, t["coral"] if pend > 0 else t["seafoam"])
    with cols[3]:
        sub_costos = fmt_both(k["total_costos"]) if show_usd else f"FB {k['costo_fb']:,.0f} · SV {k['costo_sv']:,.0f} · Asis {k['costo_as']:,.0f}"
        bento_kpi("💸 Costos", k["total_costos"], sub_costos, t["sun"])
    with cols[4]:
        sub_comision = fmt_both(k["comision_desde_mar"]) if show_usd else "5% desde 03/03/2026"
        bento_kpi("📊 Comisión Acum.", k["comision_desde_mar"], sub_comision, "#8b5cf6")

    st.markdown("</div>", unsafe_allow_html=True)

    # ─── ROI Grid ───
    st.markdown("### 📊 ROI — Retorno de Inversión (Período)")
    st.markdown('<div class="bento-grid">', unsafe_allow_html=True)

    roi_pct_val = k.get("roi_periodo_pct", 0)
    ganancia_val = k.get("ganancia_periodo", 0)
    inversion_val = k.get("inversion_periodo", 0)
    x_sol_val = k.get("roi_periodo_x_sol", 0)

    roi_cols = st.columns(4)
    with roi_cols[0]:
        roi_color = t["seafoam"] if roi_pct_val > 0 else t["coral"]
        roi_label = f"+{roi_pct_val:,.1f}%" if roi_pct_val > 0 else f"{roi_pct_val:,.1f}%"
        ganancia_sub = fmt_both(ganancia_val) if show_usd else f"Ganancia neta: {fmt_pen(ganancia_val)}"
        bento_kpi("🎯 ROI Período", roi_label, ganancia_sub, roi_color, fmt="{}")
    with roi_cols[1]:
        sub_x_sol = f"Por cada {fmt_pen(1)} invertido" if not show_usd else f"Por cada $ 1 invertido (S/ {usd_rate:.2f})"
        bento_kpi("💰 Por S/ 1 invertido", f"S/ {x_sol_val:,.2f}", sub_x_sol, t["primary"], fmt="{}")
    with roi_cols[2]:
        sub_inv = fmt_both(inversion_val) if show_usd else f"Comisión {fmt_both(k['comision'])} + Costos {fmt_both(k['total_costos'])}"
        bento_kpi("📥 Inversión Total", inversion_val, sub_inv, t["sun"])
    with roi_cols[3]:
        sub_neto = fmt_both(k["tb_sirvoy"]) if show_usd else "Ventas netas del período"
        bento_kpi("📈 Neto Sirvoy", k["tb_sirvoy"], sub_neto, t["seafoam"])

    st.markdown("</div>", unsafe_allow_html=True)

    # ─── Saldo Pendiente ───
    saldo = k["saldo_pendiente"]
    if saldo > 0:
        sub_saldo = f"Adeudado {fmt_both(k['adeudado'])} − Abonos {fmt_both(k['total_abonos'])}" if show_usd else f"Adeudado {fmt_pen(k['adeudado'])} - Abonos {fmt_pen(k['total_abonos'])}"
        bento_kpi("💰 SALDO PENDIENTE (Deuda)", saldo, sub_saldo, t["coral"])
    else:
        st.success(f"✅ **Deuda saldada** — Abonos cubren el total adeudado ({fmt_pen(k['total_abonos'])} ≥ {fmt_pen(k['adeudado'])})")

    # ─── Insights y Análisis ───
    st.markdown("---")
    st.markdown("### 🧠 Insights y Análisis")
    fi_k = k.get('fi', None)
    ff_k = k.get('ff', None)
    if fi_k and ff_k:
        st.caption(f"Período: {fi_k.strftime('%d/%m/%Y')} a {ff_k.strftime('%d/%m/%Y')}")
    for insight in k.get("insights", []):
        st.markdown(f"- {insight}")

    # ─── Desglose de Eficiencia ───
    if k["tb_sirvoy"] > 0:
        st.markdown("### 📉 Eficiencia del Negocio")
        eff_cols = st.columns(4)
        with eff_cols[0]:
            comision_ratio = (k["comision"] / k["tb_sirvoy"] * 100) if k["tb_sirvoy"] > 0 else 0
            st.metric("Costo Comisión", f"{comision_ratio:.1f}%", f"{fmt_both(k['comision'])} del bruto")
        with eff_cols[1]:
            cost_ratio = (k["total_costos"] / k["tb_sirvoy"] * 100) if k["tb_sirvoy"] > 0 else 0
            st.metric("Costo Operativo", f"{cost_ratio:.1f}%", f"{fmt_both(k['total_costos'])} del bruto")
        with eff_cols[2]:
            total_ratio = comision_ratio + cost_ratio
            st.metric("Costo Total", f"{total_ratio:.1f}%", "Comisión + Operativos del bruto")
        with eff_cols[3]:
            cr_pct = k.get("costos_recibido_pct", 0)
            cr_color = "🔴" if cr_pct > 30 else "🟡" if cr_pct > 15 else "🟢"
            st.metric("Costos / Recibido", f"{cr_pct:.1f}%",
                       f"{cr_color} costos sobre ingresos netos (S/ {k['tb_recibido']:,.0f})")

    # ─── Alertas de atención ───
    st.markdown("---")
    st.markdown("### ⚠️ ¿Qué necesita atención?")

    if k["lk"] > 0:
        alert_box(
            "📌 PAGOS CON TARJETA POR CONFIRMAR",
            f"""
            **{fmt_both(k['lk'])}** en ventas con tarjeta Sirvoy aún no tienen respaldo en plataformas
            (Izipay, Culqi, Openpay).<br>
            <small>Estos montos suelen estar en los reportes POS del hotel.
            Si ya los recibiste por correo, súbelos en la pestaña <b>📤 POS</b>.</small>
            """,
        )

    if k["total_ret"] > 0:
        pend_count = len(k["pendientes_link"])
        alert_box(
            "🔗 LINKS DE PAGO PENDIENTES",
            f"""
            **{pend_count} links** por {fmt_both(k['total_ret'])} están marcados como 'pendiente'.
            <br><small>Verifica en tu banco y márcalos como depositados en la pestaña Conciliación.</small>
            """,
        )

    if k["lk"] == 0 and k["total_ret"] == 0:
        st.success("✅ Todo al día — No hay pendientes de atención urgente.")
