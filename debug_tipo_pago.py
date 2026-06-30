#!/usr/bin/env python3
"""Diagnosticar por qué 0 docs Sirvoy pasan el filtro de tipo_pago."""
import pandas as pd
from datetime import datetime
from pymongo import MongoClient

cli = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
docs = list(cli['pena_linda']['pagos'].find({}, {'hash': 0}))
df = pd.DataFrame(docs)
df['date'] = pd.to_datetime(df['fecha'], errors='coerce')

# tiempo en Peru
df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')

fi = datetime(2026, 3, 3).date()
ff = datetime(2026, 6, 29).date()
mask = (df['date_pe'].dt.date >= fi) & (df['date_pe'].dt.date <= ff)
df_f = df[mask].copy()

print(f"df_f: {len(df_f)} docs")

# Tipo de pago: qué valores únicos tienen los docs Sirvoy en df_f?
sv_in_filter = df_f[df_f['fuente'] == 'Sirvoy']
print(f"\nSirvoy docs in df_f: {len(sv_in_filter)}")
print(f"tipo_pago unique: {sv_in_filter['tipo_pago'].unique().tolist()}")
print(f"tipo_pago counts:")
for tp, cnt in sv_in_filter['tipo_pago'].value_counts().items():
    print(f"  '{tp}': {cnt}")

# Are there any docs with tipo_pago 'Tarjeta'?
tarjeta = df_f[df_f['tipo_pago'] == 'Tarjeta']
print(f"\nDocs with tipo_pago='Tarjeta': {len(tarjeta)}")
if len(tarjeta) > 0:
    print(f"  fuentes: {tarjeta['fuente'].value_counts().to_dict()}")

# Full Sirvoy data overview
sv_all = df[df['fuente'] == 'Sirvoy']
print(f"\nALL Sirvoy docs: {len(sv_all)}")
print(f"tipo_pago value_counts:")
for tp, cnt in sv_all['tipo_pago'].value_counts().head(10).items():
    print(f"  '{tp}': {cnt}")

# Check a sample of our new Sirvoy docs (from 2026-03)
new_sv = sv_all[sv_all['date'] >= '2026-03-01'].head(5)
print("\nSample new Sirvoy docs:")
for _, r in new_sv.iterrows():
    print(f"  fecha={r['date']}  fuente='{r['fuente']}'  tipo_pago='{r['tipo_pago']}'  monto={r['monto']}")

# Check what 'tipo_pago' values exist across ALL data
print(f"\nALL tipo_pago values: {df['tipo_pago'].unique().tolist()}")
