#!/usr/bin/env python3
"""
Seed MongoDB — Peña Linda Bungalows
Lee todos los CSVs, deduplica y carga en MongoDB.
Campos unificados para todas las fuentes.
"""
import pandas as pd, os, sys, warnings, hashlib, numpy as np
from datetime import datetime
from pymongo import MongoClient, errors
warnings.filterwarnings('ignore')

CARPETA = os.path.dirname(os.path.abspath(__file__))
client = MongoClient('mongodb://localhost:27017/')
db = client['pena_linda']
collection = db['pagos']

# Crear índice único por hash para deduplicación
collection.create_index('hash', unique=True, background=True)
collection.create_index('fecha')
collection.create_index('fuente')
collection.create_index('tipo_pago')
collection.create_index('es_link')

def generar_hash(doc):
    """Genera un hash único para evitar duplicados"""
    raw = f"{doc['fuente']}|{doc.get('transaction_id','')}|{doc.get('fecha','')}|{doc.get('monto',0)}|{doc.get('metodo','')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def insertar_documentos(documentos, fuente_nombre):
    """Inserta documentos evitando duplicados"""
    insertados, duplicados, errores = 0, 0, 0
    for doc in documentos:
        doc['hash'] = generar_hash(doc)
        doc['_cargado'] = datetime.now()
        try:
            collection.insert_one(doc)
            insertados += 1
        except errors.DuplicateKeyError:
            duplicados += 1
        except Exception:
            errores += 1
    print(f"  ✅ {fuente_nombre}: {insertados} nuevos, {duplicados} duplicados, {errores} errores")
    return insertados, duplicados, errores

total_global = 0

# ═══ 1. SIRVOY GLOBAL (ene-jun scraper) ═══
print("\n📥 Cargando Sirvoy Global...")
df = pd.read_csv(os.path.join(CARPETA, 'sirvoy_global_ene_jun_2026.csv'), encoding='utf-8')
df = df.rename(columns={
    'align-middle': 'payment_id', 'align-middle href': 'url',
    'align-middle 2': 'date', 'align-middle 3': 'method',
    'align-middle 4': 'reference', 'align-middle 5': 'linked_type',
    'align-middle 6': 'linked_id', 'text-success': 'amount_raw'
})
df['amount'] = pd.to_numeric(df['amount_raw'].astype(str).str.replace(',', '.'), errors='coerce')
df['date_parsed'] = pd.to_datetime(df['date'], format='%d/%m/%Y %H:%M', errors='coerce')
df = df.dropna(subset=['date_parsed', 'amount'])

met = df['method'].astype(str).str.lower()
tipo = 'Otros'
tipo = np.where(met.str.contains('tarjeta|card', na=False), 'Tarjeta', tipo)
# can't chain numpy where, let me do it differently

docs = []
for _, r in df.iterrows():
    m = str(r['method']).lower()
    if 'tarjeta' in m or 'card' in m: t = 'Tarjeta'
    elif 'transferencia' in m or 'transf' in m: t = 'Transferencia'
    elif 'efectivo' in m or 'cash' in m: t = 'Efectivo'
    else: t = 'Otros'
    es_link = 'link' in str(r.get('reference','')).lower()
    docs.append({
        'fuente': 'Sirvoy',
        'transaction_id': str(r['payment_id']),
        'fecha': r['date_parsed'],
        'monto': float(r['amount']),
        'metodo': str(r['method']),
        'tipo_pago': t,
        'referencia': str(r.get('reference','')),
        'es_link': es_link,
        'link_vinculado': str(r.get('linked_id','')),
        'tipo_vinculo': str(r.get('linked_type','')),
    })

total_global += insertar_documentos(docs, 'Sirvoy Global')[0]

# ═══ 2. SIRVOY RECIENTE (export payments) ═══
print("\n📥 Cargando Sirvoy Reciente...")
df2 = pd.read_csv(os.path.join(CARPETA, 'sirvoy_pagos_22may_22jun_2026.csv'), encoding='utf-8')
df2['amount'] = pd.to_numeric(df2['Amount'].astype(str).str.replace(',', '.'), errors='coerce')
df2['date_parsed'] = pd.to_datetime(df2['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
df2 = df2.dropna(subset=['date_parsed', 'amount'])

docs2 = []
for _, r in df2.iterrows():
    m = str(r['Method']).lower()
    if 'tarjeta' in m or 'card' in m: t = 'Tarjeta'
    elif 'transferencia' in m or 'transf' in m: t = 'Transferencia'
    elif 'efectivo' in m or 'cash' in m: t = 'Efectivo'
    else: t = 'Otros'
    es_link = 'link' in str(r.get('Comment','')).lower()
    docs2.append({
        'fuente': 'Sirvoy',
        'transaction_id': str(r['Payment Id']),
        'fecha': r['date_parsed'],
        'monto': float(r['amount']),
        'metodo': str(r['Method']),
        'tipo_pago': t,
        'referencia': str(r.get('Comment','')),
        'es_link': es_link,
        'link_vinculado': str(r.get('Linked To','')),
    })

total_global += insertar_documentos(docs2, 'Sirvoy Reciente')[0]

# ═══ 3. OPENPAY ═══
print("\n📥 Cargando Openpay...")
from data_processor import PaymentDataProcessor
p = PaymentDataProcessor()
try:
    op = p.load_openpay_data(os.path.join(CARPETA, 'openpay_mayo_2026.csv'))
    docs3 = []
    for _, r in op.iterrows():
        docs3.append({
            'fuente': 'Openpay',
            'transaction_id': str(r.get('transaction_id','')),
            'fecha': r['date'] if pd.notna(r['date']) else None,
            'monto': float(r['amount']) if pd.notna(r.get('amount',0)) else 0,
            'metodo': 'Tarjeta',
            'tipo_pago': 'Tarjeta',
            'comision': float(r.get('fee',0)),
            'fee_tax': float(r.get('fee_tax',0)),
            'comision_total': float(r.get('fee',0)) + float(r.get('fee_tax',0)),
            'card_last4': str(r.get('card_last4','')),
            'es_link': False,
        })
    total_global += insertar_documentos(docs3, 'Openpay')[0]
except Exception as e:
    print(f"  ⚠️  Openpay: Error — {e}")

# ═══ 4. IZIPAY SOLES ═══
print("\n📥 Cargando Izipay Soles...")
try:
    iz = p.load_izipay_data(os.path.join(CARPETA, 'izipay_soles_22may_22jun_2026.csv'))
    docs4 = []
    for _, r in iz.iterrows():
        docs4.append({
            'fuente': 'Izipay',
            'transaction_id': str(r.get('Transacción UUID','')),
            'fecha': r['Fecha del pago'] if pd.notna(r.get('Fecha del pago')) else None,
            'monto': float(r['Importe del pago']) if pd.notna(r.get('Importe del pago',0)) else 0,
            'metodo': str(r.get('Medio de pago','')),
            'tipo_pago': 'Tarjeta',
            'moneda': 'PEN',
            'comision': float(r.get('Comisión',0)),
            'tarjeta': str(r.get('Número de tarjeta','')),
            'comprador': str(r.get('Comprador','')),
            'email': str(r.get('E-mail comprador','')),
            'es_link': False,
        })
    total_global += insertar_documentos(docs4, 'Izipay Soles')[0]
except Exception as e:
    print(f"  ⚠️  Izipay Soles: Error — {e}")

# ═══ 5. IZIPAY USD ═══
print("\n📥 Cargando Izipay USD...")
try:
    izu = p.load_izipay_data(os.path.join(CARPETA, 'izipay_22may_22jun_2026.csv'))
    docs5 = []
    for _, r in izu.iterrows():
        docs5.append({
            'fuente': 'Izipay',
            'transaction_id': '',
            'fecha': r['Fecha del pago'] if pd.notna(r.get('Fecha del pago')) else None,
            'monto': float(r['Importe del pago']) if pd.notna(r.get('Importe del pago',0)) else 0,
            'metodo': str(r.get('Medio de pago','')),
            'tipo_pago': 'Tarjeta',
            'moneda': 'USD',
            'comision': float(r.get('Comisión',0)),
            'tarjeta': str(r.get('Número del medio de pago','')),
            'comprador': str(r.get('Comprador','')),
            'email': str(r.get('E-mail comprador','')),
            'es_link': False,
        })
    total_global += insertar_documentos(docs5, 'Izipay USD')[0]
except Exception as e:
    print(f"  ⚠️  Izipay USD: Error — {e}")

# ═══ 6. CULQI ═══
print("\n📥 Cargando Culqi...")
try:
    cq = p.load_culqi_data(os.path.join(CARPETA, 'culqi_ventas_22may_22jun_2026.csv'))
    docs6 = []
    for _, r in cq.iterrows():
        docs6.append({
            'fuente': 'Culqi',
            'transaction_id': str(r.get('ID Venta','')),
            'fecha': r['datetime'] if pd.notna(r.get('datetime')) else None,
            'monto': float(r['Monto VENTA']) if pd.notna(r.get('Monto VENTA',0)) else 0,
            'monto_final': float(r['Venta Final']) if pd.notna(r.get('Venta Final',0)) else 0,
            'metodo': str(r.get('Marca','')),
            'tipo_pago': 'Tarjeta',
            'moneda': str(r.get('Moneda','PEN')),
            'comision_culqi': float(r.get('Comision Culqi',0)),
            'comision_emisor': float(r.get('Comision Emisor',0)),
            'comision_total': float(r.get('Comision TOTAL',0)),
            'card_last4': str(r.get('Ult. 4 digitos','')),
            'comprador': str(r.get('customer_full_name','')),
            'email': str(r.get('Correo Electronico','')),
            'estado': str(r.get('Estado','')),
            'es_link': False,
        })
    total_global += insertar_documentos(docs6, 'Culqi')[0]
except Exception as e:
    print(f"  ⚠️  Culqi: Error — {e}")

# ═══ ESTADÍSTICAS ═══
print(f"\n{'='*55}")
print(f"📊 RESUMEN DEL SEED")
print(f"{'='*55}")
total_db = collection.count_documents({})
print(f"  Total en MongoDB: {total_db:,} documentos")
print(f"  Insertados ahora: {total_global:,}")
print()

# Estadísticas por fuente
print("  Por fuente:")
for f in collection.distinct('fuente'):
    cant = collection.count_documents({'fuente': f})
    try:
        mont = list(collection.aggregate([{'$match': {'fuente': f}}, {'$group': {'_id': None, 'sum': {'$sum': '$monto'}}}]))
        print(f"    {f:<15} {cant:>5} docs  S/ {mont[0]['sum']:>10,.2f}" if mont else f"    {f:<15} {cant:>5} docs")
    except:
        print(f"    {f:<15} {cant:>5} docs")

print()
print("  Por tipo de pago:")
for t in collection.distinct('tipo_pago'):
    cant = collection.count_documents({'tipo_pago': t})
    print(f"    {t:<15} {cant:>5} docs")

print()
print("  Links de Pago:")
links = collection.count_documents({'es_link': True})
link_monto = list(collection.aggregate([{'$match': {'es_link': True}}, {'$group': {'_id': None, 'sum': {'$sum': '$monto'}}}]))
print(f"    {links} documentos, S/ {link_monto[0]['sum']:,.2f}" if link_monto else f"    {links} documentos")

print(f"\n✅ Seed completado. MongoDB lista en localhost:27017/pena_linda")
