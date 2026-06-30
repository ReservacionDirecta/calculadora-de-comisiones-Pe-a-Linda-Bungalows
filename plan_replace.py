#!/usr/bin/env python3
"""
Verificación de datos MONGO para 03/03-13/03 y plan de reemplazo para 14/03-29/06.
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

start = datetime(2026, 3, 3)
mid = datetime(2026, 3, 14)  # Exclusive (data before this stays)
end = datetime(2026, 6, 29, 23, 59, 59)

# ===== Verificar data temprana en MongoDB (03/03-13/03) =====
print("=" * 70)
print("VERIFICACIÓN MONGO 03/03-13/03 (data que se conserva)")
print("=" * 70)

early = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': start, '$lt': mid}
}).sort('fecha', 1))

pos_early = sum(d['monto'] for d in early if d['monto'] > 0)
neg_early = sum(d['monto'] for d in early if d['monto'] < 0)
net_early = sum(d['monto'] for d in early)

print(f"  Total docs: {len(early)}")
print(f"  Positivos:  {sum(1 for d in early if d['monto'] > 0)}  S/ {pos_early:,.2f}")
print(f"  Negativos:  {sum(1 for d in early if d['monto'] < 0)}  S/ {neg_early:,.2f}")
print(f"  Neto:       S/ {net_early:,.2f}")
print(f"  Esperado:   S/ 44,066.24")
match = "✅" if abs(net_early - 44066.24) < 0.5 else "❌"
print(f"  Match:      {match} (diff S/ {net_early - 44066.24:+.2f})")

# Show any negatives in early period
negs = [d for d in early if d['monto'] < 0]
if negs:
    print(f"\n  Negativos en período temprano:")
    for d in negs:
        print(f"    S/ {d['monto']:>+10.2f}  {d['fecha'].strftime('%d/%m/%Y %H:%M')}  {str(d.get('metodo','')):30s}  PaymentId={str(d.get('PaymentId','N/A'))[:10]}")

# ===== Verificar data media en Export =====  
print(f"\n{'='*70}")
print("VERIFICACIÓN EXPORT 14/03-29/06 (data que se reimporta)")
print("="*70)

exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].str.replace('.','',regex=False).str.replace(',','.',regex=False).astype(float)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp_filtered = exp[(exp['fecha'] >= '2026-03-14') & (exp['fecha'] <= '2026-06-29 23:59')]

n_pos = (exp_filtered['monto'] > 0).sum()
n_neg = (exp_filtered['monto'] < 0).sum()
tot = exp_filtered['monto'].sum()
print(f"  Total: {len(exp_filtered)} payments")
print(f"  Positivos: {n_pos}  Negativos: {n_neg}")
print(f"  Neto: S/ {tot:,.2f}")
print(f"  Esperado: S/ 302,035.59")
match2 = "✅" if abs(tot - 302035.59) < 0.5 else "❌"
print(f"  Match: {match2} (diff S/ {tot - 302035.59:+.2f})")

# Check if there are documents in MongoDB for the mid period that we'll delete
mid_mongo = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': mid, '$lte': end}
}))
print(f"\n  Docs a ELIMINAR en MongoDB (14/03-29/06): {len(mid_mongo)}")
print(f"  Neto actual MongoDB: S/ {sum(d['monto'] for d in mid_mongo):,.2f}")
print(f"  Neto nuevo (export): S/ {tot:,.2f}")

# ===== Proyección final =====
print(f"\n{'='*70}")
print("PROYECCIÓN FINAL")
print("="*70)
print(f"  Temprano (MongoDB):  S/ {net_early:>+10.2f}")
print(f"  Nuevo (Export):      S/ {tot:>+10.2f}")
print(f"  ─────────────────────────")
print(f"  TOTAL:               S/ {net_early + tot:>+10.2f}")
print(f"  Sirvoy Web:          S/ 346,101.83")
print(f"  Match: {'✅' if abs(net_early + tot - 346101.83) < 0.5 else '❌'} (diff S/ {net_early + tot - 346101.83:+.2f})")
print(f"\n  Acción: borrar {len(mid_mongo)} docs MONGO + insertar {len(exp_filtered)} docs EXPORT")
