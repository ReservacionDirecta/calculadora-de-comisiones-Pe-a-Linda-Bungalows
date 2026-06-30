#!/usr/bin/env python3
"""Analizar datos tempranos (03/03-13/03) faltantes del export."""
import pandas as pd
from datetime import datetime

# Cargar export
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].str.replace('.','',regex=False).str.replace(',','.',regex=False).astype(float)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')

# Cargar scraped
sc = pd.read_csv('secured (3).csv')
sc['monto'] = pd.to_numeric(sc['text-success'].str.replace('.','',regex=False).str.replace(',','.',regex=False), errors='coerce')
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = pd.to_datetime(sc['align-middle 2'], dayfirst=True, errors='coerce')

# Scraped IDs NO en export
exp_ids = set(exp['Payment Id'].astype(str))
sc['in_export'] = sc['PaymentId'].isin(exp_ids)

# Early March
early = sc[(sc['fecha'] >= '2026-03-03') & (sc['fecha'] < '2026-03-14')].copy()
print(f"Scraped payments 03/03-13/03: {len(early)}")
print(f"  In export: {(early['in_export']).sum()}")
print(f"  NOT in export: {(~early['in_export']).sum()}")

# Conteo de vacíos vs con monto
empty = early[early['monto'].isna() | (early['monto'] == 0)]
with_monto = early[early['monto'] > 0]
print(f"\n  Con monto (positivo): {len(with_monto)}")
print(f"  Vacío/cancelado: {len(empty)}")
print(f"  Total scraped early: {len(with_monto) + len(empty)}")

if len(with_monto) > 0:
    print(f"\n  Suma con monto: S/ {with_monto['monto'].sum():,.2f}")
    print(f"  Stats: min={with_monto['monto'].min():.2f} max={with_monto['monto'].max():.2f} mean={with_monto['monto'].mean():.2f}")
    high = with_monto[with_monto['monto'] > 5000]
    print(f"  >5000: {len(high)} payments")
    if len(high) > 0:
        print(f"\n  Pagos >5000 (posibles agregados):")
        for _, r in high.sort_values('monto', ascending=False).iterrows():
            print(f"    ID {r['PaymentId']:>8}  S/ {r['monto']:>+10.2f}  {r['align-middle 3']}  Book={r.get('align-middle 6','')}")

# Ver conteo total
print(f"\n{'='*60}")
print("PROPUESTA: usar export para 14/03-29/06 + MongoDB actual para 03/03-13/03")
print("="*60)

# Sirvoy Web total breakdown
# Sirvoy 03/03-29/06 = S/ 346,101.83
# Export 14/03-29/06 = ?
export_total = exp[(exp['fecha'] >= '2026-03-14') & (exp['fecha'] <= '2026-06-29 23:59')]['monto'].sum()
print(f"\nExport total (14/03-29/06): S/ {export_total:,.2f}")
print(f"Sirvoy Web (03/03-29/06):  S/ 346,101.83")
print(f"Early missing (03/03-13/03): S/ {346101.83 - export_total:,.2f}")
