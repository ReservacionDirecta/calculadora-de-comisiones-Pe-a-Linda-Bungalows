#!/usr/bin/env python3
"""Identificar los 6 sobrantes en MongoDB y verificar antes de borrar."""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        if s == '' or s == 'nan':
            return 0.0
        return float(s)
    except:
        return 0.0

def parse_fecha(s):
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y %H:%M')
    except:
        return None

start = datetime(2026, 3, 3)
end = datetime(2026, 6, 29, 23, 59, 59)

# Cargar fuentes
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].apply(parse_pen)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp['PaymentId'] = exp['Payment Id'].astype(str)
exp['Method'] = exp.get('Method', '').fillna('')
exp = exp[(exp['fecha'] >= start) & (exp['fecha'] <= end)]

sc = pd.read_csv('secured (3).csv')
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = sc['align-middle 2'].apply(parse_fecha)
sc['Method'] = sc['align-middle 3'].fillna('')
sc = sc[(sc['fecha'] >= start) & (sc['fecha'] <= end)]

# Construir master fingerprints
master_fps = set()
for _, r in exp.iterrows():
    master_fps.add((round(r['monto'], 2), str(r['Method']).strip().lower()))
for _, r in sc.iterrows():
    # Para scraped-only, usar monto positivo
    monto = parse_pen(r.get('text-success', '0'))
    if monto > 0:
        master_fps.add((round(monto, 2), str(r['Method']).strip().lower()))

# Verificar sobrantes
mongo_docs = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': start, '$lte': end}
}).sort('fecha', -1))

print("=" * 80)
print(f"VERIFICACIÓN DE {len(mongo_docs)} DOCUMENTOS SIRVOY EN MONGO (03/03-29/06)")
print("=" * 80)

sobrantes = []
for d in mongo_docs:
    monto = round(d['monto'], 2)
    metodo = str(d.get('metodo', '')).strip().lower()
    fp = (monto, metodo)
    if fp not in master_fps:
        sobrantes.append(d)
    else:
        # Consumir (eliminar una ocurrencia)
        master_fps.discard(fp)

print(f"\n📋 SOBRANTES EN MONGO (no están en export ni scraped): {len(sobrantes)}")
print(f"{'ID':>8} {'Monto':>12} {'Fecha':>20} {'Método':>25} {'Tipo':>10} {'PaymentId':>10}")
print(f"{'-'*85}")
for d in sobrantes:
    pid = str(d.get('PaymentId', 'N/A'))[:10]
    tipo = d.get('tipo_pago', '')
    print(f"  S/ {d['monto']:>+9.2f}  {d['fecha'].strftime('%d/%m/%Y %H:%M'):>20}  {str(d.get('metodo',''))[:25]:>25}  {tipo[:10]:>10}  {pid:>10}")

print(f"\n   Total sobrantes: S/ {sum(d['monto'] for d in sobrantes):,.2f}")

# Verificar semanal: Sirvoy Web vs MongoDB
print(f"\n{'='*80}")
print("VERIFICACIÓN SEMANAL PRE-IMPORT")
print(f"{'='*80}")

semanas = [
    ("03/03-09/03", datetime(2026,3,3), datetime(2026,3,9,23,59,59)),
    ("10/03-16/03", datetime(2026,3,10), datetime(2026,3,16,23,59,59)),
    ("17/03-23/03", datetime(2026,3,17), datetime(2026,3,23,23,59,59)),
    ("24/03-30/03", datetime(2026,3,24), datetime(2026,3,30,23,59,59)),
    ("31/03-06/04", datetime(2026,3,31), datetime(2026,4,6,23,59,59)),
    ("07/04-13/04", datetime(2026,4,7), datetime(2026,4,13,23,59,59)),
    ("14/04-20/04", datetime(2026,4,14), datetime(2026,4,20,23,59,59)),
    ("21/04-27/04", datetime(2026,4,21), datetime(2026,4,27,23,59,59)),
    ("28/04-04/05", datetime(2026,4,28), datetime(2026,5,4,23,59,59)),
    ("05/05-11/05", datetime(2026,5,5), datetime(2026,5,11,23,59,59)),
    ("12/05-18/05", datetime(2026,5,12), datetime(2026,5,18,23,59,59)),
    ("19/05-25/05", datetime(2026,5,19), datetime(2026,5,25,23,59,59)),
    ("26/05-01/06", datetime(2026,5,26), datetime(2026,6,1,23,59,59)),
    ("02/06-08/06", datetime(2026,6,2), datetime(2026,6,8,23,59,59)),
    ("09/06-15/06", datetime(2026,6,9), datetime(2026,6,15,23,59,59)),
    ("16/06-22/06", datetime(2026,6,16), datetime(2026,6,22,23,59,59)),
    ("23/06-29/06", datetime(2026,6,23), datetime(2026,6,29,23,59,59)),
]

print(f"{'Semana':<20} {'Export':>12} {'MongoDB':>12} {'Scraped':>12} {'Objetivo Sirvoy':>16}")
print(f"{'-'*75}")

for nombre, s, e in semanas:
    # Export
    exp_s = exp[(exp['fecha'] >= s) & (exp['fecha'] <= e)]['monto'].sum()
    # MongoDB
    mongo_s = sum(d['monto'] for d in mongo_docs if s <= d['fecha'] <= e)
    # Scraped
    sc_s = sc[(sc['fecha'] >= s) & (sc['fecha'] <= e)]
    sc_monto = sum(parse_pen(str(x)) for x in sc_s['text-success'].dropna())
    
    print(f"{'✅' if abs(exp_s - mongo_s) < 1 else '⚠️'} {nombre:<18} S/ {exp_s:>+9.2f} S/ {mongo_s:>+9.2f} S/ {sc_monto:>+9.2f} S/ {'':>10}")

# Total semanal Sirvoy
print(f"\n📊 SIRVOY WEB SEMANAL (reported by user):")
print(f"   23/06-29/06: S/ 17,426.08 ✅ Export match: {abs(exp[(exp['fecha'] >= '2026-06-23') & (exp['fecha'] <= '2026-06-29 23:59:59')]['monto'].sum() - 17426.08) < 1}")
print(f"   16/06-22/06: S/ 15,753.13 ✅ Export match: {abs(exp[(exp['fecha'] >= '2026-06-16') & (exp['fecha'] <= '2026-06-22 23:59:59')]['monto'].sum() - 15753.13) < 1}")
print(f"   03/03-29/06: S/ 346,101.83")
