#!/usr/bin/env python3
"""Comparar Export vs Scraped vs MongoDB 03/03-29/06."""
import pandas as pd
from datetime import datetime
from pymongo import MongoClient

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    s = str(s).strip().replace('.', '').replace(',', '.')
    return float(s)

def parse_fecha(s):
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y %H:%M')
    except:
        return None

# ===== EXPORT =====
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].apply(parse_pen)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp['PaymentId'] = exp['Payment Id'].astype(str)
exp['Method'] = exp.get('Method', '')

mask = (exp['fecha'] >= '2026-03-03') & (exp['fecha'] <= '2026-06-29 23:59:59')
exp_f = exp[mask].copy()
exp_net = exp_f['monto'].sum()

# ===== SCRAPED (secured 3) =====
sc = pd.read_csv('secured (3).csv')
sc['monto'] = sc['text-success'].apply(parse_pen)
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = sc['align-middle 2'].apply(parse_fecha)
sc['Method'] = sc['align-middle 3']

mask_sc = (sc['fecha'] >= datetime(2026,3,3)) & (sc['fecha'] <= datetime(2026,6,29,23,59,59))
sc_f = sc[mask_sc].copy()
sc_net = sc_f['monto'].sum()

# ===== MONGO =====
mongo_all = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': datetime(2026,3,3), '$lte': datetime(2026,6,29,23,59,59)}
}))
mongo_net = sum(d['monto'] for d in mongo_all)
mongo_pos = sum(d['monto'] for d in mongo_all if d['monto'] > 0)

print(f"{'='*65}")
print(f"{'COMPARACIÓN 03/03 - 29/06/2026':^65}")
print(f"{'='*65}")
print(f"{'Fuente':<18} {'Pagos':>8} {'Bruto Neto':>16} {'Com.5%':>14}")
print(f"{'-'*56}")
print(f"{'Export Sirvoy':<18} {len(exp_f):>8} S/ {exp_net:>+12.2f}  S/ {exp_net*0.05:>+10.2f}")
print(f"{'Scraped (secured 3)':<18} {len(sc_f):>8} S/ {sc_net:>+12.2f}  S/ {sc_net*0.05:>+10.2f}")
print(f"{'MongoDB (Sirvoy)':<18} {len(mongo_all):>8} S/ {mongo_net:>+12.2f}  S/ {mongo_net*0.05:>+10.2f}")
print(f"{'-'*56}")

# Comparaciones
print(f"{'Scraped vs Export':<25} {'':>1} S/ {sc_net - exp_net:>+12.2f}")
print(f"{'Mongo vs Export':<25} {'':>1} S/ {mongo_net - exp_net:>+12.2f}")
print(f"{'Mongo vs Scraped':<25} {'':>1} S/ {mongo_net - sc_net:>+12.2f}")

# ===== IDs faltantes =====
sc_ids = set(sc_f['PaymentId'])
exp_ids = set(exp_f['PaymentId'])
missing_in_mongo_by_id = exp_ids - sc_ids  # IDs en export pero no en scraped (negativos principalmente)
print(f"\n📋 IDs del export que NO están en scraped: {len(missing_in_mongo_by_id)}")
if missing_in_mongo_by_id:
    missing_df = exp_f[exp_f['PaymentId'].isin(missing_in_mongo_by_id)]
    # Agrupar por signo
    pos_missing = missing_df[missing_df['monto'] > 0]['monto'].sum()
    neg_missing = missing_df[missing_df['monto'] < 0]['monto'].sum()
    print(f"   Positivos: S/ {pos_missing:,.2f}")
    print(f"   Negativos: S/ {neg_missing:,.2f}")
    print(f"   Neto:      S/ {pos_missing+neg_missing:,.2f}")

# IDs comunes vs MongoDB
print(f"\n🔍 VERIFICACIÓN: IDs del scraped vs MongoDB:")
comunes = sc_ids & exp_ids
print(f"   IDs comunes scraped+export: {len(comunes)}")
print(f"   IDs solo scraped: {len(sc_ids - exp_ids)}")
print(f"   IDs solo export: {len(exp_ids - sc_ids)}")

# ===== Negativos en export vs MongoDB =====
negativos_exp = exp_f[exp_f['monto'] < 0]
print(f"\n📊 Negativos en export (03/03-29/06): {len(negativos_exp)}")
print(f"   Total negativo: S/ {negativos_exp['monto'].sum():,.2f}")
for _, r in negativos_exp.iterrows():
    mongo_match = db['pagos'].find_one({
        'fuente': 'Sirvoy',
        'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
        'metodo': r['Method']
    })
    status = "✅" if mongo_match else "❌"
    print(f"   {status} ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {r['fecha'].strftime('%d/%m/%y')}  {r['Method']:25s}")

print(f"\n{'='*65}")
diff = mongo_net - sc_net
print(f"RESUMEN: MongoDB - Scraped = S/ {diff:+,.2f}")
if diff != 0:
    print(f"Los negativos del export suman S/ {negativos_exp['monto'].sum():,.2f}")
    print(f"(Los negativos ya están en MongoDB, el scraped no los tiene)")
