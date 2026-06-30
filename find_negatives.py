#!/usr/bin/env python3
"""Analyze the negative amount problem in detail."""
from pymongo import MongoClient
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# 1. Check if any negatives were stored as positives
print("=== ¿Hay negativos almacenados como POSITIVOS? ===")
# Look for the specific negative amounts from new CSV
df = pd.read_csv('payments_export-2026-06-30_09_44_18.csv')
def parse_pen(s):
    try: s = str(s).strip().replace('.', '').replace(',', '.'); return float(s)
    except: return 0.0
df['monto'] = df['Amount'].apply(parse_pen)

negatives = df[df['monto'] < 0]
print("En el nuevo CSV exportado hay estos negativos:")
for _, r in negatives.iterrows():
    pid = r['Payment Id']
    monto = r['monto']
    method = r.get('Method', '')
    # Check if stored as negative (correct)
    correct = db['pagos'].find_one({'fuente': 'Sirvoy', 'monto': {'$gte': monto - 0.5, '$lte': monto + 0.5}, 'metodo': method})
    # Check if stored as POSITIVE (wrong!)
    wrong = db['pagos'].find_one({'fuente': 'Sirvoy', 'monto': {'$gte': abs(monto) - 0.5, '$lte': abs(monto) + 0.5}, 'metodo': method})
    result = ""
    if correct:
        result = "✅ correcto (negativo)"
    elif wrong:
        result = "⚠️ ALMACENADO COMO POSITIVO!"
    else:
        result = "❌ faltante (no existe)"
    print(f"  ID {pid:>8}  S/ {monto:>8.2f}  {method:30s}  → {result}")

# 2. Total negative amounts impact
print("\n=== Impacto de los negativos ===")
pipeline = [
    {'$match': {'fuente': 'Sirvoy', 'monto': {'$lt': 0}}},
    {'$group': {'_id': None, 'count': {'$sum': 1}, 'total': {'$sum': '$monto'}}}
]
result = list(db['pagos'].aggregate(pipeline))
if result:
    r = result[0]
    print(f"Total negativos en MongoDB: {r['count']}")
    print(f"Monto total negativo: S/ {r['total']:,.2f}")

# All Sirvoy total
total_sirvoy = db['pagos'].aggregate([
    {'$match': {'fuente': 'Sirvoy'}},
    {'$group': {'_id': None, 'count': {'$sum': 1}, 'total': {'$sum': '$monto'}}}
])
t = list(total_sirvoy)[0]
print(f"\nTotal Sirvoy en MongoDB:")
print(f"  Documentos: {t['count']}")
print(f"  Monto total: S/ {t['total']:,.2f}")
print(f"  Nota: Este total ya incluye los {result[0]['count'] if result else 0} negativos (restados)")

# 3. Check the dashboard KPI calculation
# The "VENDIDO" KPI uses Sirvoy bruto - does it sum correctly?
print("\n=== VENDIDO (Sirvoy) con/sin negativos ===")
all_sirvoy = db['pagos'].find({'fuente': 'Sirvoy'})
total_all = sum(d['monto'] for d in all_sirvoy)
total_pos = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$gt': 0}}))
total_neg = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$lt': 0}}))
print(f"  Suma positivos: S/ {total_pos:,.2f}")
print(f"  Suma negativos: S/ {total_neg:,.2f}")
print(f"  Neto (correcto): S/ {total_all:,.2f}")
print(f"  Sin negativos (incorrecto): S/ {total_pos:,.2f}")
print(f"  Diferencia: S/ {total_pos - total_all:,.2f} {'✅ correcto' if abs(total_all - (total_pos + total_neg)) < 1 else '❌ error'}")

# 4. Check which negatives are the 5 missing ones
print("\n=== Los 5 negativos que FALTAN en MongoDB ===")
missing_list = [
    (17304191, -360.01, 'Pago con tarjeta'),
    (17304169, -341.08, 'Transferencia bancaria'),
    (17303864, -306.97, 'Transferencia bancaria'),
    (17303822, -511.62, 'Tarjeta/efectivo'),
    (17285287, -682.00, 'Transferencia bancaria'),
]
total_missing = 0
for pid, monto, metodo in missing_list:
    exists = db['pagos'].find_one({'fuente': 'Sirvoy', 'monto': {'$gte': monto - 0.1, '$lte': monto + 0.1}, 'metodo': metodo})
    if not exists:
        print(f"  ID {pid}  S/ {monto:>8.2f}  {metodo}  → ❌ FALTA")
        total_missing += monto
    else:
        print(f"  ID {pid}  S/ {monto:>8.2f}  {metodo}  → ✅ EXISTE")

print(f"\n  Total faltante: S/ {total_missing:,.2f}")
