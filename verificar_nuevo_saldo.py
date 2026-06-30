#!/usr/bin/env python3
"""Simular la nueva lógica de data.py para verificar el saldo."""
from pymongo import MongoClient
import pandas as pd
from datetime import datetime

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# Cargar datos como data.py
df = pd.DataFrame(list(db['pagos'].find({}, {'hash': 0})))
cobros_df_raw = list(db['cobros'].find({}))

if df.empty:
    print("ERROR: No data")
    exit(1)

# Timezone handling (mismo que data.py)
df['date'] = pd.to_datetime(df['fecha'], errors='coerce')
df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')
df['amount'] = pd.to_numeric(df['monto'], errors='coerce')
df['tipo_pago'] = df['tipo_pago'].fillna('Otros')
df['es_link'] = df['es_link'].fillna(False)

# --- NUEVA LÓGICA ---
fecha_base = pd.Timestamp("2026-03-03").date()

# Comisión acumulada (NETO)
sv_desde_mar = df[(df["date_pe"].dt.date >= fecha_base) & (df["fuente"] == "Sirvoy")]
comision_desde_mar = float(sv_desde_mar["amount"].sum() * 0.05)

# Costos acumulados
costos_hist = df[(df["date_pe"].dt.date >= fecha_base) & (df["tipo_pago"] == "Costo") & (df["fuente"] != "Saldo Base")]
total_costos_hist = float(costos_hist["amount"].sum())

# Saldo Base
saldo_base_hist = float(df[df["fuente"] == "Saldo Base"]["amount"].sum())

# Abonos
total_abonos = 0.0
if cobros_df_raw:
    cobros_df = pd.DataFrame(cobros_df_raw)
    cobros_df['fecha_dt'] = pd.to_datetime(cobros_df['fecha'], errors='coerce')
    mask_c = cobros_df["fecha_dt"].dt.date >= fecha_base
    # filter rows with tipo=='abono'
    abono_rows = cobros_df[mask_c & (cobros_df["tipo"] == "abono")]
    total_abonos = float(abono_rows["monto"].sum())

adeudado = saldo_base_hist + comision_desde_mar + total_costos_hist
saldo_pendiente = max(0.0, adeudado - total_abonos)

print("=" * 60)
print("✅ NUEVA LÓGICA DE SALDO (acumulado desde 03/03)")
print("=" * 60)
print(f"  Saldo Base (heredado):       S/ {saldo_base_hist:>10,.2f}")
print(f"  + Comisión 5% NETO Sirvoy:  S/ {comision_desde_mar:>10,.2f}")
print(f"  + Costos operativos:         S/ {total_costos_hist:>10,.2f}")
print(f"  ──────────────────────────────────────────")
print(f"  = Adeudado:                  S/ {adeudado:>10,.2f}")
print(f"  - Abonos recibidos:          S/ {total_abonos:>10,.2f}")
print(f"  ──────────────────────────────────────────")
print(f"  = Saldo Pendiente:           S/ {saldo_pendiente:>10,.2f}")

print(f"\n  ─── Verificación ───")
print(f"  Sirvoy NET desde 03/03:     S/ {sv_desde_mar['amount'].sum():,.2f}")
print(f"  Comisión 5%:                S/ {sv_desde_mar['amount'].sum() * 0.05:,.2f}")
print(f"  Costos (FB+SV+Asis+Extra):  S/ {total_costos_hist:,.2f}")
print(f"  Abonos desde 03/03:         S/ {total_abonos:,.2f}")
print(f"  Docs cobros tipo abono:     {len(abono_rows) if cobros_df_raw else 0}")
