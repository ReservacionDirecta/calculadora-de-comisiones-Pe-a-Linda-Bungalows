#!/usr/bin/env python3
"""
Corregir tipo_pago de documentos Sirvoy para que el dashboard los muestre.
El dashboard filtra por tipo_pago IN ['Tarjeta','Transferencia','Efectivo'].
Pero nuestro import puso 'Pago' y 'Reversion'.
"""
from pymongo import MongoClient
from datetime import datetime

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def classify_tipo(metodo):
    """Mapear método de pago a tipo_pago esperado por dashboard."""
    m = str(metodo).lower().strip()
    if 'tarjeta' in m or m in ('pago con tarjeta', 'tarjeta/efectivo', 'card', 'visa', 'mastercard', 'mc'):
        return 'Tarjeta'
    if 'transferencia' in m or 'transf' in m or m == 'transferencia bancaria':
        return 'Transferencia'
    if 'efectivo' in m or 'cash' in m or m == 'efectivo':
        return 'Efectivo'
    # Fallback - check common patterns
    if m in ('', 'otro', 'otros'):
        return 'Tarjeta'
    return 'Tarjeta'  # default

# Fix ALL Sirvoy docs (including old ones before March)
sirvoy_docs = list(db['pagos'].find({'fuente': 'Sirvoy'}))
print(f"Total Sirvoy docs: {len(sirvoy_docs)}")

fixed = 0
for doc in sirvoy_docs:
    old_tp = doc.get('tipo_pago', '')
    metodo = doc.get('metodo', '')
    new_tp = classify_tipo(metodo)
    
    if old_tp != new_tp:
        # For reversions, determine the correct tipo
        monto = doc.get('monto', 0)
        if monto < 0 and new_tp == 'Tarjeta':
            # Keep it, or could keep 'Reversion'... but dashboard needs Tarjeta/Transferencia/Efectivo
            pass  # Use classified tipo based on method
            
        db['pagos'].update_one(
            {'_id': doc['_id']},
            {'$set': {'tipo_pago': new_tp}}
        )
        fixed += 1
        if fixed <= 5:
            print(f"  S/{doc.get('monto',0):>+10.2f}  {doc.get('fecha','')}  '{old_tp}' -> '{new_tp}'  (metodo: '{metodo}')")

print(f"\nCorregidos: {fixed} documentos")

# Verify
docs_new = list(db['pagos'].find({'fuente': 'Sirvoy'}))
tp_counts = {}
for d in docs_new:
    tp = d.get('tipo_pago', '?')
    tp_counts[tp] = tp_counts.get(tp, 0) + 1
print(f"\ntipo_pago distribution:")
for tp, cnt in sorted(tp_counts.items()):
    print(f"  '{tp}': {cnt}")

# Verify dashboard would now show data
import pandas as pd
all_docs = list(db['pagos'].find({}, {'hash': 0}))
df = pd.DataFrame(all_docs)
df['date'] = pd.to_datetime(df['fecha'], errors='coerce')
df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')
df['amount'] = pd.to_numeric(df['monto'], errors='coerce')
df['tipo_pago'] = df['tipo_pago'].fillna('Otros')
df['es_link'] = df['es_link'].fillna(False)

fi = datetime(2026, 3, 3).date()
ff = datetime(2026, 6, 29).date()
mask = (df['date_pe'].dt.date >= fi) & (df['date_pe'].dt.date <= ff)
df_f = df[mask].copy()

is_sale = ~df_f['tipo_pago'].isin(['Costo']) & ~df_f['fuente'].isin(['Abono Chamba', 'Saldo Base'])
sv_sales = df_f[is_sale & df_f['tipo_pago'].isin(['Tarjeta', 'Transferencia', 'Efectivo'])]
sv_sirvoy = sv_sales[sv_sales['fuente'] == 'Sirvoy']

tb_sirvoy = float(sv_sirvoy['amount'].sum())
print(f"\n=== VERIFICACIÓN DASHBOARD ===")
print(f"df_f: {len(df_f)} docs")
print(f"sv_sales_f: {len(sv_sales)} docs")
print(f"sv_sirvoy_f: {len(sv_sirvoy)} docs")
print(f"tb_sirvoy (ventas Sirvoy): S/ {tb_sirvoy:,.2f}")
print(f"Transacciones Sirvoy: {len(sv_sirvoy)}")
