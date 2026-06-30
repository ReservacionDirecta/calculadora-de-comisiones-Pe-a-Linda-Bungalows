#!/usr/bin/env python3
"""Elimina Sirvoy duplicados y re-importa solo fechas nuevas (26-29 Jun)."""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import hashlib, json

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# 1. Delete all duplicate Sirvoy docs (with metadata/PaymentId)
del_result = db['pagos'].delete_many({'fuente': 'Sirvoy', 'metadata': {'$exists': True}})
print(f"Deleted: {del_result.deleted_count}")
print(f"Total pagos after delete: {db['pagos'].count_documents({})}")

# 2. Parse CSV and import only June 26-29
df = pd.read_csv('payments_export-2026-06-29_19_57_09.csv')

def parse_pen_amount(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

df['monto'] = df['Amount'].apply(parse_pen_amount)
df['fecha'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
df = df[(df['monto'] > 0) & (df['fecha'] >= datetime(2026, 6, 26))].copy()
print(f"\nDocs from 26/06: {len(df)}")
print(f"Date range: {df['fecha'].min()} to {df['fecha'].max()}")

new_count = 0
for _, row in df.iterrows():
    pid = str(row['Payment Id'])
    method = str(row.get('Method', ''))
    linked = str(row.get('Linked To', ''))

    doc = {
        'fuente': 'Sirvoy',
        'fecha': row['fecha'].to_pydatetime(),
        'monto': row['monto'],
        'moneda': 'PEN',
        'metodo': method,
        'categoria': 'Venta',
        'tipo_pago': 'Tarjeta' if any(w in method.lower() for w in ['card', 'tarj', 'visa', 'master', 'amex', 'diners']) else 'Transferencia',
        'metadata': json.dumps({'PaymentId': pid}),
        'hash': hashlib.md5(f'sirvoy_{pid}'.encode()).hexdigest()
    }
    if db['pagos'].find_one({'hash': doc['hash']}):
        continue
    db['pagos'].insert_one(doc)
    new_count += 1

print(f"New docs imported: {new_count}")
print(f"Total Sirvoy: {db['pagos'].count_documents({'fuente': 'Sirvoy'})}")
print(f"Total pagos: {db['pagos'].count_documents({})}")

# Verify latest 5
print("\nLatest 5 Sirvoy payments:")
for d in db['pagos'].find({'fuente': 'Sirvoy'}, {'fecha': 1, 'monto': 1, 'metodo': 1, '_id': 0}).sort('fecha', -1).limit(5):
    print(f"  {d['fecha']}  S/ {d['monto']:>8.2f}  {d['metodo']}")
