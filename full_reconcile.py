#!/usr/bin/env python3
"""
Reconciliación final: Scraped (secured 3) + Export (09_59_04) vs MongoDB.
Sirvoy Web: 1,152 pagos, S/ 346,101.83 (03/03-29/06).

Estrategia:
- Para IDs en ambos (scraped+export): usar el monto del EXPORT (tiene signo correcto)
- Para IDs solo scraped (152): usar monto positivo del scraped
- Para IDs solo export (80): usar monto del export (incluye 33 negativos)
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import numpy as np

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        if s == '' or s == 'nan' or s == '-nan':
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

# ===== Cargar export =====
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].apply(parse_pen)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp['PaymentId'] = exp['Payment Id'].astype(str)
exp['Method'] = exp.get('Method', '').fillna('')
exp['Comment'] = exp.get('Comment', '').fillna('')
exp = exp[(exp['fecha'] >= start) & (exp['fecha'] <= end)]
exp_dict = {r['PaymentId']: r for _, r in exp.iterrows()}

# ===== Cargar scraped (secured 3) =====
sc = pd.read_csv('secured (3).csv')
sc['monto_scraped'] = sc['text-success'].apply(parse_pen)
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = sc['align-middle 2'].apply(parse_fecha)
sc['Method'] = sc['align-middle 3'].fillna('')
sc['Comment'] = sc['align-middle 4'].fillna('')
sc = sc[(sc['fecha'] >= start) & (sc['fecha'] <= end)]

print("=" * 75)
print("RECONCILIACIÓN FINAL: SIRVOY vs MONGO (03/03-29/06)")
print("=" * 75)

# ===== Construir maestro =====
sc_ids = set(sc['PaymentId'])
exp_ids = set(exp['PaymentId'])
common_ids = sc_ids & exp_ids

print(f"\n📊 Cobertura: {len(sc_ids | exp_ids)} IDs únicos (Sirvoy Web: 1,152)")
print(f"   Comunes: {len(common_ids)} | Solo scraped: {len(sc_ids - exp_ids)} | Solo export: {len(exp_ids - sc_ids)}")

# Maestro: para cada ID único, tomar el mejor monto disponible
master = []
for _, r in sc.iterrows():
    pid = r['PaymentId']
    if pid in exp_dict:
        # Usar monto del export (tiene signo para negativos)
        monto = exp_dict[pid]['monto']
        method = exp_dict[pid]['Method']
        comment = exp_dict[pid]['Comment']
        source = 'both'
    else:
        # Solo scraped: usar monto positivo del scraped
        monto = r['monto_scraped']
        method = r['Method']
        comment = r['Comment']
        source = 'scraped_only'
    master.append({'PaymentId': pid, 'monto': monto, 'fecha': r['fecha'], 'Method': method, 'Comment': comment, 'source': source})

# Agregar IDs solo export
for pid in exp_ids - sc_ids:
    r = exp_dict[pid]
    master.append({'PaymentId': pid, 'monto': r['monto'], 'fecha': r['fecha'], 'Method': r['Method'], 'Comment': r['Comment'], 'source': 'export_only'})

master_df = pd.DataFrame(master)
master_total = master_df['monto'].sum()

print(f"\n📊 Maestro combinado:")
print(f"   Pagos: {len(master_df)}")
print(f"   Fuentes: {master_df['source'].value_counts().to_dict()}")
neto = master_df['monto'].sum()
pos = master_df[master_df['monto'] > 0]['monto'].sum()
neg = master_df[master_df['monto'] < 0]['monto'].sum()
print(f"   Bruto: S/ {neto:,.2f} (Sirvoy Web: S/ 346,101.83)")
print(f"   Positivos: S/ {pos:,.2f} | Negativos: S/ {neg:,.2f}")
match = "✅" if abs(neto - 346101.83) < 5 else f"❌ Diff S/ {neto - 346101.83:+.2f}"
print(f"   Match: {match}")

# ===== Cruzar contra MongoDB =====
mongo_all = list(db['pagos'].find({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': start, '$lte': end}
}))
mongo_fp = {}
for d in mongo_all:
    fp = (round(d['monto'], 2), str(d.get('metodo', '')).strip().lower())
    if fp not in mongo_fp:
        mongo_fp[fp] = []
    mongo_fp[fp].append(d)

matched = 0
missing = []

for _, r in master_df.iterrows():
    # Probar match exacto por (monto, método)
    fp = (round(r['monto'], 2), str(r['Method']).strip().lower())
    if fp in mongo_fp:
        matched += 1
        # Consumir
        mongo_fp[fp] = mongo_fp[fp][1:] if len(mongo_fp[fp]) > 1 else []
        if not mongo_fp[fp]:
            del mongo_fp[fp]
    else:
        missing.append(r.copy() if hasattr(r, 'copy') else r)

# Sobrantes
remaining_mongo = sum(len(v) for v in mongo_fp.values())

print(f"\n🔍 RESULTADOS:")
print(f"   ✅ Coinciden con MongoDB: {matched}")
print(f"   ❌ Faltantes en MongoDB:  {len(missing)}")
print(f"   ⚠️ Sobrantes en MongoDB:   {remaining_mongo}")

# ===== Pagos faltantes =====
if missing:
    # Separar por tipo
    missing_pos = [m for m in missing if m['monto'] > 0]
    missing_neg = [m for m in missing if m['monto'] < 0]
    
    print(f"\n📋 FALTANTES POSITIVOS ({len(missing_pos)}):")
    total_pos = 0
    for m in sorted(missing_pos, key=lambda x: x['fecha'], reverse=True):
        total_pos += m['monto']
        print(f"   ID {m['PaymentId']:>8}  S/ {m['monto']:>+8.2f}  {m['fecha'].strftime('%d/%m/%y %H:%M')}  {m['Method']:30s}  '{str(m.get('Comment',''))[:20]}'")
    print(f"   Total: S/ {total_pos:,.2f}")

    print(f"\n📋 FALTANTES NEGATIVOS ({len(missing_neg)}):")
    total_neg = 0
    for m in sorted(missing_neg, key=lambda x: x['fecha'], reverse=True):
        total_neg += m['monto']
        print(f"   ID {m['PaymentId']:>8}  S/ {m['monto']:>+8.2f}  {m['fecha'].strftime('%d/%m/%y %H:%M')}  {m['Method']:30s}")
    print(f"   Total: S/ {total_neg:,.2f}")
    
    print(f"\n   Total faltantes: S/ {total_pos + total_neg:,.2f}")

# Extra: verificar los IDs con error de signo
mongo_net = sum(d['monto'] for d in mongo_all)
resultado_esperado = mongo_net + sum(m['monto'] for m in missing) - remaining_mongo  # ignoring sobrantes
print(f"\n🏁 Proyección:")
print(f"   MongoDB actual:    S/ {mongo_net:>+10.2f}")
print(f"   + faltantes:       S/ {sum(m['monto'] for m in missing):>+10.2f}")
print(f"   - sobrantes:       S/ {-sum(d['monto'] for docs in mongo_fp.values() for d in docs):>+10.2f}" if remaining_mongo > 0 else "")
print(f"   ─────────────────")
print(f"   Resultado:         S/ {mongo_net + sum(m['monto'] for m in missing):>+10.2f}" + 
      (f" - S/ {sum(d['monto'] for docs in mongo_fp.values() for d in docs):,.2f}" if remaining_mongo > 0 else ""))
print(f"   Objetivo (Sirvoy): S/ {346101.83:>+10.2f}")
print(f"   Diferencia final:  S/ {mongo_net + sum(m['monto'] for m in missing) - 346101.83:>+10.2f}")
