# views/historial.py - Historial y conciliación con QuickBooks
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from components import export_buttons

def render(df, k, fi, ff, MONGO_URL):
    st.markdown("## 📋 Historial y Conciliación")
    st.write("Cruce entre facturas QuickBooks (comisiones + costos) y abonos registrados.")

    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        cobros = list(cli["pena_linda"]["cobros"].find({}))
        cli.close()
        cobros_df = pd.DataFrame(cobros)

        if cobros_df.empty:
            st.info("No hay datos en cobros.")
            return

        cobros_df["fecha_dt"] = pd.to_datetime(cobros_df["fecha"], errors="coerce")
        cobros_df = cobros_df.sort_values("fecha_dt", ascending=False)

        # Separar por origen y tipo
        qb = cobros_df[cobros_df["origen_importacion"] == "QuickBooks"].copy()
        manual = cobros_df[cobros_df["origen_importacion"] != "QuickBooks"].copy()
        qb_com = qb[qb["tipo"] == "comision"].copy()
        qb_cost = qb[qb["tipo"] == "costo"].copy()
        abonos_qb = cobros_df[(cobros_df["tipo"] == "abono") & (cobros_df["origen_importacion"] == "QuickBooks")].copy()
        abonos_manual = cobros_df[(cobros_df["tipo"] == "abono") & (cobros_df["origen_importacion"] != "QuickBooks")].copy()

        # KPIs
        h1, h2, h3, h4 = st.columns(4)
        with h1:
            st.metric("📄 Facturas QB Com.", f"S/ {qb_com['monto'].sum():,.2f}", help=f"{len(qb_com)} docs")
        with h2:
            st.metric("📄 Facturas QB Cost.", f"S/ {qb_cost['monto'].sum():,.2f}", help=f"{len(qb_cost)} docs")
        with h3:
            st.metric("💰 Abonos QB (hist.)", f"S/ {abonos_qb['monto'].sum():,.2f}", help=f"{len(abonos_qb)} docs")
        with h4:
            st.metric("💰 Abonos Manuales", f"S/ {abonos_manual['monto'].sum():,.2f}", help=f"{len(abonos_manual)} docs")

        st.markdown("---")

        # ─── Facturas ───
        st.markdown("### 🔍 Facturas QuickBooks")
        fc1, fc2 = st.tabs(["💼 Comisión", "💸 Costos"])
        with fc1:
            if not qb_com.empty:
                qb_com["Fecha"] = qb_com["fecha_dt"].dt.strftime("%d/%m/%Y")
                qb_com["Monto"] = qb_com["monto"].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(qb_com[["Fecha", "qbo_ref", "Monto", "qbo_estado"]].rename(
                    columns={"qbo_ref": "Factura", "qbo_estado": "Estado QB"}
                ), hide_index=True, use_container_width=True)
                export_buttons("hist_com", qb_com, fi, ff, "Facturas_Comision")
            else:
                st.info("Sin facturas de comisión")

        with fc2:
            if not qb_cost.empty:
                qb_cost["Fecha"] = qb_cost["fecha_dt"].dt.strftime("%d/%m/%Y")
                qb_cost["Monto"] = qb_cost["monto"].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(qb_cost[["Fecha", "qbo_ref", "Monto", "qbo_estado"]].rename(
                    columns={"qbo_ref": "Factura", "qbo_estado": "Estado QB"}
                ), hide_index=True, use_container_width=True)
                export_buttons("hist_cost", qb_cost, fi, ff, "Facturas_Costos")
            else:
                st.info("Sin facturas de costos")

        st.markdown("---")

        # ─── Abonos ───
        st.markdown("### 💳 Abonos Recibidos")
        aa1, aa2 = st.tabs(["📥 QuickBooks (hist.)", "✏️ Manuales (desde 03/03)"])
        with aa1:
            if not abonos_qb.empty:
                abonos_qb["Fecha"] = abonos_qb["fecha_dt"].dt.strftime("%d/%m/%Y")
                abonos_qb["Monto"] = abonos_qb["monto"].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(abonos_qb[["Fecha", "Monto"]], hide_index=True, use_container_width=True)
                st.caption(f"Total: S/ {abonos_qb['monto'].sum():,.2f} ({len(abonos_qb)} abonos)")
            else:
                st.info("Sin abonos QuickBooks")

        with aa2:
            if not abonos_manual.empty:
                abonos_manual["Fecha"] = pd.to_datetime(abonos_manual["fecha"]).dt.strftime("%d/%m/%Y")
                abonos_manual["Monto"] = abonos_manual["monto"].apply(lambda x: f"S/ {x:,.2f}")
                st.dataframe(abonos_manual[["Fecha", "Monto", "detalle"]].rename(
                    columns={"detalle": "Ref."}
                ), hide_index=True, use_container_width=True)
                st.caption(f"Total: S/ {abonos_manual['monto'].sum():,.2f} ({len(abonos_manual)} abonos)")
            else:
                st.info("Sin abonos manuales")

        st.markdown("---")

        # ─── Discrepancias ───
        st.markdown("### ⚠️ Discrepancias")
        vencidas = qb[qb["qbo_estado"].str.contains("Vencido", na=False)]
        if not vencidas.empty:
            st.warning(f"⚠️ **{len(vencidas)} facturas vencidas en QuickBooks** — revisar:")
            vencidas["Fecha"] = vencidas["fecha_dt"].dt.strftime("%d/%m/%Y")
            vencidas["Monto"] = vencidas["monto"].apply(lambda x: f"S/ {x:,.2f}")
            st.dataframe(vencidas[["Fecha", "qbo_ref", "Monto", "qbo_estado", "tipo"]].rename(
                columns={"qbo_ref": "Factura", "tipo": "Tipo"}
            ), hide_index=True, use_container_width=True)

        pagadas_qb = qb[qb["qbo_estado"] == "Pagada"]
        if not pagadas_qb.empty:
            st.info(f"ℹ️ {len(pagadas_qb)} facturas 'Pagada' en QB — verificar si cada una tiene su abono.")

        # Diferencia total
        total_com_qb = qb_com["monto"].sum()
        total_abonado = abonos_qb["monto"].sum() + abonos_manual["monto"].sum()
        diff = total_com_qb - total_abonado

        if diff > 0:
            st.error(f"🔴 **Diferencia por cubrir: S/ {diff:,.2f}** — Comisión QB > Abonos (QB+manuales)")
        elif diff < 0:
            st.success(f"🟢 Sobrante: S/ {abs(diff):,.2f} — Abonos > Comisión QB")
        else:
            st.success("✅ Cuadrado perfecto")

    except Exception as e:
        st.error(f"Error: {e}")
