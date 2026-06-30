#!/usr/bin/env python3
"""
Compara secured (1).csv (scraped) vs payments_export-2026-06-30_09_59_04.csv (exportado)
y cruza contra MongoDB para detectar diferencias.
"""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import hashlib

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

# ============ 1. SCRAPED ============
df1 = pd.read_csv('secured (1).csv')
df1['monto_pos'] = df1['text-success'].apply(parse_pen)
df1['monto_neg'] = df1['text-error'].apply(parse_pen)
df1['monto'] = df1['monto_pos'] + df1['monto_neg']
df1['PaymentId'] = df1['align-middle'].astype(str)
df1['Method'] = df1['align-middle 3']
df1['Date'] = df1['align-middle 2']
df1['Comment'] = df1['align-middle 4']

# ============ 2. EXPORTADO ============
df2 = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
df2['monto'] = df2['Amount'].apply(parse_pen)
df2['fecha'] = pd.to_datetime(df2['Date'], dayfirst=True, errors='coerce')
df2['PaymentId'] = df2['Payment Id'].astype(str)
df2['Method'] = df2.get('Method', '')

print("=" * 80)
print("COMPARACIÓN: SCRAPED (secured (1).csv) vs EXPORTADO (09_59_04)")
print("=" * 80)

# ============ 3. Comparación PaymentId a PaymentId ============
scraped_ids = set(df1['PaymentId'])
export_ids = set(df2['PaymentId'])
common_ids = scraped_ids & export_ids
only_scraped = scraped_ids - export_ids
only_export = export_ids - scraped_ids

print(f"\n📊 Conteo:")
print(f"   Scraped:     {len(df1)} payments")
print(f"   Exportado:   {len(df2)} payments")
print(f"   IDs comunes: {len(common_ids)}")
print(f"   Solo scraped: {len(only_scraped)}")
print(f"   Solo export:  {len(only_export)}")

# ============ 4. Pagos en común: diferencia de montos ============
if common_ids:
    print(f"\n🔍 Diferencias de monto en IDs comunes:")
    diffs = []
    for pid in common_ids:
        r1 = df1[df1['PaymentId'] == pid].iloc[0]
        r2 = df2[df2['PaymentId'] == pid].iloc[0]
        m1 = r1['monto']
        m2 = r2['monto']
        if abs(m1 - m2) > 0.01:
            diffs.append(f"   ID {pid:>8}: Scraped={m1:>+8.2f} ≠ Export={m2:>+8.2f} (Δ={m2-m1:>+8.2f})")
    if diffs:
        for d in diffs:
            print(d)
    else:
        print("   ✅ Todos los montos coinciden")

# ============ 5. Solo en export (no están en scraped) ============
if only_export:
    print(f"\n📋 Pagos en EXPORTADO que NO están en scraped ({len(only_export)}):")
    solo_export = df2[df2['PaymentId'].isin(only_export)]
    for _, r in solo_export.iterrows():
        # Buscar en MongoDB
        docs = list(db['pagos'].find({'fuente': 'Sirvoy', 'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1}, 'metodo': r['Method']}))
        in_mongo = "✅" if docs else "❌"
        print(f"   {in_mongo} ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {r['Method']:25s}  {r['fecha'].strftime('%d/%m %H:%M')}")

# ============ 6. Solo en scraped ============
if only_scraped:
    print(f"\n📋 Pagos en SCRAPED que NO están en export ({len(only_scraped)}):")
    solo_scraped = df1[df1['PaymentId'].isin(only_scraped)]
    for _, r in solo_scraped.iterrows():
        in_mongo = "✅" if db['pagos'].find_one({'fuente': 'Sirvoy', 'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1}, 'metodo': r['Method']}) else "❌"
        print(f"   {in_mongo} ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {r['Method']:25s}")

# ============ 7. Totales por período ============
print(f"\n{'='*80}")
print("COMPARACIÓN DE TOTALES POR PERÍODO SEMANAL")
print(f"{'='*80}")

# Exportado tiene fechas completas; scraped no
# Ver si el problema es que el scraped NO incluye todas las transacciones
# porque la página de Sirvoy paginó/mostró solo las últimas 20

print("\n📅 Últimos 7 días (23/06 - 29/06) — Exportado:")
ultima_semana_exp = df2[(df2['fecha'] >= '2026-06-23') & (df2['fecha'] <= '2026-06-29')]
pos = ultima_semana_exp[ultima_semana_exp['monto'] > 0]['monto'].sum()
neg = ultima_semana_exp[ultima_semana_exp['monto'] < 0]['monto'].sum()
print(f"   Positivos: S/ {pos:,.2f}")
print(f"   Negativos: S/ {neg:,.2f}")
print(f"   Neto:      S/ {pos+neg:,.2f}")

print("\n📅 Últimos 7 días (23/06 - 29/06) — MongoDB Sirvoy:")
mongo_semana = list(db['pagos'].find({'fuente': 'Sirvoy', 'fecha': {'$gte': datetime(2026,6,23), '$lte': datetime(2026,6,29,23,59,59)}}))
pos_m = sum(d['monto'] for d in mongo_semana if d['monto'] > 0)
neg_m = sum(d['monto'] for d in mongo_semana if d['monto'] < 0)
print(f"   Positivos: S/ {pos_m:,.2f}")
print(f"   Negativos: S/ {neg_m:,.2f}")
print(f"   Neto:      S/ {pos_m+neg_m:,.2f}")

# ============ 8. Diferencia por rango de fechas (export vs mongo) ============
print(f"\n{'='*80}")
print("DIFERENCIAS SISTEMÁTICAS POR RANGO DE FECHA")
print(f"{'='*80}")

# Agrupar export por día
df2['dia'] = df2['fecha'].dt.date
print(f"\n📊 Exportado vs MongoDB por día (23-29 Jun):")
print(f"{'Día':<15} {'Export Bruto':>15} {'Mongo Bruto':>15} {'Diferencia':>15}")
for dia, grp in df2[df2['fecha'] >= '2026-06-23'].groupby('dia'):
    exp_net = grp['monto'].sum()
    mongo_net = sum(d['monto'] for d in db['pagos'].find({'fuente': 'Sirvoy', 'fecha': {'$gte': datetime.combine(dia, datetime.min.time()), '$lte': datetime.combine(dia, datetime.max.time())}}))
    diff = exp_net - mongo_net
    print(f" {dia}    S/ {exp_net:>+10.2f}  S/ {mongo_net:>+10.2f}  S/ {diff:>+10.2f}")

# ============ 9. Verificar zona horaria ============
print(f"\n{'='*80}")
print("VERIFICACIÓN DE ZONA HORARIA")
print(f"{'='*80}")

# Sirvoy timestamps están en Perú UTC-5 sin tzinfo
# El scraped probablemente también
# El exportado tiene fechas con hora — ver si las fechas del exportado son las mismas que el scraped
print("\n🔍 Comparación de fechas (IDs comunes):")
for pid in sorted(common_ids, key=lambda x: int(x))[:5]:
    r1 = df1[df1['PaymentId'] == pid].iloc[0]
    r2 = df2[df2['PaymentId'] == pid].iloc[0]
    print(f"   ID {pid}: Scraped date='{r1['Date']}' | Export date='{r2['Date']}'")

print("\n🔍 IDs del export que están FUERA del rango del scraped (fecha):")
# El scraped probablemente solo tiene las últimas ~20 transacciones visibles
# El export tiene todas las del período
for _, r in solo_export.iterrows():
    comment = str(r.get('Comment', ''))[:30]
    print(f"   ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {r['fecha'].strftime('%d/%m/%Y %H:%M')}  {r['Method']:25s}  '{comment}'")
