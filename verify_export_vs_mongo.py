#!/usr/bin/env python3
"""Verificación detallada: export vs MongoDB, con foco en la diferencia semanal."""
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

# Cargar export
df = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
df['monto'] = df['Amount'].apply(parse_pen)
df['fecha'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
df['PaymentId'] = df['Payment Id'].astype(str)

# Filtrar rango 03/03 - 29/06
start = datetime(2026, 3, 3)
end = datetime(2026, 6, 30)
df_period = df[(df['fecha'] >= start) & (df['fecha'] <= end)]

print("=" * 80)
print("VERIFICACIÓN EXPORT vs MONGO: PERÍODO COMPLETO (03/03 - 29/06)")
print("=" * 80)

# ========= 1. Totales generales =========
# Export
exp_pos = df_period[df_period['monto'] > 0]['monto'].sum()
exp_neg = df_period[df_period['monto'] < 0]['monto'].sum()
exp_net = exp_pos + exp_neg

# MongoDB (Sirvoy, 03/03-29/06)
mongo_all = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': start, '$lte': end}
}))
mongo_pos = sum(d['monto'] for d in mongo_all if d['monto'] > 0)
mongo_neg = sum(d['monto'] for d in mongo_all if d['monto'] < 0)
mongo_net = mongo_pos + mongo_neg

print(f"\n📊 TOTALES (03/03 - 29/06):")
print(f"{'':30} {'Export':>15} {'MongoDB':>15} {'Diferencia':>15}")
print(f"{'Positivos':30} S/ {exp_pos:>+12.2f} S/ {mongo_pos:>+12.2f} S/ {exp_pos-mongo_pos:>+12.2f}")
print(f"{'Negativos':30} S/ {exp_neg:>+12.2f} S/ {mongo_neg:>+12.2f} S/ {exp_neg-mongo_neg:>+12.2f}")
print(f"{'NETO (Bruto)':30} S/ {exp_net:>+12.2f} S/ {mongo_net:>+12.2f} S/ {exp_net-mongo_net:>+12.2f}")
print(f"{'Comisión 5%':30} S/ {exp_net*0.05:>+12.2f} S/ {mongo_net*0.05:>+12.2f} S/ {(exp_net-mongo_net)*0.05:>+12.2f}")

# ========= 2. Por semana =========
print(f"\n📅 COMPARACIÓN SEMANAL (Export vs MongoDB):")
print(f"{'Semana':<20} {'Export Neto':>15} {'Mongo Neto':>15} {'Diff':>15} {'#Faltan':>8}")
print(f"{'-'*75}")

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

total_exp = 0
total_mongo = 0
total_faltan = 0

for nombre, s, e in semanas:
    # Export
    mask = (df['fecha'] >= s) & (df['fecha'] <= e)
    exp_semana = df[mask]['monto'].sum()
    
    # MongoDB
    mongo_semana = list(db['pagos'].find({
        'fuente': 'Sirvoy',
        'fecha': {'$gte': s, '$lte': e}
    }))
    mongo_sum = sum(d['monto'] for d in mongo_semana)
    
    # Faltantes: export IDs no en MongoDB
    exp_ids = set(df[mask]['PaymentId'])
    mongo_fingerprints = set()
    for d in mongo_semana:
        mongo_fingerprints.add((round(d['monto'], 2), str(d.get('metodo', '')).strip().lower()))
    
    faltan = 0
    falta_monto = 0.0
    for _, r in df[mask].iterrows():
        fp = (round(r['monto'], 2), str(r.get('Method', '')).strip().lower())
        if fp not in mongo_fingerprints:
            faltan += 1
            falta_monto += r['monto']
    
    diff = exp_semana - mongo_sum
    total_exp += exp_semana
    total_mongo += mongo_sum
    total_faltan += faltan
    
    status = "⚠️" if abs(diff) > 50 else "✅"
    print(f"{status} {nombre:<18} S/ {exp_semana:>+10.2f}  S/ {mongo_sum:>+10.2f}  S/ {diff:>+10.2f}  {faltan:>3} (S/ {falta_monto:>+8.2f})")

print(f"{'-'*75}")
print(f"{'TOTAL':<20} S/ {total_exp:>+10.2f}  S/ {total_mongo:>+10.2f}  S/ {total_exp-mongo_sum:>+10.2f}  {total_faltan:>3}")

# ========= 3. Últimos 3 días: revisar zona horaria =========
print(f"\n{'='*80}")
print("VERIFICACIÓN ZONA HORARIA: Últimos 3 días del export (27-29 Jun)")
print(f"{'='*80}")

df_ultimos = df[(df['fecha'] >= '2026-06-27') & (df['fecha'] <= '2026-06-30')].copy()

# En el export, 29/Jun a las 23:00 podría ser 30/Jun 04:00 UTC 
# pero Sirvoy usa UTC-5, entonces 23:00 Peru = correcto
# El scraped tiene datos con hora 28/06 09:51 etc. que podrían tener
# diferencia de horas vs export

# Ver pagos del 29/Jun después de 23:00 (podrían estar en el 30 en otro sistema)
df_despues_23 = df[(df['fecha'] >= '2026-06-29') & (df['fecha'] <= '2026-06-30')]
print(f"\n📋 Pagos del 29/Jun en el export:")
for _, r in df_despues_23.iterrows():
    mongo_match = list(db['pagos'].find({
        'fuente': 'Sirvoy',
        'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
        'metodo': r.get('Method','')
    }))
    status = "✅" if mongo_match else "❌"
    comment = str(r.get('Comment', ''))[:30]
    print(f"  {status} ID {r['PaymentId']:>8}  S/ {r['monto']:>+10.2f}  {r['fecha'].strftime('%d/%m %H:%M')}  {r.get('Method',''):25s}  '{comment}'")

# ========= 4. Reversiones del export vs scraped =========
print(f"\n{'='*80}")
print("REVISIONES EN EXPORT (negativos) vs SCRAPED")
print(f"{'='*80}")

negativos = df[df['monto'] < 0].copy()
print(f"\nTotal negativos en export: {len(negativos)}")

for _, r in negativos.iterrows():
    # Buscar en scraped por ID
    mongo_doc = db['pagos'].find_one({
        'fuente': 'Sirvoy',
        'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
        'metodo': r.get('Method','')
    })
    status = "✅ Mongo" if mongo_doc else "❌ Mongo"
    print(f"  ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {r['fecha'].strftime('%d/%m %H:%M')}  {r.get('Method',''):25s}  {status}")
