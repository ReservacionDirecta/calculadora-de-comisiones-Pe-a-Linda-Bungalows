#!/usr/bin/env python3
"""
IMPORT DEFINITIVO: Reemplazar datos Sirvoy 03/03-29/06 en MongoDB.
Fuentes:
  - Export (14/03-29/06): 1,000 payments con signos correctos ✅
  - Scraped early positives (03/03-13/03): 140 payments
  - Scraped early reversions: 6 payments con montos determinados por booking
  - Scraped-only 14/03 morning: 6 payments (no están en export por hora)

Total: 1,152 payments, S/ 346,101.83 = Sirvoy Web exacto ✅
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']
col = db['pagos']

start = datetime(2026, 3, 3)
end = datetime(2026, 6, 29, 23, 59, 59)
mid = datetime(2026, 3, 14)

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        if s == '' or s == 'nan':
            return 0.0
        return float(s)
    except:
        return 0.0

print("="*70)
print("IMPORT DEFINITIVO SIRVOY (03/03-29/06)")
print("="*70)

# ===== 1. Cargar Export =====
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].str.replace('.','',regex=False).str.replace(',','.',regex=False).astype(float)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')

# ===== 2. Cargar Scraped =====
sc = pd.read_csv('secured (3).csv')
sc['monto'] = pd.to_numeric(sc['text-success'].str.replace('.','',regex=False).str.replace(',','.',regex=False), errors='coerce')
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = pd.to_datetime(sc['align-middle 2'], dayfirst=True, errors='coerce')
sc['Method'] = sc['align-middle 3'].fillna('')
sc['Comment'] = sc['align-middle 4'].fillna('')

# ===== 3. Construir lista maestra =====
payments = []
exp_ids = set(exp['Payment Id'].astype(str))

# 3a. Export payments (14/03-29/06)
for _, r in exp.iterrows():
    payments.append({
        'fuente': 'Sirvoy',
        'PaymentId': r['Payment Id'],
        'fecha': r['fecha'].to_pydatetime(),
        'monto': r['monto'],
        'metodo': r.get('Method', ''),
        'tipo_pago': 'Reversion' if r['monto'] < 0 else 'Pago',
        'comentario': str(r.get('Comment', '') or ''),
        'platform': 'sirvoy_export'
    })

# 3b. Scraped early (03/03-13/03): positives + reversions
early_sc = sc[(sc['fecha'] >= '2026-03-03') & (sc['fecha'] < '2026-03-14')].copy()

# Reversions amounts from booking matching
reversion_amounts = {
    '16537235': -433.16,  # Booking 43824
    '16527665': -400.00,  # Booking 43851
    '16526948': -145.11,  # Booking 43806
    '16510139': -134.37,  # Booking 43813
    '16510135': -333.71,  # Booking 43814
    '16510109': -494.27,  # Booking 43817
}

added_early = 0
for _, r in early_sc.iterrows():
    pid = str(r['PaymentId'])
    
    # Skip if already in export
    if pid in exp_ids:
        continue
    
    monto = r['monto'] if pd.notna(r['monto']) and r['monto'] > 0 else 0
    
    # Check if this is a reversion
    if monto == 0 and pid in reversion_amounts:
        monto = reversion_amounts[pid]
    
    if monto == 0:
        continue  # Skip any other zero-amount entries
    
    payments.append({
        'fuente': 'Sirvoy',
        'PaymentId': pid,
        'fecha': r['fecha'].to_pydatetime(),
        'monto': monto,
        'metodo': r.get('Method', r.get('align-middle 3', '')),
        'tipo_pago': 'Reversion' if monto < 0 else 'Pago',
        'comentario': str(r.get('Comment', r.get('align-middle 4', '')) or ''),
        'platform': 'sirvoy_scraped'
    })
    added_early += 1

# 3c. Scraped-only 14/03 morning (not in export, before 11:56)
later_sc = sc[(sc['fecha'] >= '2026-03-14') & ~sc['PaymentId'].isin(exp_ids)].copy()
added_later = 0
for _, r in later_sc.iterrows():
    monto = r['monto'] if pd.notna(r['monto']) and r['monto'] > 0 else 0
    if monto > 0:
        payments.append({
            'fuente': 'Sirvoy',
            'PaymentId': str(r['PaymentId']),
            'fecha': r['fecha'].to_pydatetime(),
            'monto': monto,
            'metodo': r.get('Method', r.get('align-middle 3', '')),
            'tipo_pago': 'Pago',
            'comentario': str(r.get('Comment', r.get('align-middle 4', '')) or ''),
            'platform': 'sirvoy_scraped'
        })
        added_later += 1

print(f"\n📊 Composición del dataset maestro:")
print(f"   Export (14/03-29/06):      {len(exp)} payments")
print(f"   Scraped early (03/03-13/03): {added_early} payments")
print(f"   Scraped 14/03 morning:     {added_later} payments")
print(f"   ───────────────────────────")
print(f"   TOTAL:                     {len(exp) + added_early + added_later} payments")
print(f"   Sirvoy Web:                1,152 payments")

# ===== 4. Verificar totales =====
total = sum(p['monto'] for p in payments)
print(f"\n💰 Total neto: S/ {total:,.2f}")
print(f"   Sirvoy Web: S/ 346,101.83")
match = "✅" if abs(total - 346101.83) < 0.5 else f"❌ Diff S/ {total - 346101.83:+.2f}"
print(f"   Match: {match}")

# Breakdown
pos = sum(p['monto'] for p in payments if p['monto'] > 0)
neg = sum(p['monto'] for p in payments if p['monto'] < 0)
n_pos = sum(1 for p in payments if p['monto'] > 0)
n_neg = sum(1 for p in payments if p['monto'] < 0)
print(f"   Positivos: {n_pos}  S/ {pos:,.2f}")
print(f"   Negativos: {n_neg}  S/ {neg:,.2f}")

if abs(total - 346101.83) >= 0.5:
    print("\n⚠️  TOTAL NO COINCIDE - REVISAR DATOS")
    exit(1)

# ===== 5. Ejecutar import =====
print(f"\n{'='*70}")
print("EJECUTANDO IMPORT...")
print("="*70)

# 5a. Delete existing Sirvoy data for period
result = col.delete_many({'fuente': 'Sirvoy', 'fecha': {'$gte': start, '$lte': end}})
print(f"\n🗑️  Eliminados {result.deleted_count} documentos Sirvoy ({start.date()} a {end.date()})")

# 5b. Insert new payments
import hashlib
for p in payments:
    p['hash'] = hashlib.md5(f"{p['PaymentId']}_{p['monto']}_{p['metodo']}".encode()).hexdigest()
    result = col.insert_one(p)
print(f"✅ Insertados {len(payments)} documentos")

# ===== 6. Verificar post-import =====
print(f"\n{'='*70}")
print("VERIFICACIÓN POST-IMPORT")
print("="*70)

verif = list(col.find({'fuente': 'Sirvoy', 'fecha': {'$gte': start, '$lte': end}}))
v_total = sum(d['monto'] for d in verif)
v_pos = sum(d['monto'] for d in verif if d['monto'] > 0)
v_neg = sum(d['monto'] for d in verif if d['monto'] < 0)
v_n_pos = sum(1 for d in verif if d['monto'] > 0)
v_n_neg = sum(1 for d in verif if d['monto'] < 0)

print(f"   Documentos: {len(verif)}")
print(f"   Neto: S/ {v_total:,.2f}")
print(f"   Positivos: {v_n_pos} S/ {v_pos:,.2f}")
print(f"   Negativos: {v_n_neg} S/ {v_neg:,.2f}")
print(f"   Sirvoy Web: S/ 346,101.83")
v_match = "✅" if abs(v_total - 346101.83) < 0.5 else f"❌ Diff S/ {v_total - 346101.83:+.2f}"
print(f"   Match: {v_match}")

# Check negatives
if v_n_neg > 0:
    print(f"\n   Reversiones en MongoDB:")
    for d in sorted(verif, key=lambda x: x['fecha']):
        if d['monto'] < 0:
            print(f"      S/ {d['monto']:>+9.2f}  {d['fecha'].strftime('%d/%m/%Y %H:%M')}  {d.get('metodo','')[:25]:<25}  ID:{str(d.get('PaymentId',''))[:8]}")

print(f"\n{'='*70}")
print("IMPORT COMPLETADO ✅" if v_match == "✅" else "IMPORT CON ERRORES ❌")
print("="*70)
