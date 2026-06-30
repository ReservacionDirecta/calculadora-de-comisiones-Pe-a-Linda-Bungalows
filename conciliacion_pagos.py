#!/usr/bin/env python3
"""
Conciliación de Pagos — Peña Linda Bungalows
Sirvoy = registro maestro de TODOS los pagos del hotel.
Se contrastan pagos con tarjeta vs plataformas.
Link de Pago retenidos por embargo se muestran por separado.
"""
import pandas as pd, warnings, os, sys
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
from data_processor import PaymentDataProcessor
p = PaymentDataProcessor()

MODO = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
hoy = datetime.now()
if MODO == 'weekly':
    dias_desde_martes = (hoy.weekday() - 1) % 7
    lunes_anterior = hoy - timedelta(days=dias_desde_martes + 1)
    martes_anterior = lunes_anterior - timedelta(days=6)
    fecha_inicio = martes_anterior; fecha_fin = lunes_anterior
else:
    fecha_inicio = datetime(2026, 5, 22); fecha_fin = datetime(2026, 6, 22)
periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"

def q(text=""): print(text)
def linea(c="═", n=62): q(c * n)
def sep(): q("  " + "─" * 55)

# ═══ 1. SIRVOY ═══
q("📥 Cargando Sirvoy...")
sv_raw = pd.read_csv(os.path.join(CARPETA, 'sirvoy_pagos_22may_22jun_2026.csv'), encoding='utf-8')
sv = p.load_sirvoy_data(os.path.join(CARPETA, 'sirvoy_pagos_22may_22jun_2026.csv'))
col_m = next((c for c in ['amount','monto_eur','monto_eur_sirvoy'] if c in sv.columns), None)
sv['monto_num'] = pd.to_numeric(sv[col_m], errors='coerce')

met_col = next((c for c in ['payment_method_sirvoy_clean','payment_method_sirvoy','method'] if c in sv.columns), None)
if met_col: sv['metodo_clean'] = sv[met_col].astype(str).str.strip().str.lower()

# Clasificar Sirvoy
m_tarj = sv[sv['metodo_clean'].str.contains('tarjeta|card', na=False)]['monto_num'].sum() if met_col else 0
m_transf = sv[sv['metodo_clean'].str.contains('transferencia|transf', na=False)]['monto_num'].sum() if met_col else 0
m_efect = sv[sv['metodo_clean'].str.contains('efectivo|cash|efect', na=False)]['monto_num'].sum() if met_col else 0
m_otros = sv['monto_num'].sum() - m_tarj - m_transf - m_efect

# Identificar Link de Pago (embargo)
sv_raw['monto_num'] = pd.to_numeric(sv_raw['Amount'].astype(str).str.replace(',','.'), errors='coerce')
mask_link = sv_raw['Comment'].astype(str).str.lower().str.contains('link|pago.link', na=False)
link_tx = sv_raw[mask_link]
link_monto = link_tx['monto_num'].sum()
link_tx_count = len(link_tx)

# ═══ 2. PLATAFORMAS ═══
q("📥 Cargando plataformas...")
def cargar(nombre, archivo, tipo):
    try:
        ruta = os.path.join(CARPETA, archivo)
        if tipo == 'openpay':
            df = p.load_openpay_data(ruta)
            return len(df), df['amount'].sum(), 0
        elif tipo == 'izipay':
            df = p.load_izipay_data(ruta)
            return len(df), df['Importe del pago'].sum(), 0
        elif tipo == 'culqi':
            df = p.load_culqi_data(ruta)
            return len(df), df['Monto VENTA'].sum(), 0
    except: return 0, 0.0, 0

tx_op, m_op, _ = cargar('Openpay', 'openpay_mayo_2026.csv', 'openpay')
tx_iz_s, m_iz_s, _ = cargar('Izipay Soles', 'izipay_soles_22may_22jun_2026.csv', 'izipay')
tx_iz_u, m_iz_u, _ = cargar('Izipay USD', 'izipay_22may_22jun_2026.csv', 'izipay')
tx_cq, m_cq, _ = cargar('Culqi', 'culqi_ventas_22may_22jun_2026.csv', 'culqi')

total_plat_soles = m_op + m_iz_s + m_cq
total_plat_usd = m_iz_u
total_sv = m_tarj + m_transf + m_efect + m_otros
neto_disponible = total_sv - link_monto

# ═══ REPORTE ═══
linea(); q(f"🏝️  PEÑA LINDA BUNGALOWS — Conciliación de Pagos")
linea(); q(f"📅  {periodo}  |  {datetime.now().strftime('%d/%m/%Y %H:%M')} (hora Lima)  |  Modo: {MODO.upper()}")
linea()

# ─── SECCIÓN 1: SIRVOY MAESTRO ───
q("\n📋  REGISTRO MAESTRO — SIRVOY (todos los pagos del hotel)")
sep()
q(f"  {'💳 Pago con tarjeta':<35}  S/{m_tarj:>10,.2f}")
q(f"  {'🏦 Transferencia bancaria':<35}  S/{m_transf:>10,.2f}")
q(f"  {'💵 Efectivo':<35}  S/{m_efect:>10,.2f}")
q(f"  {'📌 Otros':<35}  S/{m_otros:>10,.2f}")
sep()
q(f"  {'📊 TOTAL SIRVOY':<35}  S/{total_sv:>10,.2f}")

# ─── SECCIÓN 2: LINK DE PAGO RETENIDO ───
q(f"\n🚫  LINK DE PAGO — RETENIDOS POR EMBARGO")
linea()
q(f"  {link_tx_count} transacciones identificadas como Link de Pago")
q(f"  Fondos capturados por Izipay pero NO depositados por embargo")
sep()
q(f"  {'💳 Pago con tarjeta (Link)':<35}  {link_tx[link_tx['Method'].str.contains('tarjeta|card', case=False, na=False)]['monto_num'].sum():>10,.2f}")
q(f"  {'🏦 Transferencia (Link)':<35}  {link_tx[link_tx['Method'].str.contains('transferencia|transf', case=False, na=False)]['monto_num'].sum():>10,.2f}")
sep()
q(f"  {'🚫 TOTAL RETENIDO':<35}  S/{link_monto:>10,.2f}")
q(f"  {'💰 NETO DISPONIBLE (Sirvoy - Retenido)':<35}  S/{neto_disponible:>10,.2f}")

# ─── SECCIÓN 3: CONTRASTE TARJETA ───
q(f"\n⚡  CONTRASTE — Pagos con Tarjeta")
linea()
q(f"\n  📊 Plataformas (Openpay + Izipay + Culqi):")
q(f"  {'Openpay':<30}  S/{m_op:>10,.2f}")
q(f"  {'Izipay (Soles)':<30}  S/{m_iz_s:>10,.2f}")
q(f"  {'Izipay (USD)':<30}  USD {m_iz_u:>9,.2f}")
q(f"  {'Culqi':<30}  S/{m_cq:>10,.2f}")
sep()
q(f"  {'Total Plataformas (Soles)':<30}  S/{total_plat_soles:>10,.2f}")

q(f"\n  🔄 Contraste Tarjeta:")
sep()
q(f"  Sirvoy (Pagos con tarjeta):           S/{m_tarj:>10,.2f}")
q(f"  Plataformas:                          S/{total_plat_soles:>10,.2f}")
dif = m_tarj - total_plat_soles
pct = (dif / m_tarj * 100) if m_tarj > 0 else 0
sep()
if dif >= 0:
    q(f"  ✅ Diferencia (Sirvoy > Plataformas):  S/{dif:>10,.2f}  ({pct:.1f}%)")
else:
    q(f"  ⚠️  Diferencia (Plataformas > Sirvoy):  S/{abs(dif):>10,.2f}  ({abs(pct):.1f}%)")
q(f"     Posibles causas: pagos manuales, Culqi incompleto, Link retenidos")

# ─── SECCIÓN 4: INGRESOS DIRECTOS ───
q(f"\n🏦  INGRESOS DIRECTOS (Transferencias + Efectivo)")
linea()
q(f"  Estos pagos NO pasan por plataformas — sin comisión de gateway")
q(f"  {'🏦 Transferencias':<35}  S/{m_transf:>10,.2f}")
q(f"  {'💵 Efectivo':<35}  S/{m_efect:>10,.2f}")
m_directo = m_transf + m_efect
sep()
q(f"  {'💰 Total Ingresos Directos':<35}  S/{m_directo:>10,.2f}")

# ─── SECCIÓN 5: COMISIONES ───
q(f"\n📋  COMISIONES CHAMBA DIGITAL (5%)")
linea()
q(f"\n  ✅  Política: Se cobra sobre VENTAS GENERADAS CONTABILIZADAS (Bruto Sirvoy)")
q(f"     Situaciones financieras/fiscales del hotel no afectan la comisión")
q(f"\n  {'Base Soles (Bruto Sirvoy)':<35}  S/{total_sv:>10,.2f}")
q(f"  {'Base USD':<35}  USD {total_plat_usd:>9,.2f}")
sep()
q(f"  🏪  Comisión 5% Soles:               S/{total_sv * 0.05:>10,.2f}")
q(f"  🏪  Comisión 5% USD:                 USD {total_plat_usd * 0.05:>9,.2f}")

q(f"\n  Desglose de la Base Soles:")
q(f"  {'💳 Pagos Tarjeta (vía plataformas)':<35}  S/{m_tarj:>10,.2f}")
q(f"  {'🏦 Transferencias bancarias':<35}  S/{m_transf:>10,.2f}")
q(f"  {'💵 Efectivo':<35}  S/{m_efect:>10,.2f}")
q(f"  {'🚫 Link retenido (incluido en bruto)':<35}  S/{link_monto:>10,.2f}")
sep()
q(f"  {'Total Base Soles':<35}  S/{total_sv:>10,.2f}")

linea()
q(f"\n🏢  Chamba Digital — No vendemos humo, vendemos Ingeniería")
linea()
