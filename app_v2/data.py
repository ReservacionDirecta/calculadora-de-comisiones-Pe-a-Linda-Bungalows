# data.py - Carga optimizada con caching
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import streamlit as st
import os

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")
if "interchange.proxy.rlwy.net" in MONGO_URL and "authSource" not in MONGO_URL:
    MONGO_URL += "&authSource=admin" if "?" in MONGO_URL else "?authSource=admin"


@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    """Carga pagos y cobros desde MongoDB."""
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)
        cli.admin.command("ping")
        docs = list(cli["pena_linda"]["pagos"].find({}, {"hash": 0}))
        cobros_docs = list(cli["pena_linda"]["cobros"].find({}))
        cli.close()
        if not docs:
            return pd.DataFrame(), pd.DataFrame(), "BD vacia"

        # ─── DataFrame principal (pagos) ───
        df = pd.DataFrame(docs)
        df["date"] = pd.to_datetime(df["fecha"], errors="coerce")

        # Timezone: todas las fechas en America/Lima (hotel en Peru)
        # Sirvoy guarda fechas midnight Lima, Izipay tambien usa hora Lima
        df["date_pe"] = df["date"].dt.tz_localize("America/Lima", ambiguous="NaT")

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
        return pd.DataFrame(), pd.DataFrame(), f"Error MongoDB: {str(e)[:100]}"


def calc_kpis(df, cobros_df, fi, ff, ts):
    """
    Calcula todos los KPIs a partir de los DataFrames ya filtrados por fecha.
    Retorna dict con todas las métricas.
    """
    # ─── Filtro por fecha ───
    mask = (df["date_pe"].dt.date >= fi) & (df["date_pe"].dt.date <= ff)
    df_f = df[mask].copy()

    # Ventas del período - Sirvoy total (NETO: incluye positivos y negativos)
    # El total de Sirvoy debe ser el neto (como lo muestra Sirvoy en su página)
    # Excluir Izipay POS (son depósitos del POS al banco, no ventas Sirvoy)
    is_sale = ~df_f["tipo_pago"].isin(["Costo"]) & ~df_f["fuente"].isin(["Abono Chamba", "Saldo Base", "Izipay POS"])
    sv_sirvoy_all = df_f[is_sale & (df_f["fuente"] == "Sirvoy")]

    # Para gráficos/desglose: filtrar por tipo seleccionado (excluyendo Izipay POS)
    sv_sales = df_f[is_sale & df_f["tipo_pago"].isin(ts)]
    sv_sirvoy = sv_sales[sv_sales["fuente"] == "Sirvoy"]

    # Total Sirvoy = NETO (positivos + negativos), igual que Sirvoy página
    tb_sirvoy = float(sv_sirvoy_all["amount"].sum())

    # Plataformas: solo pagos positivos (excluir depósitos Izipay POS negativos)
    plataformas_mask = sv_sales["fuente"].isin(["Izipay", "Culqi", "Openpay"])
    plataformas_all = sv_sales[plataformas_mask]
    tb_plataformas = float(plataformas_all[plataformas_all["amount"] > 0]["amount"].sum())

    # Recibido = Sirvoy neto (base real del hotel)
    # Las plataformas son confirmación de pagos con tarjeta, no ingresos adicionales
    tb_recibido = tb_sirvoy

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

    # Porcentaje costos vs ingresos netos (recibido)
    costos_recibido_pct = (total_costos / tb_recibido * 100) if tb_recibido > 0 else 0.0

    # Ticket promedio (sobre todos los Sirvoy del periodo)
    prom = float(sv_sirvoy_all["amount"].mean()) if not sv_sirvoy_all.empty else 0.0
    tx = len(sv_sirvoy_all)

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

    # ─── ROI (acumulado desde 03/03) ───
    neto_desde_mar = float(sv_desde_mar["amount"].sum())
    inversion_hist = comision_desde_mar + total_costos_hist
    ganancia_hist = neto_desde_mar - inversion_hist
    roi_pct = (ganancia_hist / inversion_hist * 100) if inversion_hist > 0 else 0.0
    roi_x_sol = (neto_desde_mar / inversion_hist) if inversion_hist > 0 else 0.0

    # ROI del período filtrado
    inversion_periodo = comision + total_costos
    ganancia_periodo = tb_sirvoy - inversion_periodo
    roi_periodo_pct = (ganancia_periodo / inversion_periodo * 100) if inversion_periodo > 0 else 0.0
    roi_periodo_x_sol = (tb_sirvoy / inversion_periodo) if inversion_periodo > 0 else 0.0

    # ─── Acumulados del PERÍODO filtrado ───
    comision_periodo = float(sv_sirvoy_all["amount"].sum() * 0.05)
    costos_periodo = float(costos_sin_base["amount"].sum())
    abonos_periodo = 0.0
    if not cobros_df.empty and not cobros_df["fecha_dt"].isna().all():
        mask_periodo = (cobros_df["fecha_dt"].dt.date >= fi) & (cobros_df["fecha_dt"].dt.date <= ff)
        abonos_periodo = float(cobros_df.loc[mask_periodo & (cobros_df["tipo"] == "abono"), "monto"].sum())
    adeudado_periodo = comision_periodo + costos_periodo
    saldo_pendiente_periodo = max(0.0, adeudado_periodo - abonos_periodo)

    # ─── Insights automáticos (ajustados al rango de fechas) ───
    insights = []

    # Período
    dias = (ff - fi).days + 1
    insights.append(f"📅 **Período:** {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')} ({dias} días)")

    # Ventas
    if tb_sirvoy > 0:
        insights.append(f"📊 **Ventas Sirvoy:** S/ {tb_sirvoy:,.2f} ({tx} transacciones)")
    else:
        insights.append("⚠️ **Sin ventas Sirvoy** en este período.")

    # Comisión
    if comision > 0:
        insights.append(f"💰 **Comisión 5%:** S/ {comision:,.2f}")

    # Costos
    if total_costos > 0:
        fb_pct = (costo_fb / total_costos * 100) if total_costos > 0 else 0
        sv_pct = (costo_sv / total_costos * 100) if total_costos > 0 else 0
        as_pct = (costo_as / total_costos * 100) if total_costos > 0 else 0
        insights.append(f"💸 **Costos operativos:** S/ {total_costos:,.2f}")
        insights.append(f"  - Facebook Ads: S/ {costo_fb:,.2f} ({fb_pct:.1f}%)")
        insights.append(f"  - Sirvoy: S/ {costo_sv:,.2f} ({sv_pct:.1f}%)")
        insights.append(f"  - Asistente: S/ {costo_as:,.2f} ({as_pct:.1f}%)")

    # Ticket promedio
    if tx > 0:
        insights.append(f"🎫 **Ticket promedio:** S/ {prom:,.2f} ({tx} transacciones)")

    # Plataformas
    if tb_plataformas > 0:
        insights.append(f"💳 **Plataformas:** S/ {tb_plataformas:,.2f} (confirmación de pagos con tarjeta)")

    # Recibido
    if tb_recibido > 0:
        insights.append(f"✅ **Recibido:** S/ {tb_recibido:,.2f} (Transferencia + Efectivo + Plataformas)")

    # ROI del período
    if inversion_periodo > 0:
        if ganancia_periodo > 0:
            insights.append(f"📈 **ROI período:** +{roi_periodo_pct:.1f}% — Por cada S/ 1 invertido, S/ {roi_periodo_x_sol:.2f} en ventas")
        else:
            insights.append(f"⚠️ **ROI período negativo:** Los costos y comisión superan las ventas del período.")

    # Contraste tarjeta
    if lk > 0:
        insights.append(f"⏳ **S/ {lk:,.2f}** en tarjeta Sirvoy sin contraste en plataformas — posible demora en depósito.")

    # Acumulado histórico
    if adeudado > 0:
        insights.append(f"📋 **Deuda acumulada (desde 03/03):** S/ {adeudado:,.2f}")
        if total_abonos > 0:
            insights.append(f"  - Abonos: S/ {total_abonos:,.2f}")
            insights.append(f"  - Pendiente: S/ {saldo_pendiente:,.2f}")

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
        "neto_desde_mar": neto_desde_mar,
        "inversion_hist": inversion_hist,
        "ganancia_hist": ganancia_hist,
        "roi_pct": roi_pct,
        "roi_x_sol": roi_x_sol,
        "inversion_periodo": inversion_periodo,
        "ganancia_periodo": ganancia_periodo,
        "roi_periodo_pct": roi_periodo_pct,
        "roi_periodo_x_sol": roi_periodo_x_sol,
        "costos_recibido_pct": costos_recibido_pct,
        "insights": insights,
        "comision_periodo": comision_periodo,
        "costos_periodo": costos_periodo,
        "abonos_periodo": abonos_periodo,
        "adeudado_periodo": adeudado_periodo,
        "saldo_pendiente_periodo": saldo_pendiente_periodo,
        "fi": fi,
        "ff": ff,
    }
