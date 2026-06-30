#!/usr/bin/env python3
"""Verificar saldo deudor real: comision + costos - abonos."""
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

c = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
db = c['pena_linda']

# 1. COMISION desde 03/03 (calculada desde Sirvoy)
start = datetime(2026, 3, 3)
end = datetime(2026, 6, 29, 23, 59, 59)
sv = list(db['pagos'].find({'fuente': 'Sirvoy', 'fecha': {'$gte': start, '$lte': end}}))
sv_pos = sum(d['monto'] for d in sv if d['monto'] > 0)
sv_neg = sum(d['monto'] for d in sv if d['monto'] < 0)
sv_net = sv_pos + sv_neg
comision_5 = sv_pos * 0.05

print("=" * 65)
print("1️⃣  COMISIÓN ACUMULADA (desde 03/03)")
print("=" * 65)
print(f"  Bruto Sirvoy (solo positivos): S/ {sv_pos:>12,.2f}")
print(f"  Comisión 5%:                    S/ {comision_5:>12,.2f}")
print(f"  Negativos (reversiones):        S/ {sv_neg:>12,.2f}")
print(f"  Neto Sirvoy:                    S/ {sv_net:>12,.2f}")

# 2. COSTOS OPERATIVOS desde 03/03
costos = list(db['pagos'].find({
    'tipo_pago': 'Costo',
    'fecha': {'$gte': start, '$lte': end}
}))
print(f"\n{'=' * 65}")
print("2️⃣  COSTOS OPERATIVOS (desde 03/03)")
print("=" * 65)
costo_fb = sum(d['monto'] for d in costos if d.get('fuente') == 'Costo FB Ads')
costo_sv = sum(d['monto'] for d in costos if d.get('fuente') == 'Costo Sirvoy')
costo_as = sum(d['monto'] for d in costos if d.get('fuente') == 'Costo Asistente')
costo_saldo = sum(d['monto'] for d in costos if d.get('fuente') == 'Saldo Base')

# Also costo_extra
costo_extra = sum(d['monto'] for d in costos if d.get('fuente') == 'Costo Extra')

total_costos_sin_saldo = costo_fb + costo_sv + costo_as + costo_extra
total_costos = total_costos_sin_saldo + costo_saldo

print(f"  Facebook Ads:     S/ {costo_fb:>10,.2f}")
print(f"  Sirvoy (software): S/ {costo_sv:>10,.2f}")
print(f"  Asistente:        S/ {costo_as:>10,.2f}")
print(f"  Costo Extra:      S/ {costo_extra:>10,.2f}")
print(f"  ─────────────────────────────────────")
print(f"  Subtotal (sin saldo): S/ {total_costos_sin_saldo:>10,.2f}")
print(f"  Saldo Base:       S/ {costo_saldo:>10,.2f}")
print(f"  ─────────────────────────────────────")
print(f"  TOTAL COSTOS:     S/ {total_costos:>10,.2f}")

# 3. ABONOS (cobros) desde 03/03
cobros_docs = list(db['cobros'].find({}))
print(f"\n{'=' * 65}")
print("3️⃣  ABONOS RECIBIDOS (desde 03/03)")
print("=" * 65)

if cobros_docs:
    cf = pd.DataFrame(cobros_docs)
    cf['fecha_dt'] = pd.to_datetime(cf['fecha'], errors='coerce')
    cf = cf.sort_values('fecha_dt').reset_index(drop=True)

    mask = (cf['fecha_dt'].dt.date >= pd.Timestamp('2026-03-03').date()) & \
           (cf['fecha_dt'].dt.date <= pd.Timestamp('2026-06-29').date())
    cf_f = cf[mask].copy()

    print("\nTipos de cobros:")
    for tp, grp in cf_f.groupby('tipo'):
        print(f"  {tp}: {len(grp)} docs = S/ {grp['monto'].sum():>10,.2f}")

    total_abonos = float(cf_f[cf_f['tipo'] == 'abono']['monto'].sum())
    total_comision_cobros = float(cf_f[cf_f['tipo'] == 'comision']['monto'].sum())
    total_costos_cobros = float(cf_f[cf_f['tipo'].isin(['costo', 'saldo_inicial'])]['monto'].sum())
    total_otros = float(cf_f[~cf_f['tipo'].isin(['abono', 'comision', 'costo', 'saldo_inicial'])]['monto'].sum())

    print(f"\n  Abonos recibidos:     S/ {total_abonos:>10,.2f}")
    print(f"  Comisiones (cobros):  S/ {total_comision_cobros:>10,.2f}")
    print(f"  Costos (cobros):      S/ {total_costos_cobros:>10,.2f}")
    if total_otros:
        print(f"  Otros:                S/ {total_otros:>10,.2f}")

    # 4. CÁLCULO DEL SALDO
    print(f"\n{'=' * 65}")
    print("4️⃣  CÁLCULO DEL SALDO (según código actual)")
    print("=" * 65)
    print(f"  Adeudado (comisiones + costos de cobros):  S/ {total_comision_cobros + total_costos_cobros:>10,.2f}")
    print(f"  - Abonos:                                   S/ {total_abonos:>10,.2f}")
    print(f"  ─────────────────────────────────────────────────")
    saldo = max(0, (total_comision_cobros + total_costos_cobros) - total_abonos)
    print(f"  Saldo Pendiente:                            S/ {saldo:>10,.2f}")

    print(f"\n{'─' * 65}")
    print(f"  [Versión esperada por usuario]")
    print(f"  Adeudado (comision_desde_mar + costos_desde_mar): S/ {comision_5 + total_costos_sin_saldo:>10,.2f}")
    print(f"  - Abonos:                                             S/ {total_abonos:>10,.2f}")
    saldo_esperado = max(0, (comision_5 + total_costos_sin_saldo) - total_abonos)
    print(f"  Saldo Pendiente:                                      S/ {saldo_esperado:>10,.2f}")

    # Mostrar detalle completo
    print(f"\n{'─' * 65}")
    print("📋 DETALLE COMPLETO DESDE 03/03")
    print("=" * 65)
    print(f"  COSTOS:                       S/ {total_costos_sin_saldo:>10,.2f}")
    print(f"  + COMISIÓN 5%:                S/ {comision_5:>10,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  = DEUDA TOTAL:                S/ {comision_5 + total_costos_sin_saldo:>10,.2f}")
    print(f"  - ABONOS:                     S/ {total_abonos:>10,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  = SALDO PENDIENTE:            S/ {comision_5 + total_costos_sin_saldo - total_abonos:>10,.2f}")

    # Mostrar saldo base
    print(f"\n  Saldo Base (al 03/03):        S/ {costo_saldo:>10,.2f}")
    print(f"  Adeudado total + saldo base:  S/ {costo_saldo + comision_5 + total_costos_sin_saldo:>10,.2f}")
else:
    print("  No hay documentos en cobros!")
