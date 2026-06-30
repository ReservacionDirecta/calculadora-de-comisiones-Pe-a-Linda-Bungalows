#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Reportes PDF para Peña Linda Bungalows
Genera informes financieros profesionales con KPIs, ingresos, gastos y comisiones.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        # Colores Corporativos
        self.color_primary = colors.HexColor('#1B365D') # Azul Marino
        self.color_secondary = colors.HexColor('#2E75B6') # Azul Medio
        self.color_accent = colors.HexColor('#F2F2F2') # Gris Claro
        self.color_text = colors.HexColor('#333333')

    def _setup_custom_styles(self):
        """Configura estilos personalizados para el reporte"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            alignment=TA_LEFT,
            spaceAfter=10,
            textColor=colors.HexColor('#1B365D'),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#1B365D'),
            fontName='Helvetica-Bold',
            borderPadding=(0, 0, 5, 0),
            borderWidth=0,
            borderColor=colors.HexColor('#1B365D')
        ))

        self.styles.add(ParagraphStyle(
            name='KPINumber',
            fontSize=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1B365D'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='KPILabel',
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica'
        ))

        self.styles.add(ParagraphStyle(
            name='TableText',
            fontSize=9,
            textColor=colors.HexColor('#333333')
        ))

        self.styles.add(ParagraphStyle(
            name='TableTextBold',
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1B365D')
        ))

        self.styles.add(ParagraphStyle(
            name='FooterStyle',
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))

    def _draw_header(self, elements):
        """Añade la cabecera profesional"""
        header_data = [
            [Paragraph("PEÑA LINDA BUNGALOWS", self.styles['ReportTitle']), 
             Paragraph(f"ESTADO DE CUENTA<br/><font size=10 color='#666666'>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</font>", self.styles['Normal'])]
        ]
        header_table = Table(header_data, colWidths=[11*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(HRFlowable(width="100%", thickness=2, color=self.color_primary, spaceBefore=5, spaceAfter=20))

    def generate_report(self, df_unified, stats, output_path):
        """
        Genera un informe PDF completo basado en los datos unificados y estadísticas.
        """
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []

        # --- CABECERA ---
        self._draw_header(elements)
        
        # --- INFO DEL PERIODO ---
        if 'date' in df_unified.columns and not df_unified['date'].isna().all():
            start_date = df_unified['date'].min().strftime('%d/%m/%Y')
            end_date = df_unified['date'].max().strftime('%d/%m/%Y')
            elements.append(Paragraph(f"<b>Periodo del Reporte:</b> {start_date} al {end_date}", self.styles['Normal']))
            elements.append(Spacer(1, 0.5*cm))

        # --- SECCIÓN 1: RESUMEN EJECUTIVO (KPIs) ---
        elements.append(Paragraph("Resumen Ejecutivo de Ventas", self.styles['SectionHeader']))
        
        ingresos_brutos = stats.get('total_gross_income', 0)
        gastos_fb = abs(stats.get('total_facebook_expenses', 0))
        gastos_sirvoy = abs(stats.get('total_sirvoy_expenses', 0)) # Intentar obtener de stats
        if gastos_sirvoy == 0: # Fallback a cálculo manual si no está en stats
            sirvoy_fees_data = df_unified[df_unified['source'] == 'Sirvoy Software']
            gastos_sirvoy = abs(sirvoy_fees_data['amount_gross'].sum())
            
        neto_final = stats.get('total_net_income', 0)

        # Tabla de KPIs con estilo de bloques
        kpi_data = [
            [Paragraph(f"S/ {ingresos_brutos:,.2f}", self.styles['KPINumber']), 
             Paragraph(f"S/ {gastos_fb + gastos_sirvoy:,.2f}", self.styles['KPINumber']), 
             Paragraph(f"S/ {neto_final:,.2f}", self.styles['KPINumber'])],
            [Paragraph("VENTAS BRUTAS", self.styles['KPILabel']), 
             Paragraph("GASTOS OPERATIVOS", self.styles['KPILabel']), 
             Paragraph("UTILIDAD NETA", self.styles['KPILabel'])]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[6*cm, 6*cm, 6*cm])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (0,1), 1, self.color_primary),
            ('BOX', (1,0), (1,1), 1, colors.grey),
            ('BOX', (2,0), (2,1), 1, colors.green),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 1*cm))

        # --- SECCIÓN 2: LIQUIDACIÓN DE COMISIONES ---
        elements.append(Paragraph("Liquidación de Comisiones - Chamba Digital", self.styles['SectionHeader']))
        
        comision_chamba = stats.get('total_chamba_commission', 0)
        
        commission_data = [
            [Paragraph("<b>Concepto</b>", self.styles['TableTextBold']), 
             Paragraph("<b>Base Cálculo</b>", self.styles['TableTextBold']), 
             Paragraph("<b>Tasa</b>", self.styles['TableTextBold']), 
             Paragraph("<b>Monto a Pagar</b>", self.styles['TableTextBold'])],
            [Paragraph("Comisión por Gestión de Ventas Digitales", self.styles['TableText']), 
             f"S/ {ingresos_brutos:,.2f}", 
             "5.0%", 
             f"S/ {comision_chamba:,.2f}"],
            ["", "", Paragraph("<b>TOTAL A TRANSFERIR:</b>", self.styles['TableTextBold']), 
             Paragraph(f"<b>S/ {comision_chamba:,.2f}</b>", self.styles['TableTextBold'])]
        ]
        
        comm_table = Table(commission_data, colWidths=[8*cm, 3.5*cm, 2.5*cm, 3.5*cm])
        comm_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.color_accent),
            ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('LINEBELOW', (2,2), (3,2), 1, self.color_primary),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(comm_table)
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("<i>Nota: El cálculo se realiza sobre el ingreso bruto total capturado en el periodo.</i>", self.styles['Italic']))
        elements.append(Spacer(1, 1*cm))

        # --- SECCIÓN 3: DESGLOSE POR CANAL ---
        elements.append(Paragraph("Desempeño por Canal de Procesamiento", self.styles['SectionHeader']))
        
        # Agrupar datos por procesador para la tabla
        proc_rows = []
        if not df_unified.empty:
            # Filtrar solo ingresos para esta tabla
            df_ingresos = df_unified[df_unified['income_type'] != 'Gasto']
            summary = df_ingresos.groupby('processor').agg({
                'amount_gross': 'sum',
                'commission_processor': 'sum',
                'transaction_id': 'count'
            })
            
            for proc, row in summary.iterrows():
                proc_rows.append([
                    str(proc),
                    str(int(row['transaction_id'])),
                    f"S/ {row['amount_gross']:,.2f}",
                    f"S/ {row['commission_processor']:,.2f}",
                    f"S/ {row['amount_gross'] - row['commission_processor']:,.2f}"
                ])

        proc_header = [["Canal", "Trans.", "Bruto", "Comis. Pasarela", "Neto Canal"]]
        proc_table_data = proc_header + proc_rows
        
        proc_table = Table(proc_table_data, colWidths=[4*cm, 2*cm, 4*cm, 4*cm, 4*cm])
        proc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.color_primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(proc_table)
        
        # --- SECCIÓN 4: DETALLE DE GASTOS ---
        elements.append(Paragraph("Desglose de Gastos Operativos", self.styles['SectionHeader']))
        
        gastos_data = [["Descripción", "Tipo", "Monto PEN"]]
        
        # Añadir Facebook
        if gastos_fb > 0:
            gastos_data.append(["Publicidad en Meta (Facebook Ads)", "Marketing", f"S/ {gastos_fb:,.2f}"])
        
        # Añadir Sirvoy Software
        if gastos_sirvoy > 0:
            gastos_data.append(["Suscripción Software Sirvoy (Hospitality)", "Software", f"S/ {gastos_sirvoy:,.2f}"])
            
        # Añadir Asistente Comercial
        gastos_asis = abs(stats.get('total_assistant_expenses', 0))
        if gastos_asis > 0:
            gastos_data.append(["Servicio de Asistente Comercial (Proyectado)", "Personal", f"S/ {gastos_asis:,.2f}"])

        gastos_table = Table(gastos_data, colWidths=[9*cm, 4.5*cm, 4.5*cm])
        gastos_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FFCCCC')),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(gastos_table)

        # --- SECCIÓN 5: RESUMEN DE LIQUIDACIÓN FINAL ---
        elements.append(Paragraph("Resumen de Liquidación Final (Monto a Transferir)", self.styles['SectionHeader']))
        
        liquidacion_data = [
            [Paragraph("<b>Concepto</b>", self.styles['TableTextBold']), 
             Paragraph("<b>Detalle</b>", self.styles['TableTextBold']), 
             Paragraph("<b>Monto PEN</b>", self.styles['TableTextBold'])],
            [Paragraph("Comisiones Chamba Digital", self.styles['TableText']), 
             "5% s/ Ventas Verificadas", 
             f"S/ {stats.get('total_chamba_commission', 0):,.2f}"],
            [Paragraph("Reembolso Gastos Facebook Ads", self.styles['TableText']), 
             "Ajuste incl. (Historial Completo)", 
             f"S/ {stats.get('total_facebook_expenses', 0):,.2f}"],
            [Paragraph("Reembolso Gastos Sirvoy", self.styles['TableText']), 
             "Suscripción Software", 
             f"S/ {stats.get('total_sirvoy_expenses', 0):,.2f}"],
            [Paragraph("Reembolso Gastos Asistente", self.styles['TableText']), 
             "Honorarios Proyectados", 
             f"S/ {stats.get('total_assistant_expenses', 0):,.2f}"],
            [Paragraph("Saldo Pendiente Anterior", self.styles['TableText']), 
             "Corte al 02/03/2026", 
             f"S/ {stats.get('pending_balance', 0):,.2f}"],
            [Paragraph("Pagos Realizados (Abonos a Adriana)", self.styles['TableText']), 
             "Vouchers Validados (Vision AI)", 
             f"S/ -{stats.get('total_abonos', 0):,.2f}"],
            [Paragraph("<b>SALDO NETO PENDIENTE AL 30/05/2026</b>", self.styles['TableTextBold']), 
             "", 
             Paragraph(f"<b>S/ {stats.get('net_balance', 0):,.2f}</b>", self.styles['TableTextBold'])]
        ]
        
        liq_table = Table(liquidacion_data, colWidths=[8*cm, 6*cm, 4*cm])
        liq_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.color_primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FFFFCC')), # Resaltar total
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(liq_table)
        elements.append(Spacer(1, 0.5*cm))

        # --- SECCIÓN 6: MÉTRICAS DE NEGOCIO (BI) ---
        elements.append(Paragraph("Análisis de Crecimiento y Eficiencia Comercial", self.styles['SectionHeader']))
        
        # Preparar datos de métricas
        roi = stats.get('roi_facebook', 0)
        cac = stats.get('cac', 0)
        ltv = stats.get('ltv', 0)
        mrr = stats.get('mrr', 0)
        
        bi_data = [
            [Paragraph(f"{roi:.1f}%", self.styles['KPINumber']), 
             Paragraph(f"S/ {cac:,.2f}", self.styles['KPINumber']), 
             Paragraph(f"S/ {ltv:,.2f}", self.styles['KPINumber']),
             Paragraph(f"S/ {mrr:,.2f}", self.styles['KPINumber'])],
            [Paragraph("ROI PUBLICITARIO", self.styles['KPILabel']), 
             Paragraph("COSTO ADQUISICIÓN (CAC)", self.styles['KPILabel']), 
             Paragraph("VALOR VIDA CLIENTE (LTV)", self.styles['KPILabel']),
             Paragraph("INGR. MENSUAL PROM. (MRR)", self.styles['KPILabel'])]
        ]
        
        bi_table = Table(bi_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm])
        bi_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(bi_table)
        elements.append(Spacer(1, 0.5*cm))

        # Tabla MoM Growth
        mom_stats = stats.get('mom_growth', [])
        if mom_stats:
            elements.append(Paragraph("<b>Evolución Mensual (MoM Growth)</b>", self.styles['Normal']))
            mom_data = [["Mes", "Ingreso Bruto", "Crecimiento %"]]
            for m in mom_stats:
                mom_data.append([m['month'], f"S/ {m['revenue']:,.2f}", f"{m['growth']}%"])
            
            mom_table = Table(mom_data, colWidths=[5*cm, 5*cm, 5*cm])
            mom_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.color_accent),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ]))
            elements.append(mom_table)
            elements.append(Spacer(1, 1*cm))

        # --- SECCIÓN 7: ANEXO - ÚLTIMAS TRANSACCIONES ---
        elements.append(PageBreak())
        self._draw_header(elements)
        elements.append(Paragraph("Anexo: Detalle de Transacciones (Últimas 30)", self.styles['SectionHeader']))
        
        # Obtener las 30 transacciones de ingreso más recientes
        df_recents = df_unified[df_unified['income_type'] != 'Gasto'].sort_values('date', ascending=False).head(30)
        
        recent_data = [["Fecha", "ID / Referencia", "Canal", "Cliente", "Monto PEN"]]
        for _, row in df_recents.iterrows():
            cliente = str(row.get('customer_name', ''))[:20]
            if not cliente or cliente == 'nan': cliente = "-"
            
            recent_data.append([
                row['date'].strftime('%d/%m/%y'),
                str(row.get('transaction_id', ''))[:15],
                row.get('processor', ''),
                cliente,
                f"{row['amount_gross']:,.2f}"
            ])
            
        recent_table = Table(recent_data, colWidths=[2.5*cm, 4*cm, 3*cm, 5*cm, 3.5*cm])
        recent_table.setStyle(TableStyle([
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), self.color_accent),
            ('ALIGN', (4,1), (4,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(recent_table)

        # --- PIE DE PÁGINA ---
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph("________________________________", self.styles['FooterStyle']))
        elements.append(Paragraph("Sello de Validación del Sistema PLB", self.styles['FooterStyle']))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(f"Pagina 1 de 2 | Sistema de Automatización Financiera PLB v2.0", self.styles['FooterStyle']))

        # Construir PDF
        doc.build(elements)
        return output_path
