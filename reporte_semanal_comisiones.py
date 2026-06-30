#!/usr/bin/env python3
"""
Reporte semanal de comisiones Peña Linda Bungalows
Calcula ingresos brutos (sin fees/IGV) y aplica 5% de comisión.
Ejecutado por cron todos los martes 10 AM (hora Lima).
"""
import pandas as pd, warnings, os, sys, traceback
warnings.filterwarnings('ignore')

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
from data_processor import PaymentDataProcessor

p = PaymentDataProcessor()
resultados = {}

# ─── 1. Openpay ───
try:
    op = p.load_openpay_data(os.path.join(CARPETA, 'openpay_mayo_2026.csv'))
    resultados['Openpay'] = {'tx': len(op), 'monto': op['amount'].sum()}
except Exception as e:
    resultados['Openpay'] = {'tx': 0, 'monto': 0, 'error': str(e)}

# ─── 2. Izipay Soles ───
try:
    iz = p.load_izipay_data(os.path.join(CARPETA, 'izipay_soles_22may_22jun_2026.csv'))
    resultados['Izipay (Soles)'] = {'tx': len(iz), 'monto': iz['Importe del pago'].sum()}
except Exception as e:
    resultados['Izipay (Soles)'] = {'tx': 0, 'monto': 0, 'error': str(e)}

# ─── 3. Izipay USD ───
try:
    iz_usd = p.load_izipay_data(os.path.join(CARPETA, 'izipay_22may_22jun_2026.csv'))
    resultados['Izipay (USD)'] = {'tx': len(iz_usd), 'monto': iz_usd['Importe del pago'].sum()}
except Exception as e:
    resultados['Izipay (USD)'] = {'tx': 0, 'monto': 0, 'error': str(e)}

# ─── 4. Culqi ───
try:
    cq = p.load_culqi_data(os.path.join(CARPETA, 'culqi_ventas_22may_22jun_2026.csv'))
    resultados['Culqi'] = {'tx': len(cq), 'monto': cq['Monto VENTA'].sum()}
except Exception as e:
    try:
        resultados['Culqi'] = {'tx': 0, 'monto': 0, 'error': str(e)}
    except:
        resultados['Culqi'] = {'tx': 0, 'monto': 0}

# ─── 5. Sirvoy (pagos registrados aquí) ───
try:
    sv = p.load_sirvoy_data(os.path.join(CARPETA, 'sirvoy_pagos_22may_22jun_2026.csv'))
    monto_sv = 0
    # La columna de monto puede llamarse 'amount', 'monto_eur' o 'monto_eur_sirvoy'
    for col in ['amount', 'monto_eur', 'monto_eur_sirvoy']:
        if col in sv.columns:
            monto_sv = pd.to_numeric(sv[col], errors='coerce').sum()
            break
    resultados['Sirvoy'] = {'tx': len(sv), 'monto': monto_sv}
except Exception as e:
    resultados['Sirvoy'] = {'tx': 0, 'monto': 0, 'error': str(e)}

# ─── 6. Sirvoy - Pagos con tarjeta (ya incluidos en Izipay/Culqi) ───
# Separamos los pagos con tarjeta registrados en Sirvoy
try:
    sv_raw = pd.read_csv(os.path.join(CARPETA, 'sirvoy_pagos_22may_22jun_2026.csv'), encoding='utf-8')
    # Buscar columna de método
    met_col = None
    for c in sv_raw.columns:
        if 'method' in c.lower():
            met_col = c
            break
    if met_col:
        # Filtrar pagos con tarjeta en Sirvoy
        mask_tarjeta = sv_raw[met_col].astype(str).str.contains('tarjeta|card', case=False, na=False)
        sv_tarjetas = sv_raw[mask_tarjeta]
        # Estos montos YA están en Izipay/Culqi, solo informativo
        col_amount = None
        for c in sv_raw.columns:
            if 'amount' in c.lower():
                col_amount = c
                break
        if col_amount:
            monto_tarjeta = pd.to_numeric(sv_tarjetas[col_amount].astype(str).str.replace(',', '.'), errors='coerce').sum()
            resultados['Sirvoy (Pagos Tarjeta - informativo)'] = {'tx': len(sv_tarjetas), 'monto': monto_tarjeta}
except:
    pass

# ─── CÁLCULO DE COMISIÓN ───
total_soles = 0
total_usd = 0

for fuente, datos in resultados.items():
    if 'error' in datos:
        continue
    # Izipay USD va aparte
    if '(USD)' in fuente:
        total_usd += datos['monto']
    else:
        total_soles += datos['monto']

# 5% de comisión
comision_soles = total_soles * 0.05
comision_usd = total_usd * 0.05

# ─── REPORTE ───
linea = "═" * 60
print(f"""
{linea}
🏝️  PEÑA LINDA BUNGALOWS — Reporte Semanal de Comisiones
{linea}
📅  Período: 22 Mayo - 22 Junio 2026
⏰  Generado: {pd.Timestamp.now(tz='America/Lima').strftime('%d/%m/%Y %H:%M')} (hora Lima)
{linea}

📊 INGRESOS BRUTOS (sin descontar fees/IGV):
""")

for fuente in ['Openpay', 'Izipay (Soles)', 'Izipay (USD)', 'Culqi', 'Sirvoy']:
    datos = resultados.get(fuente)
    if not datos:
        continue
    if 'error' in datos:
        print(f"  ❌ {fuente}: ERROR — {datos['error']}")
        continue
    moneda = 'USD' if '(USD)' in fuente else 'S/'
    print(f"  ✅ {fuente:<30} {datos['tx']:>3} tx  {moneda} {datos['monto']:>10,.2f}")

for fuente in resultados:
    if '(informativo)' in fuente:
        datos = resultados[fuente]
        print(f"  ℹ️  {fuente:<30} {datos['tx']:>3} tx  S/ {datos['monto']:>10,.2f}")

print(f"""
{linea}
💰 TOTAL INGRESOS BRUTOS:
   Soles:   S/ {total_soles:>12,.2f}
   USD:     USD {total_usd:>11,.2f}

📋 COMISIÓN AL 5%:
   Comisión Soles: S/ {comision_soles:>12,.2f}
   Comisión USD:   USD {comision_usd:>11,.2f}
{linea}

🏢 Chamba Digital — No vendemos humo, vendemos Ingeniería
{linea}
""")
