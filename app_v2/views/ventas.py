# views/ventas.py - Ventas: gráficos, detalle, comisiones
import streamlit as st
import pandas as pd
import plotly.express as px
from components import export_buttons, get_yscale

def render(df, k, t, fi, ff, escala_log):
    st.markdown("## 📊 Ventas Generadas")

    v_tab1, v_tab2, v_tab3 = st.tabs(["📈 Ventas", "📄 Detalle", "💰 Comisiones 5%"])

    # ── Tab 1: Gráficos ──
    with v_tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="shad-card">', unsafe_allow_html=True)
            st.markdown("**📈 Ventas Diarias**")
            sv = k["sv_sales"]
            if not sv.empty:
                d = sv.set_index("date").resample("D")["amount"].sum().reset_index()
                fig = px.bar(d, x="date", y="amount", color_discrete_sequence=["#3b82f6"],
                             labels={"date": "", "amount": "S/"})
                fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                                  plot_bgcolor=t["bg"], paper_bgcolor=t["bg_card"], font_color=t["text"])
                fig.update_yaxes(tickprefix="S/ ", **get_yscale(escala_log))
                fig.update_xaxes(gridcolor=t["border"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin ventas en el período")
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="shad-card">', unsafe_allow_html=True)
            st.markdown("**🥧 Distribución por Método**")
            if not sv.empty:
                pt = sv.groupby("tipo_pago")["amount"].sum().reset_index()
                cmap = {"Tarjeta": "#3b82f6", "Transferencia": "#10b981", "Efectivo": "#f59e0b", "Otros": "#a1a1aa"}
                fig = px.pie(pt, values="amount", names="tipo_pago", color="tipo_pago", color_discrete_map=cmap)
                fig.update_traces(textposition="inside", textinfo="label+percent",
                                  marker=dict(line=dict(color=t["bg_card"], width=2)))
                fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
                                  plot_bgcolor=t["bg"], paper_bgcolor=t["bg_card"], font_color=t["text"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin ventas en el período")
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 2: Detalle de transacciones ──
    with v_tab2:
        st.markdown("**📋 Transacciones del Período**")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search = st.text_input("🔍 Buscar", "", placeholder="Método, referencia, ID...", key="ven_search")
        with col_f2:
            solo_lk = st.checkbox("Solo Links de Pago", False, key="ven_solo_lk")

        det = k["sv_sales"].copy()
        if solo_lk:
            det = det[det["es_link"] == True]
        if search:
            det = det[det["method"].str.contains(search, case=False, na=False) |
                      det["referencia"].astype(str).str.contains(search, case=False, na=False) |
                      det["metodo"].astype(str).str.contains(search, case=False, na=False)]

        st.caption(f"{len(det)} registros  ·  S/ {det['amount'].sum():,.2f}")
        export_buttons("ven_det", det, fi, ff, "Transacciones")

        if not det.empty:
            disp = det.sort_values("date_pe", ascending=False).copy()
            disp["Fecha"] = disp["date_pe"].dt.strftime("%d/%m/%Y %H:%M")
            disp["Monto S/"] = disp["amount"].apply(lambda x: f"{x:,.2f}")
            disp["Origen"] = disp["fuente"]
            st.dataframe(
                disp[["Fecha", "Origen", "Monto S/", "tipo_pago", "method"]].rename(
                    columns={"tipo_pago": "Tipo", "method": "Detalle"}
                ),
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("Sin registros")

    # ── Tab 3: Comisiones ──
    with v_tab3:
        st.markdown("**💰 Comisión Chamba Digital (5% sobre ventas Sirvoy)**")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.metric("Vendido (Período)", f"S/ {k['tb_sirvoy']:,.2f}")
        with col_c2:
            st.metric("Comisión (Período)", f"S/ {k['comision']:,.2f}")
        with col_c3:
            st.metric("Comisión Acumulada (desde 03/03)", f"S/ {k['comision_desde_mar']:,.2f}")

        st.markdown("---")
        st.markdown("**📈 Evolución**")
        sv_c = k["sv_sirvoy"]
        if not sv_c.empty:
            sv_c = sv_c.copy()
            sv_c["Comisión"] = sv_c["amount"] * 0.05

            vista = st.radio("Vista:", ["📅 Diaria", "📆 Semanal", "📊 Mensual"], horizontal=True, key="com_vista")

            if vista == "📅 Diaria":
                grp = sv_c.set_index("date_pe").resample("D")["Comisión"].sum().reset_index()
                grp.columns = ["Fecha", "Comisión"]
                x = "Fecha"
            elif vista == "📆 Semanal":
                sv_c["sem"] = sv_c["date_pe"].dt.strftime("%Y-W%U")
                grp = sv_c.groupby("sem")["Comisión"].sum().reset_index()
                grp.columns = ["Semana", "Comisión"]
                x = "Semana"
            else:
                sv_c["mes"] = sv_c["date_pe"].dt.strftime("%Y-%m")
                grp = sv_c.groupby("mes")["Comisión"].sum().reset_index()
                grp.columns = ["Mes", "Comisión"]
                x = "Mes"

            fig = px.bar(grp, x=x, y="Comisión", color_discrete_sequence=["#3b82f6"],
                         labels={x: "", "Comisión": "S/"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                              plot_bgcolor=t["bg"], paper_bgcolor=t["bg_card"], font_color=t["text"])
            fig.update_yaxes(tickprefix="S/ ", **get_yscale(escala_log))
            fig.update_xaxes(gridcolor=t["border"])
            st.plotly_chart(fig, use_container_width=True)

            cm1, cm2, cm3 = st.columns(3)
            with cm1:
                st.metric(f"Total {vista.split()[1]}", f"S/ {grp['Comisión'].sum():,.2f}")
            with cm2:
                st.metric("Promedio", f"S/ {grp['Comisión'].mean():,.2f}")
            with cm3:
                st.metric("Máximo", f"S/ {grp['Comisión'].max():,.2f}")

        # Detalle de comisiones
        st.markdown("---")
        st.markdown("**📋 Detalle por Transacción**")
        if not sv_c.empty:
            sv_c["5%"] = sv_c["amount"] * 0.05
            sv_c["Fecha"] = sv_c["date_pe"].dt.strftime("%d/%m/%Y %H:%M")
            sv_c["Bruto"] = sv_c["amount"].apply(lambda x: f"S/ {x:,.2f}")
            sv_c["Comisión"] = sv_c["5%"].apply(lambda x: f"S/ {x:,.2f}")
            st.dataframe(
                sv_c[["Fecha", "transaction_id", "metodo", "Bruto", "Comisión"]].rename(
                    columns={"transaction_id": "ID", "metodo": "Detalle"}
                ),
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("Sin transacciones Sirvoy en el período")
