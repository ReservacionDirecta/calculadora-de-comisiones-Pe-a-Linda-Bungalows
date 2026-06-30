#!/usr/bin/env python3
"""
Importa el último reporte Sirvoy evitando duplicar pagos que ya existen.
AHORA INCLUYE NEGATIVOS (reversiones/devoluciones) en lugar de filtrarlos.

Estrategia: match por combinación fecha + monto + método.
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import hashlib, json, glob, os

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# 1. Auto-detectar el CSV más reciente
csv_pattern = 'payments_export-*.csv'
csv_files = sorted(glob.glob(csv_pattern))
if not csv_files:
    print("❌ No se encontró payments_export-*.csv")
    exit(1)
csv_path = csv_files[-1]  # el más reciente
print(f"📄 Leyendo: {csv_path}")

# 2. Leer CSV
df = pd.read_csv(csv_path)

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

df['monto'] = df['Amount'].apply(parse_pen)
df['fecha'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
# YA NO filtramos solo positivos — incluimos negativos (reversiones)
df = df.dropna(subset=['fecha'])

pos = len(df[df['monto'] > 0])
neg = len(df[df['monto'] < 0])
print(f"   {len(df)} filas ({pos} positivas, {neg} negativas)")
print(f"   Rango: {df['fecha'].min()} → {df['fecha'].max()}")
print(f"   Total: S/ {df['monto'].sum():,.2f}\n")

# 3. Construir huellas de Sirvoy existentes
print("🔍 Indexando Sirvoy existentes en MongoDB...")
existing = set()
for doc in db['pagos'].find({'fuente': 'Sirvoy'}, {'fecha': 1, 'monto': 1, 'metodo': 1}):
    fecha_day = doc['fecha'].strftime('%Y-%m-%d')
    monto_2d = round(doc['monto'], 2)
    metodo = str(doc.get('metodo', '')).strip().lower()
    fingerprint = (fecha_day, monto_2d, metodo)
    existing.add(fingerprint)

print(f"   {len(existing)} huellas únicas en DB\n")

# 4. Insertar solo los que NO tienen huella existente
nuevos = 0
duplicados = 0

for _, row in df.iterrows():
    pid = str(row['Payment Id'])
    method = str(row.get('Method', ''))
    linked = str(row.get('Linked To', ''))
    comment = str(row.get('Comment', ''))

    fecha_val = row['fecha']
    fecha_day = fecha_val.strftime('%Y-%m-%d')
    monto_2d = round(row['monto'], 2)
    metodo_clean = method.strip().lower()
    fingerprint = (fecha_day, monto_2d, metodo_clean)

    if fingerprint in existing:
        duplicados += 1
        continue

    # Clasificar tipo de pago
    m_lower = method.lower()
    if row['monto'] < 0:
        tipo = 'Reversion'
    elif any(w in m_lower for w in ['card', 'tarj', 'visa', 'master', 'amex', 'diners']):
        tipo = 'Tarjeta'
    elif any(w in m_lower for w in ['transferencia', 'transf']):
        tipo = 'Transferencia'
    elif any(w in m_lower for w in ['efectivo', 'cash']):
        tipo = 'Efectivo'
    else:
        tipo = 'Tarjeta'

    hash_val = hashlib.md5(f'sirvoy_{pid}'.encode()).hexdigest()

    # Para reversiones, comentario descriptivo
    meta = {'PaymentId': pid}
    if row['monto'] < 0:
        meta['Motivo'] = 'Devolucion/Reversion'

    doc = {
        'fuente': 'Sirvoy',
        'fecha': fecha_val.to_pydatetime(),
        'monto': row['monto'],  # se guarda con signo (negativo si es reversión)
        'moneda': 'PEN',
        'metodo': method,
        'categoria': 'Venta',
        'tipo_pago': tipo,
        'metadata': json.dumps(meta),
        'hash': hash_val
    }
    db['pagos'].insert_one(doc)
    existing.add(fingerprint)
    nuevos += 1
    print(f"  + {fecha_day}  S/ {row['monto']:>9.2f}  {method:25s}  PID:{pid}  → {tipo}")

print(f"\n✅ Nuevos insertados: {nuevos}")
print(f"⏭️  Duplicados (saltados): {duplicados}")

total_pagos = db['pagos'].count_documents({})
total_sirvoy = db['pagos'].count_documents({'fuente': 'Sirvoy'})
negativos = db['pagos'].count_documents({'fuente': 'Sirvoy', 'monto': {'$lt': 0}})
print(f"\n📊 MongoDB final: {total_pagos} total | {total_sirvoy} Sirvoy ({negativos} negativos)")

print("\nÚltimos 10 Sirvoy:")
for d in db['pagos'].find({'fuente': 'Sirvoy'}, {'fecha':1,'monto':1,'metodo':1,'_id':0}).sort('fecha',-1).limit(10):
    signo = "⚠️" if d['monto'] < 0 else "  "
    print(f"  {signo} {d['fecha']}  S/ {d['monto']:>9.2f}  {d['metodo']}")
