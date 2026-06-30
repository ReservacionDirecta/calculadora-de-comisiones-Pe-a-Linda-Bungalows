#!/usr/bin/env python3
"""Genera PDF del reporte semanal de comisiones - Peña Linda Bungalows"""
import os, sys
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, Image)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)

# ─── Obtener datos del reporte ───
exec(open(os.path.join(CARPETA, 'comisiones_pena_linda.py')).read().replace(
    'MODO = sys.argv[1] if len(sys.argv) > 1 else \'weekly\'', 'MODO = \'weekly\''
))

# ─── Construir PDF ───
OUTPUT = os.path.join(CARPETA, f'Comisiones_Semanal_{datetime.now().strftime("%Y%m%d")}.pdf')

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    topMargin=1.5*cm, bottomMargin=1.5*cm,
    leftMargin=2*cm, rightMargin=2*cm
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Titulo', parent=styles['Title'], fontSize=22,
           textColor=colors.HexColor('#1B365D'), spaceAfter=6))
styles.add(ParagraphStyle('Subtitulo', parent=styles['Normal'], fontSize=12,
           textColor=colors.HexColor('#666666'), spaceAfter=20, alignment=TA_CENTER))
styles.add(ParagraphStyle('Seccion', fontSize=13, textColor=colors.HexColor('#1B365D'),
           spaceBefore=15, spaceAfter=8, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('Celda', fontSize=10, textColor=colors.HexColor('#333333'),
           alignment=TA_CENTER))
styles.add(ParagraphStyle('CeldaIzq', fontSize=10, textColor=colors.HexColor('#333333'),
           alignment=TA_LEFT))
styles.add(ParagraphStyle('TotalHead', fontSize=11, textColor=colors.white,
           alignment=TA_CENTER, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor('#999999'),
           alignment=TA_CENTER))

history = []

def titulo(texto, estilo='Titulo'):
    history.append(Paragraph(texto, styles[estilo]))

def espacio(mm_val=6):
    history.append(Spacer(1, mm_val * mm))

def linea():
    history.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'),
                              spaceBefore=4, spaceAfter=4))

def tabla(datos, col_widths=None):
    t = Table(datos, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B365D')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#DDDDDD')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F5F8FC')]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    history.append(t)

# ═══ CONTENIDO ═══

espacio(10)
titulo('🏝️  Peña Linda Bungalows')
titulo('Reporte Semanal de Comisiones', 'Subtitulo')

linea()
espacio(4)

# Info general
tabla_info = [
    ['Período', periodo],
    ['Generado', f"{datetime.now().strftime('%d/%m/%Y %H:%M')} (hora Lima)"],
    ['Modo', 'SEMANAL'],
]
t_info = Table(tabla_info, colWidths=[120, 330])
t_info.setStyle(TableStyle([
    ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#333333')),
    ('ALIGN', (0,0), (0,-1), 'RIGHT'),
    ('ALIGN', (1,0), (1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 3),
    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
]))
history.append(t_info)

espacio(10)
titulo('📊 Ingresos Brutos (sin descontar fees/IGV)', 'Seccion')

datos_tabla = [['Fuente', 'Transacciones', 'Monto Bruto', 'Moneda']]
for nombre in ['Openpay', 'Izipay (Soles)', 'Izipay (USD)', 'Culqi', 'Sirvoy']:
    d = resultados.get(nombre)
    if not d or 'error' in d:
        continue
    mon = 'USD' if '(USD)' in nombre else 'S/'
    signo = '✅ '
    mon_form = f'S/ {d["monto"]:>10,.2f}' if mon == 'S/' else f'USD {d["monto"]:>10,.2f}'
    datos_tabla.append([signo + nombre, str(d['tx']), mon_form, mon])

datos_tabla.append(['', '', '', ''])
datos_tabla.append(['💰 TOTAL', '', f'S/ {total_soles:>10,.2f}', 'Soles'])
datos_tabla.append(['', '', f'USD {total_usd:>10,.2f}', 'USD'])

tabla(datos_tabla, col_widths=[200, 100, 120, 70])

espacio(12)
titulo('📋 Comisión Chamba Digital (5%)', 'Seccion')

tabla_comision = [
    ['Moneda', 'Ingreso Bruto', 'Comisión (5%)'],
    ['Soles', f'S/ {total_soles:>10,.2f}', f'S/ {comision_soles:>10,.2f}'],
    ['USD', f'USD {total_usd:>10,.2f}', f'USD {comision_usd:>10,.2f}'],
]
t_com = Table(tabla_comision, colWidths=[100, 170, 170])
t_com.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 10),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E75B6')),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BBBBBB')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#E8F0FE')]),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ('FONTSIZE', (0,-1), (-1,-1), 11),
    ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#1B365D')),
]))
history.append(t_com)

espacio(20)
linea()
titulo('🏢  Chamba Digital — No vendemos humo, vendemos Ingeniería', 'Footer')

# Generar
doc.build(history)
print(f"✅ PDF generado: {OUTPUT}")
print(f"📄 {os.path.getsize(OUTPUT):,} bytes")
