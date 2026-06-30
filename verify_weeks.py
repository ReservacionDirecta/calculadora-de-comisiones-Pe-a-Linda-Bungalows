#!/usr/bin/env python3
"""Verificar en detalle una semana específica contra datos conocidos."""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def check_week(start_date, end_date, expected_total=None):
    """Verificar una semana completa."""
    docs = list(db['pagos'].find({
        'fuente': 'Sirvoy',
        'fecha': {'$gte': start_date, '$lte': end_date}
    }))
    
    total = sum(d['monto'] for d in docs)
    n_payments = len(docs)
    n_pos = sum(1 for d in docs if d['monto'] > 0)
    n_neg = sum(1 for d in docs if d['monto'] < 0)
    sum_pos = sum(d['monto'] for d in docs if d['monto'] > 0)
    sum_neg = sum(d['monto'] for d in docs if d['monto'] < 0)
    
    print(f"Semana: {start_date.strftime('%d/%m')}-{end_date.strftime('%d/%m')}")
    print(f"  Pagos: {n_payments} ({n_pos} pos + {n_neg} neg)")
    print(f"  Positivos: S/ {sum_pos:,.2f}")
    print(f"  Negativos: S/ {sum_neg:,.2f}")
    print(f"  Neto: S/ {total:,.2f}")
    if expected_total:
        match = "✅" if abs(total - expected_total) < 0.5 else "❌"
        print(f"  Esperado: S/ {expected_total:,.2f}  {match}")
    
    # Show all negatives in the week
    negs = [d for d in docs if d['monto'] < 0]
    if negs:
        print(f"  Reversiones ({len(negs)}):")
        for d in sorted(negs, key=lambda x: x['fecha']):
            print(f"    S/ {d['monto']:>+9.2f}  {d['fecha'].strftime('%d/%m %H:%M')}  {d.get('metodo','')}")
    
    # Show top 5 largest positive
    poss = sorted([d for d in docs if d['monto'] > 0], key=lambda x: -x['monto'])[:5]
    print(f"  Top 5 pagos:")
    for d in poss:
        print(f"    S/ {d['monto']:>+9.2f}  {d['fecha'].strftime('%d/%m %H:%M')}  {d.get('metodo','')}")
    
    # Source breakdown
    platforms = {}
    for d in docs:
        p = d.get('platform', '?')
        platforms[p] = platforms.get(p, {'count': 0, 'total': 0.0})
        platforms[p]['count'] += 1
        platforms[p]['total'] += d['monto']
    print(f"  Por fuente:")
    for p, info in sorted(platforms.items()):
        print(f"    {p}: {info['count']}  S/ {info['total']:,.2f}")
    
    return total

# Check specific weeks
check_week(datetime(2026, 3, 3), datetime(2026, 3, 9, 23, 59, 59))
print()
check_week(datetime(2026, 3, 10), datetime(2026, 3, 16, 23, 59, 59))
print()
check_week(datetime(2026, 6, 23), datetime(2026, 6, 29, 23, 59, 59), 17426.08)
print()
check_week(datetime(2026, 6, 16), datetime(2026, 6, 22, 23, 59, 59), 15753.13)
