#!/usr/bin/env python3
"""Simular exactamente lo que hace el dashboard para diagnosticar S/ 0.00."""
import pandas as pd
from datetime import datetime
from pymongo import MongoClient

cli = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
docs = list(cli['pena_linda']['pagos'].find({}, {'hash': 0}))

df = pd.DataFrame(docs)
df['date'] = pd.to_datetime(df['fecha'], errors='coerce')

# Sirvoy only
sv = df[df['fuente'] == 'Sirvoy'].copy()
print(f"Total Sirvoy docs: {len(sv)}")
print(f"Fecha range: {sv['date'].min()} to {sv['date'].max()}")
print(f"Total amount: S/ {sv['monto'].sum():,.2f}")
print(f"Positivos: S/ {sv[sv['monto']>0]['monto'].sum():,.2f}")
print(f"Negativos: S/ {sv[sv['monto']<0]['monto'].sum():,.2f}")

# Simulate load_all() tz handling
df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')
sv['date_pe'] = sv['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')

print(f"\ndate_pe range: {sv['date_pe'].min()} to {sv['date_pe'].max()}")

# Filter like dashboard does
fi = datetime(2026, 3, 3).date()
ff = datetime(2026, 6, 29).date()
# Dashboard uses df, not sv directly
# First filter by tipo_pago and fuente
is_sale = ~df['tipo_pago'].isin(['Costo']) & ~df['fuente'].isin(['Abono Chamba', 'Saldo Base'])
sv_sales = df[is_sale & df['tipo_pago'].isin(['Tarjeta', 'Transferencia', 'Efectivo'])]
mask = (df['date_pe'].dt.date >= fi) & (df['date_pe'].dt.date <= ff)
df_f = df[mask].copy()

# Now calc_kpis replicated
is_sale_f = ~df_f['tipo_pago'].isin(['Costo']) & ~df_f['fuente'].isin(['Abono Chamba', 'Saldo Base'])
sv_sales_f = df_f[is_sale_f & df_f['tipo_pago'].isin(['Tarjeta', 'Transferencia', 'Efectivo'])]
sv_sirvoy_f = sv_sales_f[sv_sales_f['fuente'] == 'Sirvoy']

df['amount'] = pd.to_numeric(df['monto'], errors='coerce')
df['tipo_pago'] = df['tipo_pago'].fillna('Otros')
df['es_link'] = df['es_link'].fillna(False)

sv_sales_f['amount'] = pd.to_numeric(sv_sales_f['monto'], errors='coerce')
sv_sirvoy_f['amount'] = pd.to_numeric(sv_sirvoy_f['monto'], errors='coerce')

tb_sirvoy = float(sv_sirvoy_f['amount'].sum())
print(f"\n=== KPI Simulation ===")
print(f"df_f docs: {len(df_f)}")
print(f"sv_sales_f docs: {len(sv_sales_f)}")
print(f"sv_sirvoy_f docs: {len(sv_sirvoy_f)}")
print(f"tb_sirvoy (ventas Sirvoy): S/ {tb_sirvoy:,.2f}")
print(f"Transacciones Sirvoy: {len(sv_sirvoy_f)}")

# Check NaT in date_pe
nat_count = df['date_pe'].isna().sum()
total_count = len(df)
print(f"\ndate_pe NaT: {nat_count}/{total_count}")

# Check for NaN in amount
nan_amount = df['amount'].isna().sum()
print(f"amount NaN: {nan_amount}/{total_count}")
