# views/conciliacion.py - Conciliación de pagos
import streamlit as st
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from components import export_buttons

def render(df, k, t, fi, ff, MONGO_URL):
    st.markdown("## 🔄 Conciliación de Pagos")

    con_t1, con_t2, con_t3 = st.tabs(["💳 Contraste Tarjeta", "🔗 Links de Pago", "💰 Abonos"])

    # ── TAB 1: Contraste Tarjeta ──
    with con_t1:
        st.markdown("**💳 Contraste: Sirvoy Tarjeta vs Plataformas**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Sirvoy (Tarjeta)", f"S/ {k['tb_sirvoy']:,.2f}")
        with c2:
            st.metric("Recibido (Plataformas)", f"S/ {k['tb_plataformas']:,.2f}")
        with c3:
            st.metric("⏳ Pendiente confirmar", f"S/ {k['lk']:,.2f}",
                      delta=f"{k['lk']:,.2f}", delta_color="inverse" if k["lk"] > 0 else "normal")

        if k["lk"] > 0:
            st.warning(f"⚠️ **S/ {k['lk']:,.2f}** en pagos con tarjeta aún no respaldados por plataformas. "
                       "Sube los reportes POS de Izipay/Culqi/Openpay en la pestaña **📤 POS**.")

    # ── TAB 2: Links de Pago ──
    with con_t2:
        st.markdown("**🔗 Links de Pago Retenidos**")
        la = k["la"]
        pend = k["pendientes_link"]
        total_ret = k["total_ret"]

        cl1, cl2, cl3 = st.columns(3)
        with cl1:
            st.metric("Monto Pendiente", f"S/ {total_ret:,.2f}")
        with cl2:
            st.metric("Links Pendientes", len(pend))
        with cl3:
            st.metric("Total Links en Rango", len(la))

        export_buttons("links", la, fi, ff, "Links")

        if not pend.empty:
            p_l = pend.copy()
            p_l["Fecha"] = p_l["date_pe"].dt.strftime("%d/%m/%Y %H:%M")
            p_l["Monto"] = p_l["amount"].apply(lambda x: f"S/ {x:,.2f}")
            st.dataframe(p_l[["Fecha", "Monto", "fuente", "method"]].rename(
                columns={"fuente": "Pasarela", "method": "Ref"}
            ), hide_index=True, use_container_width=True)

            # Marcador de depositados
            st.markdown("**✅ Marcar como depositados**")
            p_opts = pend.sort_values("date_pe").copy()
            p_opts["label"] = p_opts.apply(
                lambda r: f"{r['date_pe'].strftime('%d/%m %H:%M')} - S/ {r['amount']:,.2f} ({r['fuente']})", axis=1
            )
            p_opts["str_id"] = p_opts["_id"].apply(str)
            id_to_label = dict(zip(p_opts["str_id"], p_opts["label"]))

            seleccionados = st.multiselect("Seleccionar pagos:", p_opts["str_id"].tolist(),
                                           format_func=lambda x: id_to_label.get(x, x))
            if st.button("✅ Marcar como depositados", use_container_width=True) and seleccionados:
                try:
                    from bson import ObjectId
                    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                    cli["pena_linda"]["pagos"].update_many(
                        {"_id": {"$in": [ObjectId(s) for s in seleccionados]}},
                        {"$set": {"estado_deposito": "depositado",
                                  "fecha_depositado": datetime.now(), "conciliado": True}}
                    )
                    cli.close()
                    st.success(f"✅ {len(seleccionados)} marcados como depositados")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        if len(la) > len(pend):
            st.success(f"✅ {len(la) - len(pend)} links ya depositados en este período.")

    # ── TAB 3: Abonos ──
    with con_t3:
        st.markdown("**💰 Registro de Abonos a Chamba Digital**")
        st.caption("Abonos de saldo que Peña Linda realiza para amortizar la deuda.")

        # Cargar cobros extra
        try:
            cli_c = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
            cobros_all = list(cli_c["pena_linda"]["cobros"].find({}))
            cli_c.close()
            cobros_df = pd.DataFrame(cobros_all) if cobros_all else pd.DataFrame()
            cobros_extra = cobros_df[cobros_df["categoria"] == "Extra"].copy() if not cobros_df.empty else pd.DataFrame()
            total_extra = float(cobros_extra["monto"].sum()) if not cobros_extra.empty else 0
        except:
            cobros_extra = pd.DataFrame()
            total_extra = 0

        ca1, ca2, ca3, ca4 = st.columns(4)
        with ca1:
            st.metric("Adeudado (desde 03/03)", f"S/ {k['adeudado']:,.2f}")
            st.caption(f"📋 Saldo Base S/ {k.get('saldo_base_hist',0):,.2f} + "
                       f"Comisión S/ {k['comision_desde_mar']:,.2f} + "
                       f"Costos S/ {k.get('total_costos_hist',0):,.2f}")
        with ca2:
            st.metric("Abonado (desde 03/03)", f"S/ {k['total_abonos']:,.2f}")
        with ca3:
            st.metric("Saldo Deudor", f"S/ {k['saldo_pendiente']:,.2f}",
                      delta=f"{k['saldo_pendiente']:,.2f}", delta_color="inverse")
        with ca4:
            st.metric("📌 Costos Extra (detalle)", f"S/ {total_extra:,.2f}")

        # Desglose de Costos Extra
        if not cobros_extra.empty:
            st.markdown("---")
            st.markdown("**🔍 Costos Extra (categoría 'Extra')**")
            cobros_extra["Fecha"] = pd.to_datetime(cobros_extra["fecha"]).dt.strftime("%d/%m/%Y")
            cobros_extra["Monto"] = cobros_extra["monto"].apply(lambda x: f"S/ {x:,.2f}")
            st.data_editor(
                cobros_extra[["Fecha", "concepto", "Monto", "detalle"]].rename(
                    columns={"concepto": "Concepto", "detalle": "Detalle"}
                ),
                hide_index=True, use_container_width=True, key="cobros_extra_editor",
            )

        # Historial de abonos
        pr = k["pagos_recibidos"]
        sa1, sa2 = st.columns([3, 2])
        with sa1:
            st.markdown("**📋 Abonos Registrados**")
            if not pr.empty:
                ab_df = pr.sort_values("date_pe", ascending=False).copy()
                ab_df["Fecha"] = ab_df["date_pe"].dt.strftime("%d/%m/%Y")
                ab_df["Monto"] = ab_df["amount"].apply(lambda x: f"S/ {x:,.2f}")
                st.data_editor(
                    ab_df[["Fecha", "Monto", "method"]].rename(columns={"method": "Ref."}),
                    column_config={
                        "Monto": st.column_config.NumberColumn("Monto", format="S/ %.2f"),
                        "Ref.": st.column_config.TextColumn("Referencia"),
                    },
                    hide_index=True, use_container_width=True, key="abonos_editor",
                )
            else:
                st.info("Sin abonos en este período.")

        with sa2:
            st.markdown("**📝 Nuevo Abono**")
            ab_fecha = st.date_input("Fecha", datetime.now(), key="ab_fecha")
            ab_monto = st.number_input("Monto (S/)", min_value=0.0, step=100.0, format="%.2f", key="ab_monto")
            ab_ref = st.text_input("Referencia", placeholder="Ej: Transf. BCP...", key="ab_ref")
            if st.button("💾 Guardar", type="primary", disabled=(ab_monto <= 0), use_container_width=True):
                try:
                    import hashlib
                    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                    doc = {
                        "fuente": "Abono Chamba",
                        "fecha": datetime.combine(ab_fecha, datetime.min.time()),
                        "monto": ab_monto, "moneda": "PEN",
                        "metodo": ab_ref or "Abono manual",
                        "tipo_pago": "Abono", "categoria": "Abono",
                        "hash": hashlib.md5(f"ABONO|{ab_fecha}|{ab_monto}|{ab_ref}".encode()).hexdigest(),
                    }
                    cli["pena_linda"]["pagos"].insert_one(doc)
                    doc_cobro = {
                        "fecha": datetime.combine(ab_fecha, datetime.min.time()),
                        "monto": ab_monto, "moneda": "PEN", "tipo": "abono",
                        "categoria": "Abono", "concepto": "Pago recibido",
                        "detalle": ab_ref or "Abono manual",
                        "hash": hashlib.md5(f"COBRO_ABONO|{ab_fecha}|{ab_monto}|{ab_ref}".encode()).hexdigest(),
                    }
                    cli["pena_linda"]["cobros"].insert_one(doc_cobro)
                    cli.close()
                    st.success(f"✅ Abono de S/ {ab_monto:,.2f} registrado")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error("⚠️ Abono duplicado")
                    else:
                        st.error(f"Error: {e}")

            # Eliminar abono
            st.markdown("---")
            st.markdown("**🗑️ Eliminar Abono**")
            if not pr.empty:
                ab_opts = pr.sort_values("date_pe", ascending=False).copy()
                ab_opts["label"] = ab_opts.apply(
                    lambda r: f"S/ {r['amount']:,.2f} - {r['date_pe'].strftime('%d/%m/%Y')} ({r['method']})", axis=1
                )
                ab_opts["str_id"] = ab_opts["_id"].apply(str)
                del_id = st.selectbox(
                    "Seleccionar:",
                    ab_opts["str_id"].tolist(),
                    format_func=lambda x: dict(zip(ab_opts["str_id"], ab_opts["label"])).get(x, x),
                    key="del_abono",
                )
                if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
                    try:
                        from bson import ObjectId
                        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
                        cli["pena_linda"]["pagos"].delete_one({"_id": ObjectId(del_id)})
                        cli.close()
                        st.success("✅ Abono eliminado")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
