#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera reportes semanales (Martes a Lunes) desde MongoDB
Período: 03/03/2026 al 22/06/2026
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
from pdf_generator import PDFGenerator
import os

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "pena_linda"
START = datetime(2026, 3, 3)
END = datetime(2026, 6, 29, 23, 59, 59)

def connect():
    c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return c[DB_NAME]

def load_data(db):
    """Carga pagos desde MongoDB y filtra por rango y fuente Sirvoy."""
    raw = list(db["pagos"].find({
        "fuente": "Sirvoy",
        "fecha": {"$gte": START, "$lte": END}
    }, {"_id": 0}))
    print(f"  Pagos Sirvoy en MongoDB: {len(raw)}")
    df = pd.DataFrame(raw)

    # Parse fechas
    if "date_pe" in df.columns:
        df["date"] = pd.to_datetime(df["date_pe"], errors="coerce")
    elif "fecha" in df.columns:
        df["date"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")

    # Parse montos
    monto_col = "monto" if "monto" in df.columns else "amount"
    df["monto"] = pd.to_numeric(df[monto_col], errors="coerce").fillna(0)

    # Clasificar tipo de ingreso
    def classify(row):
        metodo = str(row.get("metodo", "")).lower()
        tipo = str(row.get("tipo_pago", "")).lower()
        monto = row.get("monto", 0)
        if "tarjeta" in metodo or "card" in metodo or metodo in ("pago con tarjeta", "tarjeta/efectivo"):
            return "Tarjeta"
        if "transferencia" in metodo or "transf" in metodo:
            return "Transferencia"
        if "efectivo" in metodo or "cash" in metodo:
            return "Efectivo"
        return "Tarjeta"  # default

    df["income_type"] = df.apply(classify, axis=1)

    # Source (costos)
    def get_source(row):
        cat = str(row.get("categoria", "")).lower()
        conc = str(row.get("concepto", "")).lower()
        if "facebook" in cat or "fb" in cat or "facebook" in conc:
            return "Facebook Ads"
        if "sirvoy" in cat or "sirvoy" in conc:
            return "Sirvoy Software"
        if "asistente" in cat or "asistente" in conc:
            return "Asistente Comercial"
        return ""
    df["source"] = df.apply(get_source, axis=1)

    print(f"  {len(df)} registros en rango")
    print(f"  Tipos: {df['income_type'].value_counts().to_dict()}")
    return df

def build_weekly_ranges(start, end):
    """Genera rangos semanales Martes a Lunes."""
    weeks = []
    cur = start
    while cur <= end:
        week_end = cur + timedelta(days=6, hours=23, minutes=59, seconds=59)
        weeks.append((cur, min(week_end, end)))
        cur += timedelta(days=7)
    return weeks

def process_week(week_df, week_label):
    """Calcula KPIs para una semana."""
    ingresos = week_df[week_df["income_type"].isin(["Tarjeta", "Transferencia", "Efectivo"])]
    gastos = week_df[week_df["income_type"] == "Gasto"]

    bruto = ingresos[ingresos["monto"] > 0]["monto"].sum()
    # Comisión 5% sobre Bruto
    comision = bruto * 0.05

    # Gastos por categoría
    fb = abs(gastos[gastos["source"] == "Facebook Ads"]["monto"].sum())
    sv = abs(gastos[gastos["source"] == "Sirvoy Software"]["monto"].sum())
    asis = abs(gastos[gastos["source"] == "Asistente Comercial"]["monto"].sum()) if "Asistente Comercial" in gastos["source"].values else 0

    neto = bruto - fb - sv - asis - comision
    transacciones = len(ingresos)

    return {
        "Semana": week_label,
        "Transacciones": transacciones,
        "Bruto": bruto,
        "Comision_5": comision,
        "Gasto_FB": fb,
        "Gasto_Sirvoy": sv,
        "Gasto_Asistente": asis,
        "Total_Gastos": fb + sv + asis,
        "Neto": neto,
    }

def main():
    print("=" * 60)
    print("📊 GENERACIÓN DE REPORTES SEMANALES")
    print(f"Período: {START.strftime('%d/%m/%Y')} al {END.strftime('%d/%m/%Y')}")
    print("=" * 60)

    # 1. Cargar datos desde MongoDB
    print("\n🔗 Conectando a MongoDB...")
    db = connect()
    df = load_data(db)

    if df.empty:
        print("❌ No hay datos en el rango solicitado.")
        return

    # 2. Construir semanas
    weeks = build_weekly_ranges(START, END)
    print(f"\n📅 {len(weeks)} semanas a generar")

    # 3. Procesar cada semana
    os.makedirs("reportes_semanales", exist_ok=True)
    pdf_gen = PDFGenerator()
    summary = []

    for i, (ws, we) in enumerate(weeks, 1):
        mask = (df["date"] >= ws) & (df["date"] <= we)
        week_df = df.loc[mask].copy()
        label = f"{ws.strftime('%d/%m')}-{we.strftime('%d/%m')}"

        if week_df.empty:
            summary.append({"Semana": label, "Transacciones": 0, "Bruto": 0,
                           "Comision_5": 0, "Total_Gastos": 0, "Neto": 0})
            print(f"  Semana {i:2d}: {label} — SIN DATOS")
            continue

        stats = process_week(week_df, label)
        summary.append(stats)

        # Preparar columnas para PDFGenerator
        pdf_df = week_df.copy()
        if "amount_gross" not in pdf_df.columns and "monto" in pdf_df.columns:
            pdf_df["amount_gross"] = pdf_df["monto"]
        if "amount_net" not in pdf_df.columns:
            pdf_df["amount_net"] = pdf_df["monto"]
        if "processor" not in pdf_df.columns:
            if "fuente" in pdf_df.columns:
                pdf_df["processor"] = pdf_df["fuente"]
            elif "metodo" in pdf_df.columns:
                pdf_df["processor"] = pdf_df["metodo"]
            else:
                pdf_df["processor"] = "Payments"
        if "transaction_id" not in pdf_df.columns:
            if "id_pago" in pdf_df.columns:
                pdf_df["transaction_id"] = pdf_df["id_pago"]
            else:
                pdf_df["transaction_id"] = pdf_df["monto"].astype(str)  # fallback
        if "customer_name" not in pdf_df.columns:
            pdf_df["customer_name"] = pdf_df.get("cliente", "") if "cliente" in pdf_df.columns else "Peña Linda"
        if "commission_chamba" not in pdf_df.columns:
            pdf_df["commission_chamba"] = 0.0
        if "commission_processor" not in pdf_df.columns:
            pdf_df["commission_processor"] = 0.0
        if "currency" not in pdf_df.columns:
            pdf_df["currency"] = "PEN"

        # Generar estadísticas para PDFGenerator
        pdf_stats = {
            'total_gross_income': stats["Bruto"],
            'total_facebook_expenses': stats["Gasto_FB"],
            'total_sirvoy_expenses': stats["Gasto_Sirvoy"],
            'total_assistant_expenses': stats["Gasto_Asistente"],
            'total_net_income': stats["Neto"],
            'total_chamba_commission': stats["Comision_5"],
            'total_processor_commission': 0,
            'pending_balance': 0,
            'total_abonos': 0,
            'total_to_pay': stats["Comision_5"],
            'net_balance': stats["Comision_5"],
            'roi_facebook': (stats["Neto"] / stats["Gasto_FB"] * 100) if stats["Gasto_FB"] > 0 else 0,
        }

        filename = f"reportes_semanales/Semana_{i:02d}_{ws.strftime('%Y%m%d')}_{we.strftime('%Y%m%d')}.pdf"
        try:
            pdf_gen.generate_report(pdf_df, pdf_stats, filename)
            print(f"  Semana {i:2d}: {label} → {filename} ✅")
        except Exception as e:
            print(f"  Semana {i:2d}: {label} — PDF ERROR: {e}")

    # 4. Exportar resumen CSV
    summary_df = pd.DataFrame(summary)
    csv_path = "reportes_semanales/resumen_semanal_03mar_29jun.csv"
    summary_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n📄 Resumen CSV: {csv_path}")

    # 5. Sumario acumulado
    total_bruto = summary_df["Bruto"].sum()
    total_comision = summary_df["Comision_5"].sum()
    total_gastos = summary_df["Total_Gastos"].sum()
    total_neto = summary_df["Neto"].sum()

    print(f"\n{'='*60}")
    print("✅ REPORTES SEMANALES COMPLETADOS")
    print(f"{'='*60}")
    print(f"{'Semana':<18} {'Bruto':>12} {'Comis 5%':>12} {'Gastos':>12} {'Neto':>12}")
    print(f"{'-'*18} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    for s in summary:
        print(f"{s['Semana']:<18} S/ {s['Bruto']:>8,.2f} S/ {s['Comision_5']:>8,.2f} S/ {s['Total_Gastos']:>8,.2f} S/ {s['Neto']:>8,.2f}")
    print(f"{'-'*18} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    print(f"{'TOTAL':<18} S/ {total_bruto:>8,.2f} S/ {total_comision:>8,.2f} S/ {total_gastos:>8,.2f} S/ {total_neto:>8,.2f}")
    print(f"\n📊 Comisión 5% acumulada: S/ {total_comision:,.2f}")
    print(f"📄 Reportes en: reportes_semanales/")

if __name__ == "__main__":
    main()
