# data.py - Carga única de datos y cálculos
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import streamlit as st

import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")


@st.cache_data(ttl=300)
def load_all():
    """
    Carga pagos y cobros desde MongoDB en UNA sola operación.
    Retorna (df, cobros_df, db_status)
    """
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        cli.admin.command("ping")
        docs = list(cli["pena_linda"]["pagos"].find({}, {"hash": 0}))
        cobros_docs = list(cli["pena_linda"]["cobros"].find({}))
        cli.close()
        if not docs:
            return pd.DataFrame(), pd.DataFrame(), "⚠️ BD vacía"

        # ─── DataFrame principal (pagos) ───
        df = pd.DataFrame(docs)
        df["date"] = pd.to_datetime(df["fecha"], errors="coerce")

        # Timezone: costos/abonos en America/Lima, resto UTC→Lima
        is_cost_or_abono = df["tipo_pago"].isin(["Costo", "Abono"]) | df["fuente"].isin(["Abono Chamba", "Saldo Base"])
        df["date_pe"] = df["date"].dt.tz_localize("UTC", ambiguous="NaT").dt.tz_convert("America/Lima")
        df.loc[is_cost_or_abono, "date_pe"] = df.loc[is_cost_or_abono, "date"].dt.tz_localize("America/Lima", ambiguous="NaT")

        df["amount"] = pd.to_numeric(df["monto"], errors="coerce")
        df = df.dropna(subset=["date_pe"]).sort_values("date_pe").reset_index(drop=True)
        df["sem_key"] = df["date_pe"].dt.strftime("%Y-S%V")
        df["mes_label"] = df["date_pe"].dt.strftime("%Y-%m")
        df["tipo_pago"] = df["tipo_pago"].fillna("Otros")
        df["es_link"] = df["es_link"].fillna(False)
        df["method"] = df["metodo"].fillna("")
        df["referencia"] = df.get("referencia", df.get("reference", df.get("transaction_id", ""))).fillna("")
        df["estado_deposito"] = df.get("estado_deposito", pd.Series(dtype="object")).fillna("depositado")

        # ─── DataFrame cobros ───
        cobros_df = pd.DataFrame(cobros_docs) if cobros_docs else pd.DataFrame()
        if not cobros_df.empty:
            cobros_df["fecha_dt"] = pd.to_datetime(cobros_df["fecha"], errors="coerce")
            cobros_df["monto"] = pd.to_numeric(cobros_df["monto"], errors="coerce")
            cobros_df = cobros_df.dropna(subset=["fecha_dt"]).sort_values("fecha_dt", ascending=False).reset_index(drop=True)

        return df, cobros_df, f"MongoDB ({len(df):,} docs)"

    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"❌ Error: {e}"


def calc_kpis(df, cobros_df, fi, ff, ts):
    """
    Calcula todos los KPIs a partir de los DataFrames ya filtrados por fecha.
    Retorna dict con todas las métricas.
    """
    # ─── Filtro por fecha ───
    mask = (df["date_pe"].dt.date >= fi) & (df["date_pe"].dt.date <= ff)
    df_f = df[mask].copy()

    # Ventas del período
    is_sale = ~df_f["tipo_pago"].isin(["Costo"]) & ~df_f["fuente"].isin(["Abono Chamba", "Saldo Base"])
    sv_sales = df_f[is_sale & df_f["tipo_pago"].isin(ts)]
    sv_sirvoy = sv_sales[sv_sales["fuente"] == "Sirvoy"]

    tb_sirvoy = float(sv_sirvoy["amount"].sum())
    tb_plataformas = float(sv_sales[sv_sales["fuente"].isin(["Izipay", "Culqi", "Openpay"])]["amount"].sum())
    sv_transf_efect = float(sv_sirvoy[sv_sirvoy["tipo_pago"].isin(["Transferencia", "Efectivo"])]["amount"].sum())
    tb_recibido = tb_plataformas + sv_transf_efect

    # Links
    la = df_f[df_f["es_link"]].copy()
    la["estado_deposito"] = la["estado_deposito"].fillna("depositado")
    pendientes_link = la[la["estado_deposito"] == "pendiente"]
    total_ret = float(pendientes_link["amount"].sum())

    # Contraste tarjeta
    lk = max(0.0, float(sv_sirvoy[sv_sirvoy["tipo_pago"] == "Tarjeta"]["amount"].sum()) - tb_plataformas)

    # Comisión 5%
    comision = tb_sirvoy * 0.05

    # Costos
    costos = df_f[df_f["tipo_pago"] == "Costo"]
    costos_sin_base = costos[costos["fuente"] != "Saldo Base"]
    total_costos = float(costos_sin_base["amount"].sum())
    costo_fb = float(costos[costos["fuente"] == "Costo FB Ads"]["amount"].sum())
    costo_sv = float(costos[costos["fuente"] == "Costo Sirvoy"]["amount"].sum())
    costo_as = float(costos[costos["fuente"] == "Costo Asistente"]["amount"].sum())
    costo_saldo = float(costos[costos["fuente"] == "Saldo Base"]["amount"].sum())

    # Ticket promedio
    prom = float(sv_sirvoy["amount"].mean()) if not sv_sirvoy.empty else 0.0
    tx = len(sv_sirvoy)

    # ─── Cálculos acumulados desde 03/03/2026 ───
    fecha_base = pd.Timestamp("2026-03-03").date()

    # Comisión: 5% sobre NETO Sirvoy (ingresos reales: positivos + negativos)
    sv_desde_mar = df[(df["date_pe"].dt.date >= fecha_base) & (df["fuente"] == "Sirvoy")]
    comision_desde_mar = float(sv_desde_mar["amount"].sum() * 0.05)

    # Costos acumulados desde 03/03 (para la deuda, excluye Saldo Base)
    costos_hist = df[(df["date_pe"].dt.date >= fecha_base) & (df["tipo_pago"] == "Costo") & (df["fuente"] != "Saldo Base")]
    total_costos_hist = float(costos_hist["amount"].sum())

    # Saldo Base (heredado QuickBooks al 03/03)
    saldo_base_hist = float(df[df["fuente"] == "Saldo Base"]["amount"].sum())

    # ─── Abonos y deuda (acumulado desde 03/03) ───
    total_abonos = 0.0
    adeudado = 0.0
    saldo_pendiente = 0.0

    if not cobros_df.empty:
        # Abonos desde 03/03 (sin filtro de sidebar)
        mask_c = cobros_df["fecha_dt"].dt.date >= fecha_base
        total_abonos = float(cobros_df.loc[mask_c & (cobros_df["tipo"] == "abono"), "monto"].sum())

    # Adeudado = Saldo Base + Comisión acumulada + Costos acumulados (todo desde 03/03)
    adeudado = saldo_base_hist + comision_desde_mar + total_costos_hist
    saldo_pendiente = max(0.0, adeudado - total_abonos)

    # ─── Pagos recibidos (abonos desde pagos, como fallback) ───
    pagos_recibidos = df[df["fuente"] == "Abono Chamba"]
    if not pagos_recibidos.empty:
        pagos_recibidos = pagos_recibidos[
            (pagos_recibidos["date_pe"].dt.date >= fi) & (pagos_recibidos["date_pe"].dt.date <= ff)
        ]

    return {
        "tb_sirvoy": tb_sirvoy,
        "tb_recibido": tb_recibido,
        "tb_plataformas": tb_plataformas,
        "comision": comision,
        "total_costos": total_costos,
        "costo_fb": costo_fb,
        "costo_sv": costo_sv,
        "costo_as": costo_as,
        "costo_saldo": costo_saldo,
        "saldo_pendiente": saldo_pendiente,
        "comision_desde_mar": comision_desde_mar,
        "total_costos_hist": total_costos_hist,
        "saldo_base_hist": saldo_base_hist,
        "total_abonos": total_abonos,
        "adeudado": adeudado,
        "prom": prom,
        "tx": tx,
        "lk": lk,
        "total_ret": total_ret,
        "sv_sales": sv_sales,
        "sv_sirvoy": sv_sirvoy,
        "la": la,
        "pendientes_link": pendientes_link,
        "costos": costos,
        "costos_sin_base": costos_sin_base,
        "pagos_recibidos": pagos_recibidos,
        "df_f": df_f,
    }
