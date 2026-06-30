#!/usr/bin/env python3
"""Verificar diferencia con Sirvoy web: S/ 744,948.52 vs MongoDB S/ 745,168.41."""
from pymongo import MongoClient
from datetime import datetime

c = MongoClient('localhost', 27017)
db = c['pena_linda']

# Todos los Sirvoy desde 01/01/2026
docs = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': datetime(2026, 1, 1, 0, 0, 0), '$lte': datetime(2026, 6, 29, 23, 59, 59)}
}, sort=[('fecha', 1)]))

total = sum(d['monto'] for d in docs)
positivos = sum(d['monto'] for d in docs if d['monto'] > 0)
negativos = sum(d['monto'] for d in docs if d['monto'] < 0)

print(f"Total MongoDB Sirvoy (01/01-29/06): S/ {total:,.2f}")
print(f"  Positivos: S/ {positivos:,.2f}")
print(f"  Negativos: S/ {negativos:,.2f}")
print(f"  Docs: {len(docs)}")
print()
print("Objetivo Sirvoy Web: S/ 744,948.52 · 2,102 transacciones")
print(f"Diferencia: S/ {total - 744948.52:+.2f}")
print(f"Diferencia docs: {len(docs) - 2102:+d}")
print()

# Ver distribución por mes
from collections import defaultdict
meses = defaultdict(lambda: {'monto': 0.0, 'count': 0})
for d in docs:
    m = d['fecha'].strftime('%Y-%m')
    meses[m]['monto'] += d['monto']
    meses[m]['count'] += 1
for m in sorted(meses):
    info = meses[m]
    print(f"  {m}: S/ {info['monto']:>10,.2f} ({info['count']} docs)")

print()

# Ver docs sin transaction_id (podrían ser duplicados)
sin_tid = [d for d in docs if not d.get('transaction_id')]
print(f"Docs sin transaction_id: {len(sin_tid)}")
if sin_tid:
    for d in sin_tid[:20]:
        print(f"  {d.get('_id')}: S/ {d['monto']:,.2f} {d.get('fecha')} {d.get('metodo','')}")

# Verificar duplicados por transaction_id
from collections import Counter
tids = [d.get('transaction_id') for d in docs if d.get('transaction_id')]
dup_tids = {tid: cnt for tid, cnt in Counter(tids).items() if cnt > 1}
if dup_tids:
    print(f"\nTransaction IDs duplicados: {len(dup_tids)}")
    for tid, cnt in sorted(dup_tids.items(), key=lambda x: -x[1])[:10]:
        dup_docs = [d for d in docs if d.get('transaction_id') == tid]
        print(f"  {tid}: {cnt}x → montos: {[d['monto'] for d in dup_docs]}")
else:
    print("Sin duplicados por transaction_id ✅")

# Últimos docs de enero 2026 (los viejos que no se reimportaron)
ene_docs = [d for d in docs if d['fecha'].month == 1 and d['fecha'].year == 2026]
if ene_docs:
    print(f"\nDocs de enero 2026 (import antiguo, no re-importado): {len(ene_docs)}")
    print(f"  Subtotal: S/ {sum(d['monto'] for d in ene_docs):,.2f}")
    print(f"  únicos vs repetidos: ...")
    # Mostrar primeros 5 y últimos 5
    for d in ene_docs[:3]:
        print(f"  {d['fecha'].strftime('%d/%m/%Y')} S/ {d['monto']:>10,.2f} tid={d.get('transaction_id','?')} {d.get('metodo','')}")
    print(f"  ...")
    for d in ene_docs[-3:]:
        print(f"  {d['fecha'].strftime('%d/%m/%Y')} S/ {d['monto']:>10,.2f} tid={d.get('transaction_id','?')} {d.get('metodo','')}")
