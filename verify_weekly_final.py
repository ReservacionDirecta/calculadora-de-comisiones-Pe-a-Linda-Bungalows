#!/usr/bin/env python3
"""Verificar totales semanales post-import vs Sirvoy Web."""
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# Define weeks 03/03 to 29/06 - each week ENDS at 23:59:59
weeks = []
d = datetime(2026, 3, 3)  # Tuesday
while d <= datetime(2026, 6, 29):
    d2 = d + timedelta(days=6, hours=23, minutes=59, seconds=59)
    if d2 > datetime(2026, 6, 29, 23, 59, 59):
        d2 = datetime(2026, 6, 29, 23, 59, 59)
    weeks.append((d, d2))
    d = d2 + timedelta(seconds=1)

# Sirvoy Web weekly totals (from user)
# The user provided some as reference
sirvoy_weekly = {
    '23/06-29/06': 17426.08,
    '16/06-22/06': 15753.13,
}

print("=" * 70)
print("VERIFICACIÓN SEMANAL POST-IMPORT")
print("=" * 70)
print(f"{'Semana':<22} {'MongoDB':>15} {'Sirvoy':>12} {'Match':>8}")
print("-" * 60)

total = 0
all_match = True
for start_date, end_date in weeks:
    week_key = f"{start_date.strftime('%d/%m')}-{end_date.strftime('%d/%m')}"
    
    docs = list(db['pagos'].find({
        'fuente': 'Sirvoy',
        'fecha': {'$gte': start_date, '$lte': end_date}
    }))
    week_total = sum(d['monto'] for d in docs)
    total += week_total
    
    sirvoy_expected = sirvoy_weekly.get(week_key, None)
    if sirvoy_expected is not None:
        match = "✅" if abs(week_total - sirvoy_expected) < 0.5 else f"❌"
        diff = week_total - sirvoy_expected
        match_str = f"{match} ({diff:+.2f})" if match == "❌" else f"{match}"
        print(f"{week_key:<22} S/{week_total:>12.2f} S/{sirvoy_expected:>10.2f} {match_str:>13}")
        if match == "❌":
            all_match = False
    else:
        print(f"{week_key:<22} S/{week_total:>12.2f} {'':>12} {'':>10}")

print("-" * 60)
print(f"{'TOTAL':<22} S/{total:>12.2f} S/{346101.83:>10.2f} {'✅' if abs(total - 346101.83) < 0.5 else '❌'}")

# Compare with export per week
print(f"\n{'='*70}")
print("VERIFICACIÓN vs EXPORT (semanas completas desde 14/03)")
print("="*70)

exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].str.replace('.','',regex=False).str.replace(',','.',regex=False).astype(float)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')

print(f"{'Semana':<22} {'MongoDB':>12} {'Export':>12} {'Match':>10}")
print("-" * 60)
all_export_ok = True
exp_total = 0
for start_date, end_date in weeks:
    week_key = f"{start_date.strftime('%d/%m')}-{end_date.strftime('%d/%m')}"
    
    exp_week = exp[(exp['fecha'] >= start_date) & (exp['fecha'] <= end_date)]
    exp_week_total = exp_week['monto'].sum()
    exp_total += exp_week_total
    
    if exp_week_total != 0:  # Only check weeks where export has data
        docs = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'fecha': {'$gte': start_date, '$lte': end_date}
        }))
        mongo_total = sum(d['monto'] for d in docs)
        match = "✅" if abs(mongo_total - exp_week_total) < 0.5 else "❌"
        print(f"{week_key:<22} S/{mongo_total:>10.2f} S/{exp_week_total:>10.2f} {match:>15}")
        if match == "❌":
            all_export_ok = False
    else:
        docs = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'fecha': {'$gte': start_date, '$lte': end_date}
        }))
        mongo_total = sum(d['monto'] for d in docs)
        print(f"{week_key:<22} S/{mongo_total:>10.2f} {'(sin export)':>15} {'':>8}")

print("-" * 60)
print(f"{'EXPORT TOTAL':<22} S/{exp_total:>10.2f}")
print(f"{'SIRVOY WEB':<22} S/ 302,035.59 (14/03-29/06)")

# Negatives breakdown
print(f"\n{'='*70}")
print("REVERSIONES POR FUENTE")
print("="*70)
for d in sorted(db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$lt': 0}}), key=lambda x: x['fecha']):
    src = d.get('platform', '?')
    print(f"  S/{d['monto']:>+9.2f}  {d['fecha'].strftime('%d/%m/%Y %H:%M')}  {d.get('metodo','')[:25]:<25}  [{src}]")
