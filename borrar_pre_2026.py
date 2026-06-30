#!/usr/bin/env python3
"""Borrar todos los documentos Sirvoy anteriores al 01/01/2026."""
from pymongo import MongoClient
from datetime import datetime

print("Conectando a MongoDB...")
c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# Contar antes
pre_2026 = db['pagos'].count_documents({
    'fuente': 'Sirvoy',
    'fecha': {'$lt': datetime(2026, 1, 1)}
})
total_sv = db['pagos'].count_documents({'fuente': 'Sirvoy'})
print(f"\nAntes de borrar:")
print(f"  Total Sirvoy: {total_sv}")
print(f"  Docs antes de 2026: {pre_2026}")

# Borrar
result = db['pagos'].delete_many({
    'fuente': 'Sirvoy',
    'fecha': {'$lt': datetime(2026, 1, 1)}
})
print(f"\nBorrados: {result.deleted_count} docs")

# Contar después
post = db['pagos'].count_documents({'fuente': 'Sirvoy'})
print(f"Restantes: {post} docs")

# Rango de fechas restantes
fechas = list(db['pagos'].find({'fuente': 'Sirvoy'}).sort('fecha', 1).limit(1))
if fechas:
    print(f"Desde: {fechas[0]['fecha']}")
fechas2 = list(db['pagos'].find({'fuente': 'Sirvoy'}).sort('fecha', -1).limit(1))
if fechas2:
    print(f"Hasta: {fechas2[0]['fecha']}")

pos = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$gt': 0}}))
neg = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$lt': 0}}))
print(f"Positivos restantes: S/ {pos:,.2f}")
print(f"Negativos restantes: S/ {neg:,.2f}")
print(f"Neto: S/ {pos + neg:,.2f}")
