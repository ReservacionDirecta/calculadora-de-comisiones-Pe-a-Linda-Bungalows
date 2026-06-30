# views/costos.py - Costos operativos
import streamlit as st
import pandas as pd
import plotly.express as px
from components import export_buttons

def render(df, k, t, fi, ff, MONGO_URL):
    st.markdown("## 💸 Costos Operativos")

    c_tab1, c_tab2, c_tab3 = st.tabs(["📋 Detalle", "➕ Registrar", "🔧 Extra"])

    costos_df = k["costos_sin_base"]
    costos_full = k["costos"]

    # ── Tab 1: Detalle ──
    with c_tab1:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("📱 Facebook Ads", f"S/ {k['costo_fb']:,.2f}")
        with col_m2:
            st.metric("🖥️ Sirvoy", f"S/ {k['costo_sv']:,.2f}")
        with col_m3:
            st.metric("👤 Asistente", f"S/ {k['costo_as']:,.2f}")
        with col_m4:
            st.metric("📊 Total", f"S/ {k['total_costos']:,.2f}")

        export_buttons("costos", costos_df, fi, ff, "Costos")

        if not costos_df.empty:
            df_c = costos_df.sort_values("date_pe", ascending=False).copy()
            df_c["Fecha"] = df_c["date_pe"].dt.strftime("%d/%m/%Y")
            df_c["Categoría"] = df_c["fuente"].str.replace("Costo ", "")
            df_c["Monto"] = df_c["amount"].apply(lambda x: f"S/ {x:,.2f}")
            df_c["Concepto"] = df_c["method"]
            st.data_editor(
                df_c[["Fecha", "transaction_id", "Categoría", "Concepto", "Monto"]].rename(
                    columns={"transaction_id": "ID"}
                ),
                column_config={
                    "Monto": st.column_config.NumberColumn("Monto", format="S/ %.2f"),
                    "Concepto": st.column_config.TextColumn("Concepto", help="Editar"),
                },
                hide_index=True, use_container_width=True, key="costos_editor",
            )

            st.markdown("**📈 Costos por Mes**")
            cm = costos_df.groupby("mes_label")["amount"].sum().reset_index()
            fig = px.bar(cm, x="mes_label", y="amount", color_discrete_sequence=["#f97316"],
                         labels={"mes_label": "", "amount": "S/"})
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                              plot_bgcolor=t["bg"], paper_bgcolor=t["bg_card"], font_color=t["text"])
            fig.update_yaxes(tickprefix="S/ ", gridcolor=t["border"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin costos en este período")

    # ── Tab 2: Registrar nuevo costo ──
    with c_tab2:
        st.markdown("**➕ Registrar Nuevo Costo**")
        with st.form("new_costo_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                nueva_fecha = st.date_input("Fecha", value=pd.Timestamp.now().date())
            with col_f2:
                nuevo_monto = st.number_input("Monto (S/)", min_value=0.0, step=50.0, format="%.2f")
            nueva_cat = st.selectbox("Categoría", ["Facebook Ads", "Sirvoy", "Asistente", "Otro"])
            nuevo_ref = st.text_input("Concepto / Referencia", placeholder="Ej: Campaña Junio...")

            if st.form_submit_button("💾 Guardar Costo", type="primary", disabled=(nuevo_monto <= 0)):
                try:
                    from pymongo import MongoClient
                    import hashlib
                    from datetime import datetime

                    cat_map = {
                        "Facebook Ads": "Costo FB Ads",
                        "Sirvoy": "Costo Sirvoy",
                        "Asistente": "Costo Asistente",
                        "Otro": "Costo Extra",
                    }
                    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                    nuevaf = datetime.combine(nueva_fecha, datetime.min.time())
                    doc = {
                        "fuente": cat_map[nueva_cat],
                        "fecha": nuevaf,
                        "monto": nuevo_monto,
                        "moneda": "PEN",
                        "metodo": nuevo_ref or f"Costo {nueva_cat}",
                        "tipo_pago": "Costo",
                        "categoria": nueva_cat,
                        "hash": hashlib.md5(f"COSTO|{nuevaf}|{nuevo_monto}|{nuevo_ref}".encode()).hexdigest(),
                    }
                    cli["pena_linda"]["pagos"].insert_one(doc)
                    # También en cobros
                    doc_cobro = {
                        "fecha": nuevaf, "monto": nuevo_monto, "moneda": "PEN",
                        "tipo": "costo", "categoria": nueva_cat,
                        "concepto": nuevo_ref or f"Costo {nueva_cat}",
                        "detalle": nuevo_ref or "",
                        "hash": hashlib.md5(f"COBRO_COSTO|{nuevaf}|{nuevo_monto}|{nuevo_ref}".encode()).hexdigest(),
                    }
                    cli["pena_linda"]["cobros"].insert_one(doc_cobro)
                    cli.close()
                    st.success(f"✅ Costo de S/ {nuevo_monto:,.2f} registrado")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Tab 3: Costos Extra ──
    with c_tab3:
        st.markdown("**🔧 Costos Extra**")
        st.caption("Costos categoría 'Otro' registrados manualmente")
        extra_df = costos_full[costos_full["fuente"] == "Costo Extra"].copy() if not costos_full.empty else pd.DataFrame()

        if not extra_df.empty:
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.metric("📦 Docs", len(extra_df))
            with col_e2:
                st.metric("💰 Total", f"S/ {extra_df['amount'].sum():,.0f}")
            export_buttons("extra", extra_df, fi, ff, "Costos_Extra")

            extra_df["Fecha"] = extra_df["date_pe"].dt.strftime("%d/%m/%Y")
            extra_df["Monto"] = extra_df["amount"].apply(lambda x: f"S/ {x:,.2f}")
            extra_df["Concepto"] = extra_df["method"]
            st.data_editor(
                extra_df[["Fecha", "Concepto", "Monto"]],
                hide_index=True, use_container_width=True, key="extra_editor",
            )
        else:
            st.info("Sin costos extra. Usa '➕ Registrar' con categoría 'Otro'.")
