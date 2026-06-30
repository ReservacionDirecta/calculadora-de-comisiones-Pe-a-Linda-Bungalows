#!/usr/bin/env python3
"""
Analizar las 6 entradas vacías del scraped en período temprano y determinar
montos correctos para reversiones. También ver scraped-only IDs de 14/03.
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

start = datetime(2026, 3, 3)
mid = datetime(2026, 3, 14)
end = datetime(2026, 6, 29, 23, 59, 59)

# Cargar fuentes
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].str.replace('.','',regex=False).str.replace(',','.',regex=False).astype(float)
exp['tipo'] = exp['Amount'].str.contains('-', na=False).map({True: 'reversion', False: 'pago'})
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp['PaymentId'] = exp['Payment Id'].astype(str)

sc = pd.read_csv('secured (3).csv')
sc['monto'] = pd.to_numeric(sc['text-success'].str.replace('.','',regex=False).str.replace(',','.',regex=False), errors='coerce')
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = pd.to_datetime(sc['align-middle 2'], dayfirst=True, errors='coerce')

exp_ids = set(exp['PaymentId'])
sc['in_export'] = sc['PaymentId'].isin(exp_ids)

# ===== 1. Scraped entries from 03/03-13/03 =====
early_sc = sc[(sc['fecha'] >= '2026-03-03') & (sc['fecha'] < '2026-03-14')].copy()
print("=" * 70)
print("SCRAPED 03/03-13/03: Entradas vacías (cancelaciones/devoluciones)")
print("=" * 70)

empty = early_sc[early_sc['monto'].isna() | (early_sc['monto'] == 0)]
print(f"Total entries: {len(early_sc)} (pos: {len(early_sc[early_sc['monto'] > 0])}, empty: {len(empty)})")

for _, r in empty.iterrows():
    print(f"\n  ID {r['PaymentId']:>8}  {r['align-middle 2']:>20}  {r['align-middle 3']}")
    print(f"  Booking ref: {r.get('align-middle 6', 'N/A')}")
    # Buscar en MongoDB
    mongo_match = list(db['pagos'].find({'PaymentId': str(r['PaymentId']), 'fuente': 'Sirvoy'}))
    if mongo_match:
        for d in mongo_match:
            print(f"  ---> MONGO: S/ {d['monto']:>+8.2f}  {d['fecha'].strftime('%d/%m/%Y %H:%M')}  {d.get('metodo','')}")
    else:
        print(f"  ---> MONGO: NO ENCONTRADO")
    # Buscar en export
    exp_match = exp[exp['PaymentId'] == r['PaymentId']]
    if len(exp_match) > 0:
        for _, er in exp_match.iterrows():
            print(f"  ---> EXPORT: S/ {er['monto']:>+8.2f}  {er['Date']}  {er.get('Method','')}")

# ===== 2. Scraped-only IDs from 14/03 onwards =====
print(f"\n{'='*70}")
print("SCRAPED-ONLY IDs desde 14/03 (no están en export)")
print("="*70)

later = sc[(sc['fecha'] >= '2026-03-14') & ~sc['in_export']].copy()
print(f"Total: {len(later)}")
for _, r in later.iterrows():
    m = r['monto'] if pd.notna(r['monto']) else 0
    print(f"  ID {r['PaymentId']:>8}  S/ {m:>+8.2f}  {r['align-middle 2']:>20}  {r['align-middle 3']}  {'(CANCELADO)' if m == 0 else ''}")

# ===== 3. Verify: Sirvoy Web = Export total + early scraped positive + early reversions =====
print(f"\n{'='*70}")
print("ECUACIÓN DE TOTALES")
print("="*70)

# Expected Sirvoy Web = 346,101.83
# Export = 302,035.59
# Expected early (03/03-13/03) = 44,066.24
# Scraped early positives = ?  
sc_early_pos = early_sc[early_sc['monto'] > 0]['monto'].sum()
sc_early_neg = early_sc[early_sc['monto'].isna() | (early_sc['monto'] == 0)]  # unknown amounts

export_total = exp[exp['fecha'] >= '2026-03-14']['monto'].sum()

print(f"Export total (14/03-29/06):  S/ {export_total:>10.2f}")
print(f"Scraped early positives:    S/ {sc_early_pos:>10.2f}")
print(f"Total without reversions:   S/ {export_total + sc_early_pos:>10.2f}")
print(f"Sirvoy Web:                 S/ 346,101.83")
print(f"Needed EARLY REVERSIONS:    S/ {346101.83 - export_total - sc_early_pos:>+10.2f}")
print(f"  (This is the sum of the 6 early cancel/reversion entries)")
print(f"\nSo each of the 6 early reversions averages S/ {(346101.83 - export_total - sc_early_pos)/6:,.2f}")

# What does MongoDB have for those 6 IDs?
print(f"\n{'='*70}")
print("CROSS-REFERENCE: 6 EMPTY SCRAPED vs MONGO")
print("="*70)
for _, r in empty.iterrows():
    mongo_matches = list(db['pagos'].find({'PaymentId': str(r['PaymentId'])}))
    if mongo_matches:
        for d in mongo_matches:
            print(f"  ID {r['PaymentId']:>8} -> MONGO S/ {d['monto']:>+8.2f}  (fuente={d.get('fuente','?')})")
    else:
        print(f"  ID {r['PaymentId']:>8} -> NO ENCONTRADO en MongoDB")

# Also check what Sirvoy web shows for these IDs via the booking reference (align-middle 6)
print(f"\n  Referencias de booking para empty entries:")
for _, r in empty.iterrows():
    booking_ref = r.get('align-middle 6', 'N/A')
    print(f"  ID {r['PaymentId']:>8}  Booking ref: {booking_ref}  Fecha: {r['align-middle 2']}")
