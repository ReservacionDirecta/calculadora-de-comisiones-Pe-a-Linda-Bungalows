#!/usr/bin/env python3
"""Diagnóstico completo: comisiones, negativos y saldos."""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

print("=" * 70)
print("DIAGNÓSTICO SIRVOY — Comisiones, negativos, saldos")
print("=" * 70)

# Consultar Sirvoy docs en rango 03/03-29/06
start = datetime(2026, 3, 3, 0, 0, 0)
end = datetime(2026, 6, 29, 23, 59, 59)
sv = list(db['pagos'].find({'fuente': 'Sirvoy', 'fecha': {'$gte': start, '$lte': end}}))
print(f"\nDocs Sirvoy en 03/03-29/06: {len(sv)}")

if sv:
    positivos = [d['monto'] for d in sv if d['monto'] > 0]
    negativos = [d['monto'] for d in sv if d['monto'] < 0]
    sum_pos = sum(positivos)
    sum_neg = sum(negativos)
    sum_net = sum_pos + sum_neg
    print(f"  Positivos: {len(positivos)} docs = S/ {sum_pos:,.2f}")
    print(f"  Negativos: {len(negativos)} docs = S/ {sum_neg:,.2f}")
    print(f"  Neto:                    S/ {sum_net:,.2f}")
    print(f"  Sirvoy Web (objetivo):   S/ 346,101.83")
    match = "✅ COINCIDE" if abs(sum_net - 346101.83) < 1 else f"❌ DIFIERE por {sum_net - 346101.83:.2f}"
    print(f"  {match}")

# Analizar negativos individualmente
if negativos:
    neg_sorted = sorted(negativos)
    print(f"\n--- Análisis de negativos ---")
    print(f"  Cantidad: {len(negativos)}")
    print(f"  Mínimo: S/ {neg_sorted[0]:,.2f}")
    print(f"  Máximo: S/ {neg_sorted[-1]:,.2f}")
    print(f"  Total: S/ {sum_neg:,.2f}")
    print(f"  % del Bruto: {abs(sum_neg)/sum_pos*100:.1f}%")
    
    # Mostrar top 10 negativos
    print(f"\n  Top 10 negativos (mayor monto):")
    for d in sorted(sv, key=lambda x: x['monto'])[:10]:
        print(f"    S/ {d['monto']:>+10.2f} | {d.get('fecha',''):19} | {d.get('metodo',''):20} | ref={d.get('referencia','')}")
    
    # Clasificar negativos
    print(f"\n  --- Clasificación sugerida de negativos ---")
    print(f"  Si son reembolsos/contracargos o correcciones:")
    print(f"  Comisión sobre BRUTO = S/ {sum_pos * 0.05:,.2f}")
    print(f"  Comisión sobre NETO  = S/ {sum_net * 0.05:,.2f}")
    print(f"  Diferencia:          = S/ {(sum_pos - sum_net) * 0.05:,.2f}")
    
print(f"\n{'=' * 70}")
print("SALDO BASE (heredado QuickBooks)")
print("=" * 70)
sm = list(db['pagos'].find({'fuente': 'Saldo Base'}))
if sm:
    for d in sm:
        print(f"  S/ {d['monto']:,.2f} - {d.get('fecha','')} - {d.get('concepto','')}")
else:
    print("  No encontrado en pagos con fuente='Saldo Base'")
    
# QuickBooks vs Live
print(f"\n{'=' * 70}")
print("COMPARACIÓN: QuickBooks (cobros) vs Live (pagos)")
print("=" * 70)
cobros = list(db['cobros'].find({}))
if cobros:
    cf = pd.DataFrame(cobros)
    cf['fecha_dt'] = pd.to_datetime(cf['fecha'], errors='coerce')
    cf_desde_mar = cf[cf['fecha_dt'] >= '2026-03-03']
    
    print(f"\n  Cobros desde 03/03:")
    for tp, grp in cf_desde_mar.groupby('tipo'):
        print(f"    {tp:15}: {len(grp):3} docs = S/ {grp['monto'].sum():>10,.2f}")
    
    # Abonos totales
    abonos_qb = cf_desde_mar[cf_desde_mar['tipo'] == 'abono']['monto'].sum()
    comisiones_qb = cf_desde_mar[cf_desde_mar['tipo'] == 'comision']['monto'].sum()
    costos_qb = cf_desde_mar[cf_desde_mar['tipo'].isin(['costo', 'saldo_inicial'])]['monto'].sum()
    
    print(f"\n  --- QuickBooks Balance ---")
    print(f"  Adeudado = Comisiones S/ {comisiones_qb:,.2f} + Costos S/ {costos_qb:,.2f}")
    print(f"           = S/ {comisiones_qb + costos_qb:,.2f}")
    print(f"  - Abonos = S/ {abonos_qb:,.2f}")
    print(f"  = Saldo  = S/ {comisiones_qb + costos_qb - abonos_qb:,.2f}")

    # Live Balance
    # Costos desde pagos
    costos_pagos = list(db['pagos'].find({
        'fuente': {'$in': ['Costo FB Ads', 'Costo Sirvoy', 'Costo Asistente', 'Costo Extra']},
        'fecha': {'$gte': start, '$lte': end}
    }))
    total_costos_live = sum(d['monto'] for d in costos_pagos)
    
    print(f"\n  --- Live Balance (desde pagos) ---")
    print(f"  Comisión (sobre bruto) = S/ {sum_pos * 0.05:,.2f}")
    print(f"  Costos operativos      = S/ {total_costos_live:,.2f}")
    print(f"  Adeudado               = S/ {sum_pos * 0.05 + total_costos_live:,.2f}")
    print(f"  - Abonos QuickBooks    = S/ {abonos_qb:,.2f}")
    print(f"  = Saldo                = S/ {sum_pos * 0.05 + total_costos_live - abonos_qb:,.2f}")
    print(f"  + Saldo Base (03/03)   = S/ 9,654.83")
    print(f"  = Saldo + Base         = S/ {sum_pos * 0.05 + total_costos_live - abonos_qb + 9654.83:,.2f}")
else:
    print("  No hay datos en cobros!")
