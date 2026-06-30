#!/usr/bin/env python3
"""
Compara el scraped (secured (1).csv) contra MongoDB para verificar
que cada pago esté registrado correctamente con su signo real.
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# 1. Cargar scraped
df = pd.read_csv('secured (1).csv')
print(f"🔍 Verificando {len(df)} pagos del scraped contra MongoDB\n")

def parse_pen(s):
    s = str(s).strip()
    if not s or s == 'nan':
        return 0.0
    s = s.replace('.', '').replace(',', '.')
    return float(s)

df['monto_pos'] = df['text-success'].apply(parse_pen)
df['monto_neg'] = df['text-error'].apply(parse_pen)
df['monto_real'] = df['monto_pos'] + df['monto_neg']  # neg ya es negativo

errores = 0
correctos = 0
by_method = []

for _, row in df.iterrows():
    pid = str(row['align-middle'])
    fecha_str = row.get('align-middle 2', '')  # "28/06/2026 09:51" etc.
    method = row.get('align-middle 3', '')
    ref = row.get('align-middle 4', '')
    monto_real = row['monto_real']
    
    # Parsear fecha del scraped
    try:
        fecha_scraped = datetime.strptime(fecha_str.strip(), '%d/%m/%Y %H:%M')
    except:
        fecha_scraped = None
    
    # Buscar en MongoDB por monto (con tolerancia)
    monto_abs = abs(monto_real)
    docs = list(db['pagos'].find({
        'fuente': 'Sirvoy',
        'monto': {'$gte': monto_real - 0.1, '$lte': monto_real + 0.1},
        'metodo': method
    }).sort('fecha', -1))
    
    estado = "❌ NO ENCONTRADO"
    if docs:
        doc = docs[0]
        if doc['monto'] < 0 and monto_real < 0:
            estado = "✅ Negativo correcto"
            correctos += 1
        elif doc['monto'] > 0 and monto_real > 0:
            estado = "✅ Positivo correcto"
            correctos += 1
        elif doc['monto'] > 0 and monto_real < 0:
            estado = "⚠️ DEBERÍA SER NEGATIVO (es positivo)"
            errores += 1
        elif doc['monto'] < 0 and monto_real > 0:
            estado = "⚠️ DEBERÍA SER POSITIVO (es negativo)"
            errores += 1
        
        # Mostrar signo de scraped vs MongoDB
        scraped_str = f"S/ {monto_real:>+8.2f}"
        mongo_str = f"S/ {doc['monto']:>+8.2f}"
        fecha_doc = doc['fecha'].strftime('%d/%m/%Y %H:%M') if hasattr(doc['fecha'], 'strftime') else str(doc['fecha'])[:19]
        print(f"  {estado:35s} | ID {pid:>8} | {fecha_doc} | {method:25s} | Scraped: {scraped_str} | MongoDB: {mongo_str}")
    else:
        # Buscar con monto absoluto (podría estar como el opuesto)
        docs_abs = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'monto': {'$gte': monto_abs - 0.1, '$lte': monto_abs + 0.1},
            'metodo': method
        }))
        if docs_abs:
            doc = docs_abs[0]
            if monto_real < 0:
                estado = f"⚠️ DEBERÍA SER NEGATIVO (es +{doc['monto']:.2f})"
                errores += 1
            else:
                estado = f"⚠️ DEBERÍA SER POSITIVO (es {doc['monto']:.2f})"
                errores += 1
            scraped_str = f"S/ {monto_real:>+8.2f}"
            mongo_str = f"S/ {doc['monto']:>+8.2f}"
            print(f"  {estado:35s} | ID {pid:>8} | {method:25s} | Scraped: {scraped_str} | MongoDB: {mongo_str}")
        else:
            print(f"  {estado:35s} | ID {pid:>8} | {fecha_str:19s} | {method:25s} | Scraped: S/ {monto_real:>+8.2f} | MongoDB: NO EXISTE")
            errores += 1
    
    by_method.append({
        'pid': pid,
        'metodo': method,
        'scraped': monto_real,
        'fecha': fecha_str
    })

print(f"\n{'='*70}")
print(f"✅ Correctos: {correctos}")
print(f"❌ Errores:   {errores}")
print(f"{'='*70}")

# Resumen por método de pago
print(f"\n📊 Resumen por método:")
df_metodo = pd.DataFrame(by_method)
for metodo, group in df_metodo.groupby('metodo'):
    total = group['scraped'].sum()
    n = len(group)
    print(f"  {metodo:30s}  {n:2d} pagos  S/ {total:>+9.2f}")
print(f"  {'TOTAL':30s}  {len(df_metodo):2d} pagos  S/ {df_metodo['scraped'].sum():>+9.2f}")
