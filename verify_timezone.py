#!/usr/bin/env python3
"""
Verificación completa: Export Sirvoy vs Sirvoy Web vs MongoDB
con enfoque en zona horaria.
"""
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

def parse_pen(s):
    s = str(s).strip().replace('.', '').replace(',', '.')
    return float(s)

# ===== Cargar export =====
exp = pd.read_csv('payments_export-2026-06-30_09_59_04.csv')
exp['monto'] = exp['Amount'].apply(parse_pen)
exp['fecha'] = pd.to_datetime(exp['Date'], dayfirst=True, errors='coerce')
exp['PaymentId'] = exp['Payment Id'].astype(str)
exp['Method'] = exp.get('Method', '')
exp['Comment'] = exp.get('Comment', '').fillna('')

# Filtrar rango
start = datetime(2026, 3, 3)
end = datetime(2026, 6, 29, 23, 59, 59)
mask = (exp['fecha'] >= start) & (exp['fecha'] <= end)
exp_p = exp[mask].copy()

# ===== Sirvoy Web totals (del usuario) =====
sirvoy_total = 346101.83
sirvoy_23_29 = 17426.08
sirvoy_16_22 = 15753.13

print("=" * 70)
print("VERIFICACIÓN EXPORT vs SIRVOY WEB vs MONGO")
print("=" * 70)

# 1. Export totals match Sirvoy Web?
exp_total_net = exp_p['monto'].sum()
exp_23_29 = exp[(exp['fecha'] >= '2026-06-23') & (exp['fecha'] <= '2026-06-29 23:59:59')]['monto'].sum()
exp_16_22 = exp[(exp['fecha'] >= '2026-06-16') & (exp['fecha'] <= '2026-06-22 23:59:59')]['monto'].sum()

print(f"\n📊 EXPORT vs SIRVOY WEB:")
print(f"{'Período':<30} {'Export Sirvoy':>15} {'Sirvoy Web':>15} {'Match?':>10}")
print(f"{'03/03-29/06':<30} S/ {exp_total_net:>+12.2f} S/ {sirvoy_total:>+12.2f} {'✅' if abs(exp_total_net-sirvoy_total)<1 else '❌'}")
print(f"{'23/06-29/06':<30} S/ {exp_23_29:>+12.2f} S/ {sirvoy_23_29:>+12.2f} {'✅' if abs(exp_23_29-sirvoy_23_29)<1 else '❌'}")
print(f"{'16/06-22/06':<30} S/ {exp_16_22:>+12.2f} S/ {sirvoy_16_22:>+12.2f} {'✅' if abs(exp_16_22-sirvoy_16_22)<1 else '❌'}")

# 2. MongoDB vs Sirvoy Web
print(f"\n📊 MONGO vs SIRVOY WEB:")
for nombre, s, e, sirvoy_val in [
    ('03/03-29/06', start, end, sirvoy_total),
    ('23/06-29/06', datetime(2026,6,23), datetime(2026,6,29,23,59,59), sirvoy_23_29),
    ('16/06-22/06', datetime(2026,6,16), datetime(2026,6,22,23,59,59), sirvoy_16_22)
]:
    mongo_docs = list(db['pagos'].find({'fuente': 'Sirvoy', 'fecha': {'$gte': s, '$lte': e}}))
    mongo_net = sum(d['monto'] for d in mongo_docs)
    diff = mongo_net - sirvoy_val
    match = '✅' if abs(diff) < 1 else f'⚠️ S/ {diff:+,.2f}'
    print(f"{nombre:<30} S/ {mongo_net:>+12.2f} S/ {sirvoy_val:>+12.2f} {match}")

# 3. ZONA HORARIA: Verificar pagos cerca de la medianoche
print(f"\n{'='*70}")
print("VERIFICACIÓN DE ZONA HORARIA (UTC-5 Perú vs servidor Sirvoy)")
print(f"{'='*70}")
print("""
Sirvoy está en Máncora, Perú = UTC-5
El servidor de Sirvoy podría estar en UTC, UTC+1, etc.
Posible efecto: pagos de 23:00 Perú → 04:00 UTC (día siguiente)
""")

# Pagos entre 22:00 y 23:59 (Perú) podrían estar al día siguiente en servidor Sirvoy
# pagos entre 00:00 y 01:00 podrían ser del día anterior

# Ver si hay pagos "madrugada" (00:00-05:59) que podrían ser del día anterior
print("🔍 Pagos entre 00:00-05:59 (posible día anterior en Perú):")
madrugada = exp_p[exp_p['fecha'].dt.hour < 6].sort_values('fecha')
if len(madrugada) > 0:
    for _, r in madrugada.iterrows():
        print(f"   ID {r['PaymentId']:>8}  {r['fecha'].strftime('%d/%m/%Y %H:%M')}  S/ {r['monto']:>+8.2f}  {r['Method']:25s}")
else:
    print("   No hay pagos en madrugada")

# Ver pagos entre 22:00-23:59 (Perú) - podrían ser día siguiente en servidor
print("\n🔍 Pagos entre 22:00-23:59 (posible día siguiente en servidor):")
tarde = exp_p[(exp_p['fecha'].dt.hour >= 22)].sort_values('fecha')
if len(tarde) > 0:
    for _, r in tarde.iterrows():
        # Buscar si este pago o uno similar está en MongoDB con fecha diferente
        mongo_docs = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
            'metodo': r['Method']
        }).sort('fecha', -1))
        same_day = any(abs((d['fecha'] - r['fecha']).total_seconds()) < 86400 for d in mongo_docs)
        different_day = any(abs((d['fecha'] - r['fecha']).total_seconds()) >= 86400 for d in mongo_docs)
        
        flag = ""
        if same_day and not different_day:
            flag = "✅ mismo día"
        elif different_day and not same_day:
            flag = "⚠️ día DIFERENTE en MongoDB"
        elif different_day and same_day:
            flag = "❓ múltiples match"
        else:
            flag = "❌ NO ENCONTRADO"
        
        print(f"   ID {r['PaymentId']:>8}  {r['fecha'].strftime('%d/%m/%Y %H:%M')}  S/ {r['monto']:>+8.2f}  {r['Method']:25s}  {flag}")
else:
    print("   No hay pagos nocturnos")

# 4. Verificar que los pagos de 23:00 del 29/06 están en MongoDB
print(f"\n🔍 Últimos pagos del 29/06 en export y si están en MongoDB:")
ultimos = exp[(exp['fecha'] >= '2026-06-29') & (exp['fecha'] <= '2026-06-30')].sort_values('fecha', ascending=False)
for _, r in ultimos.iterrows():
    mongo_doc = db['pagos'].find_one({
        'fuente': 'Sirvoy',
        'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
        'metodo': r['Method']
    })
    status = "✅" if mongo_doc else "❌ FALTA"
    hora = r['fecha'].strftime('%d/%m %H:%M')
    print(f"   {status} ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  {hora}  {r['Method']:25s}")

# 5. Pagos del 29/jun en export vs scraped secured 1 (si existen)
print(f"\n🔍 Comparar fecha de scraped (secured 1) vs export:")
try:
    sc1 = pd.read_csv('secured (1).csv')
    sc1['monto'] = sc1['text-success'].apply(parse_pen) + sc1.get('text-error', pd.Series([0]*len(sc1))).apply(lambda x: parse_pen(x) if pd.notna(x) else 0)
    sc1['PaymentId'] = sc1['align-middle'].astype(str)
    sc1['fecha_str'] = sc1['align-middle 2']
    
    for _, r in sc1.iterrows():
        exp_match = exp_p[exp_p['PaymentId'] == r['PaymentId']]
        if len(exp_match) > 0:
            exp_fecha = exp_match.iloc[0]['fecha']
            sc_fecha = r['fecha_str']
            exp_hora = exp_fecha.strftime('%d/%m/%Y %H:%M')
            diff_horas = (exp_fecha - datetime.strptime(sc_fecha.strip(), '%d/%m/%Y %H:%M')).total_seconds() / 3600 if sc_fecha else 0
            flag = "⚠️ " if abs(diff_horas) > 0.5 else "✅ "
            print(f"   {flag} ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  Scraped:{sc_fecha:>19}  Export:{exp_hora:>16}  (Δ={diff_horas:+.1f}h)")
        else:
            print(f"   ❌ ID {r['PaymentId']:>8}  S/ {r['monto']:>+8.2f}  No está en export")
except:
    print("   secured (1).csv no accesible")

# 6. Verificar días adyacentes: pagos del export vs MongoDB con desfase horario
print(f"\n{'='*70}")
print("VERIFICACIÓN DÍAS ADYACENTES - POSIBLE DESFASE HORARIO")
print(f"{'='*70}")
print("""
Si el servidor Sirvoy usa UTC y los timestamps del export están en UTC,
entonces un pago a las 23:00 Perú = 04:00 UTC (día siguiente).
Pero si los timestamps YA están en UTC-5 (Perú), no hay desfase.
""")

# Ver si algún pago de las 23:00-23:59 del día X tiene match en MongoDB
# con fecha del día X+1 (lo que indicaría desfase UTC)
for dia in range(23, 30):
    date_str = f"2026-06-{dia:02d}"
    # Pagos nocturnos en export (22:00-23:59)
    nocturnos = exp[(exp['fecha'].dt.strftime('%Y-%m-%d') == date_str) & (exp['fecha'].dt.hour >= 22)]
    for _, r in nocturnos.iterrows():
        # Buscar en MongoDB mismo monto+metodo pero DÍA SIGUIENTE
        dia_sig = (r['fecha'] + timedelta(days=1)).strftime('%Y-%m-%d')
        mongo_match = list(db['pagos'].find({
            'fuente': 'Sirvoy',
            'monto': {'$gte': r['monto']-0.1, '$lte': r['monto']+0.1},
            'metodo': r['Method'],
            'fecha': {'$regex': f'^{dia_sig}'}
        }))
        if mongo_match:
            print(f"⚠️  ID {r['PaymentId']:>8}  Export:{r['fecha'].strftime('%d/%m %H:%M')}  MongoDB:{mongo_match[0]['fecha'].strftime('%d/%m %H:%M')}  S/ {r['monto']:>+8.2f}")
