#!/usr/bin/env python3
"""Corregir los 5 negativos almacenados como positivos en MongoDB."""
from pymongo import MongoClient
import json

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# Mapeo de los pagos que están incorrectos
# payment_id -> (monto_actual_positivo, monto_correcto_negativo, metodo)
errores = [
    (17304191, 360.01, -360.01, 'Pago con tarjeta'),
    (17304169, 341.08, -341.08, 'Transferencia bancaria'),
    (17303864, 306.97, -306.97, 'Transferencia bancaria'),
    (17303822, 511.62, -511.62, 'Tarjeta/efectivo'),
    (17285287, 682.00, -682.00, 'Transferencia bancaria'),
]

for pid, monto_pos, monto_neg, metodo in errores:
    # Buscar el doc por monto POSITIVO + método + Sirvoy
    doc = db['pagos'].find_one({
        'fuente': 'Sirvoy',
        'monto': {'$gte': monto_pos - 0.1, '$lte': monto_pos + 0.1},
        'metodo': metodo
    })
    if doc:
        print(f"ID {pid} | S/ {doc['monto']:>8.2f} → S/ {monto_neg:>8.2f} | {metodo:25s} | _id: {doc['_id']}")
        # Corregir: poner monto negativo y agregar metadata de reversión
        db['pagos'].update_one(
            {'_id': doc['_id']},
            {'$set': {
                'monto': monto_neg,
                'tipo_pago': 'Reversion',
                'metadata': json.dumps({
                    'PaymentId': str(pid),
                    'Motivo': 'Devolucion/Reversion - corregido'
                })
            }}
        )
        print(f"  ✅ CORREGIDO")
    else:
        # No se encontró como positivo - buscar si ya es negativo
        doc_neg = db['pagos'].find_one({
            'fuente': 'Sirvoy',
            'monto': {'$gte': monto_neg - 0.1, '$lte': monto_neg + 0.1},
            'metodo': metodo
        })
        if doc_neg:
            print(f"ID {pid} | S/ {doc_neg['monto']:>8.2f} | {metodo:25s} | → YA ES NEGATIVO ✅")
        else:
            print(f"ID {pid} | NO ENCONTRADO en MongoDB ❌")

# Verificar resultados
print("\n=== Verificación ===")
for _, _, monto_neg, metodo in errores:
    doc = db['pagos'].find_one({
        'fuente': 'Sirvoy',
        'monto': {'$gte': monto_neg - 0.1, '$lte': monto_neg + 0.1},
        'metodo': metodo
    })
    print(f"  S/ {monto_neg:>8.2f}  {metodo:25s}  → {'✅' if doc else '❌'}")

# Total actual después de corrección
pipeline = [
    {'$match': {'fuente': 'Sirvoy', 'monto': {'$lt': 0}}},
    {'$group': {'_id': None, 'count': {'$sum': 1}, 'total': {'$sum': '$monto'}}}
]
r = list(db['pagos'].aggregate(pipeline))[0]
print(f"\nTotal negativos Sirvoy en MongoDB: {r['count']}")
print(f"Monto negativo total: S/ {r['total']:,.2f}")

total_sirvoy = db['pagos'].aggregate([
    {'$match': {'fuente': 'Sirvoy'}},
    {'$group': {'_id': None, 'count': {'$sum': 1}, 'total': {'$sum': '$monto'}}}
])['total']

# Better: just sum
total_all = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy'}))
total_pos = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$gt': 0}}))
total_neg = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$lt': 0}}))
print(f"\n📊 VENDIDO total Sirvoy: S/ {total_all:,.2f}")
print(f"   Positivos: S/ {total_pos:,.2f}")
print(f"   Negativos: S/ {total_neg:,.2f}")
