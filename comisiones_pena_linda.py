#!/usr/bin/env python3
"""
Sistema de Reportes de Comisiones — Peña Linda Bungalows
Modos: weekly, monthly, test

Semanal (martes 10AM): Semana anterior = martes 00:00 → lunes 23:59
Mensual (día 01): Mes anterior completo
Test: Usa datos existentes para verificar cálculos

Los datos se procesan SIN descontar fees/IGV (ingresos brutos).
Se aplica 5% de comisión Chamba Digital sobre el bruto.
"""
import pandas as pd, warnings, os, sys
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
from data_processor import PaymentDataProcessor

MODO = sys.argv[1] if len(sys.argv) > 1 else 'weekly'

# ─── Determinar rango de fechas según modo ───
hoy = datetime.now()
if MODO == 'weekly':
    # Martes → semana anterior: martes anterior 00:00 a lunes 23:59
    dias_desde_martes = (hoy.weekday() - 1) % 7  # martes=1
    lunes_anterior = hoy - timedelta(days=dias_desde_martes + 1)
    martes_anterior = lunes_anterior - timedelta(days=6)
    fecha_inicio = martes_anterior.replace(hour=0, minute=0, second=0)
    fecha_fin = lunes_anterior.replace(hour=23, minute=59, second=59)
    periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
elif MODO == 'monthly':
    # Día 01 → mes anterior completo
    primer_dia_mes = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes - timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    fecha_inicio = primer_dia_mes_anterior.replace(hour=0, minute=0, second=0)
    fecha_fin = ultimo_dia_mes_anterior.replace(hour=23, minute=59, second=59)
    periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
else:  # test
    fecha_inicio = datetime(2026, 5, 22)
    fecha_fin = datetime(2026, 6, 22)
    periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"

# ─── Mapeo de archivos CSV ───
ARCHIVOS = [
    ('Openpay', 'openpay_mayo_2026.csv', 'nuevo'),
    ('Izipay (Soles)', 'izipay_soles_22may_22jun_2026.csv', 'izipay'),
    ('Izipay (USD)', 'izipay_22may_22jun_2026.csv', 'izipay'),
    ('Culqi', 'culqi_ventas_22may_22jun_2026.csv', 'culqi'),
    ('Sirvoy', 'sirvoy_pagos_22may_22jun_2026.csv', 'sirvoy'),
]

# ─── Procesar cada fuente ───
resultados = {}
total_soles, total_usd = 0.0, 0.0

for nombre, archivo, tipo in ARCHIVOS:
    ruta = os.path.join(CARPETA, archivo)
    if not os.path.exists(ruta):
        resultados[nombre] = {'tx': 0, 'monto': 0, 'error': 'Archivo no encontrado'}
        continue
    
    try:
        if tipo == 'nuevo':
            df = pd.read_csv(ruta, encoding='latin1')
            if 'amount' in df.columns:
                # Convertir monto europeo
                def conv(m):
                    try: return float(str(m).replace(',','.').replace('"',''))
                    except: return 0.0
                df['monto_num'] = df['amount'].apply(conv)
            monto = df['monto_num'].sum() if 'monto_num' in df.columns else 0
            
        elif tipo == 'izipay':
            df = pd.read_csv(ruta, sep=';', encoding='utf-8')
            col = 'Importe del pago' if 'Importe del pago' in df.columns else 'Monto del pago'
            df[col] = pd.to_numeric(df[col], errors='coerce')
            monto = df[col].sum()
            
        elif tipo == 'culqi':
            df = pd.read_csv(ruta, encoding='utf-8')
            df['Monto VENTA'] = pd.to_numeric(df['Monto VENTA'], errors='coerce')
            # Filtrar solo aprobadas
            if 'Estado' in df.columns:
                df = df[df['Estado'].astype(str).str.lower().isin(['aprobada','venta_liquidada'])]
            monto = df['Monto VENTA'].sum()
            
        elif tipo == 'sirvoy':
            p = PaymentDataProcessor()
            df = p.load_sirvoy_data(ruta)
            col_monto = None
            for c in ['amount', 'monto_eur', 'monto_eur_sirvoy']:
                if c in df.columns:
                    col_monto = c
                    break
            if col_monto:
                monto = pd.to_numeric(df[col_monto], errors='coerce').sum()
            else:
                monto = 0
        
        resultados[nombre] = {'tx': len(df), 'monto': float(monto)}
        if '(USD)' in nombre:
            total_usd += float(monto)
        else:
            total_soles += float(monto)
            
    except Exception as e:
        resultados[nombre] = {'tx': 0, 'monto': 0, 'error': str(e)[:80]}

# ─── Resultados ───
comision_soles = total_soles * 0.05
comision_usd = total_usd * 0.05

linea = "═" * 58
print(f"""
{linea}
🏝️  PEÑA LINDA BUNGALOWS — Reporte de Comisiones
{linea}
📅  Período: {periodo}
⏰  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} (hora Lima)
🔄  Modo: {MODO.upper()}
{linea}

📊 INGRESOS BRUTOS (sin descontar fees/IGV):
""")

for nombre in ['Openpay', 'Izipay (Soles)', 'Izipay (USD)', 'Culqi', 'Sirvoy']:
    d = resultados.get(nombre)
    if not d:
        continue
    if 'error' in d:
        print(f"  ❌ {nombre:<28} ERROR — {d['error']}")
        continue
    mon = 'USD' if '(USD)' in nombre else 'S/'
    estado = '✅'
    print(f"  {estado} {nombre:<28} {d['tx']:>4} tx  {mon} {d['monto']:>10,.2f}")

print(f"""
{linea}
💰  TOTAL INGRESOS BRUTOS:
     Soles:   S/ {total_soles:>12,.2f}
     USD:     USD {total_usd:>11,.2f}

📋  COMISIÓN CHAMBA DIGITAL (5%):
     Comisión Soles:  S/ {comision_soles:>12,.2f}
     Comisión USD:    USD {comision_usd:>11,.2f}
{linea}

🏢  Chamba Digital — No vendemos humo, vendemos Ingeniería
{linea}
""")
