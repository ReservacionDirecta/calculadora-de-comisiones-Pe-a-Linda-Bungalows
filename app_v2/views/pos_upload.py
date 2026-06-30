# views/pos_upload.py - Carga de reportes POS (Izipay, Culqi, Openpay)
import streamlit as st
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import hashlib
import io

def render(MONGO_URL):
    st.markdown("## 📤 Cargar Reporte POS")
    st.markdown("Sube el reporte del portal bancario (Izipay, Culqi, Openpay) para conciliar pagos con tarjeta.")
    st.caption("Estos reportes los recibes por correo o los descargas del portal. Al importarlos, "
               "el monto **⏳ Pendiente** se recalcula automáticamente.")

    # ─── Selección de plataforma ───
    plataforma = st.selectbox("Selecciona la plataforma:", ["", "Izipay", "Culqi", "Openpay", "Otro"])

    if not plataforma:
        st.info("👆 Selecciona una plataforma para comenzar.")
        st.markdown("""
        **Formatos soportados:**
        - **Izipay**: CSV exportado desde secure.micuentaweb.pe
        - **Culqi**: CSV desde panel.culqi.pe
        - **Openpay**: CSV desde dashboard.openpay.pe
        """)
        return

    uploaded_file = st.file_uploader(
        f"📎 Subir archivo CSV/Excel de {plataforma}",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is None:
        return

    # ─── Parsear archivo ───
    try:
        if uploaded_file.name.endswith(".csv"):
            raw = pd.read_csv(uploaded_file, encoding="utf-8")
        else:
            raw = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return

    # ─── Vista previa ───
    st.markdown("### 🔍 Vista Previa")
    st.caption("Primeras 10 filas del archivo. Verifica que los datos sean correctos.")

    # Mostrar primeras filas
    st.dataframe(raw.head(10), use_container_width=True)

    # ─── Mapeo de columnas ───
    st.markdown("### 🗺️ Mapeo de Columnas")
    st.write("Indica qué columna del archivo corresponde a cada campo:")

    col_map = {}
    col1, col2 = st.columns(2)
    with col1:
        col_map["fecha"] = st.selectbox("Columna FECHA", raw.columns.tolist(), key="pos_fecha")
    with col2:
        col_map["monto"] = st.selectbox("Columna MONTO", raw.columns.tolist(), key="pos_monto")

    # Columnas opcionales
    op_c1, op_c2 = st.columns(2)
    with op_c1:
        col_map["referencia"] = st.selectbox("Columna REFERENCIA (opcional)", ["(ninguna)"] + raw.columns.tolist(), key="pos_ref")
    with op_c2:
        col_map["tarjeta"] = st.selectbox("Columna TARJETA (opcional)", ["(ninguna)"] + raw.columns.tolist(), key="pos_tarjeta")

    # ─── Vista previa parseada ───
    st.markdown("### 📋 Datos a Importar")
    try:
        parsed = raw.copy()
        parsed["fecha_dt"] = pd.to_datetime(parsed[col_map["fecha"]], errors="coerce", dayfirst=True)
        parsed["monto_num"] = pd.to_numeric(
            parsed[col_map["monto"]].astype(str).str.replace(",", "").str.replace("S/", "").str.strip(),
            errors="coerce",
        )
        parsed = parsed.dropna(subset=["fecha_dt", "monto_num"])

        st.dataframe(
            parsed[["fecha_dt", "monto_num"] + ([col_map["referencia"]] if col_map["referencia"] != "(ninguna)" else [])].head(20),
            use_container_width=True,
        )
        st.caption(f"**{len(parsed)} registros** · Total: S/ {parsed['monto_num'].sum():,.2f}")

        if st.button("✅ Confirmar e Importar a MongoDB", type="primary", use_container_width=True):
            cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            inserted = 0
            skipped = 0

            for _, row in parsed.iterrows():
                monto_val = row["monto_num"]
                if monto_val <= 0:
                    skipped += 1
                    continue

                ref_val = row[col_map["referencia"]] if col_map["referencia"] != "(ninguna)" else f"POS {plataforma}"
                fecha_val = row["fecha_dt"].to_pydatetime()

                # Generar hash único
                raw_hash = f"POS_{plataforma}|{fecha_val}|{monto_val}|{ref_val}"
                h = hashlib.md5(raw_hash.encode()).hexdigest()

                existing = cli["pena_linda"]["pagos"].find_one({"hash": h})
                if existing:
                    skipped += 1
                    continue

                doc = {
                    "fuente": plataforma,
                    "fecha": fecha_val,
                    "monto": monto_val,
                    "moneda": "PEN",
                    "metodo": str(ref_val),
                    "tipo_pago": "Tarjeta",
                    "es_link": False,
                    "estado_deposito": "depositado",
                    "conciliado": True,
                    "hash": h,
                    "origen_importacion": f"POS Upload {plataforma}",
                    "_cargado": datetime.now(),
                }

                try:
                    cli["pena_linda"]["pagos"].insert_one(doc)
                    inserted += 1
                except Exception:
                    skipped += 1

            cli.close()
            st.success(f"✅ **Importación completada:** {inserted} insertados, {skipped} omitidos")
            st.cache_data.clear()
            st.info("🔄 Recargando datos para reflejar cambios...")
            st.rerun()

    except Exception as e:
        st.error(f"Error procesando: {e}")
