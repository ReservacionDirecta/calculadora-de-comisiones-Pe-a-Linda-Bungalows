#!/usr/bin/env python3
"""Diagnóstico Sirvoy - distribución por fechas."""
from pymongo import MongoClient
from datetime import datetime

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

total = db['pagos'].count_documents({'fuente': 'Sirvoy'})
print(f"Total Sirvoy: {total}")

# Count by year
for anio in [2025, 2026]:
    cnt = db['pagos'].count_documents({
        'fuente': 'Sirvoy',
        'fecha': {'$gte': datetime(anio, 1, 1), '$lt': datetime(anio+1, 1, 1)}
    })
    print(f"  {anio}: {cnt} docs")

# Check first and last
pipe = [{'$match': {'fuente': 'Sirvoy'}}, {'$sort': {'fecha': 1}}, {'$limit': 3}]
for d in db['pagos'].aggregate(pipe):
    print(f"  Primeros: _id={d['_id']} fecha={d['fecha']} monto={d['monto']} metodo={d['metodo']}")

pipe2 = [{'$match': {'fuente': 'Sirvoy'}}, {'$sort': {'fecha': -1}}, {'$limit': 3}]
for d in db['pagos'].aggregate(pipe2):
    print(f"  Ultimos: _id={d['_id']} fecha={d['fecha']} monto={d['monto']} metodo={d['metodo']}")

# Total sum
pos_sum = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$gt': 0}}))
neg_sum = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$lt': 0}}))
print(f"\nTotal positivos: S/ {pos_sum:,.2f}")
print(f"Total negativos: S/ {neg_sum:,.2f}")
print(f"Neto: S/ {pos_sum + neg_sum:,.2f}")
