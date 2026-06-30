#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar reportes semanales (Martes a Lunes) del periodo Marzo-Mayo 2026.
Incluye costos proyectados del asistente comercial.
"""

import pandas as pd
from data_processor import PaymentDataProcessor
from pdf_generator import PDFGenerator
from datetime import datetime, timedelta
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_weekly_reports():
    print("🚀 Iniciando generación de reportes semanales (Martes a Lunes)...")
    
    processor = PaymentDataProcessor()
    
    # 1. Cargar todos los datos
    processor.load_izipay_data("izipay_pen.csv")
    df_usd = processor._read_csv_robust("izipay_usd.csv", sep=';')
    if df_usd is not None:
        df_usd['Moneda'] = 'USD'
        if 'Monto del pago' in df_usd.columns and 'Importe del pago' not in df_usd.columns:
            df_usd = df_usd.rename(columns={'Monto del pago': 'Importe del pago'})
        cleaned_usd = processor._clean_izipay_data(df_usd)
        if processor.izipay_data is not None:
            processor.izipay_data = pd.concat([processor.izipay_data, cleaned_usd], ignore_index=True)
        else:
            processor.izipay_data = cleaned_usd

    processor.load_culqi_data("ventasculqi.csv")
    openpay_files = ["20260530-172659a30c9a73-8dbf-40d2-86df-3a279a204277.csv", "20260530-172727dc9d8d78-4a3d-4f81-b172-52663c57df65.csv", "20260530-172711082425cd-5cd9-4b42-8f7c-8c4734092508.csv"]
    combined_openpay = []
    for file in openpay_files:
        if os.path.exists(file):
            df = processor.load_openpay_data(file)
            if df is not None and not df.empty: combined_openpay.append(df)
    if combined_openpay: processor.openpay_data = pd.concat(combined_openpay, ignore_index=True)
    
    processor.load_sirvoy_data("sirvoy_income_2026.csv")
    processor.sirvoy_expenses = processor.load_sirvoy_expenses("sirvoy_gastos.csv")
    processor.load_facebook_data("Resumen_Facturación_facebook_completo.csv")
    
    # 2. Unificar
    unified_df = processor.unify_data()
    if unified_df.empty: return

    # 3. Proyectar Asistente Comercial (S/ 750 cada 2 semanas empezando el 03/03/2026)
    current_asis_date = datetime(2026, 3, 3) # Empezamos el 03 de marzo
    period_end = unified_df['date'].max()
    
    while current_asis_date <= period_end:
        # Agregar al dataframe para que aparezca en el anexo de la semana correspondiente
        unified_df = pd.concat([unified_df, pd.DataFrame([{
            'transaction_id': f"ASIS_{current_asis_date.strftime('%Y%m%d')}",
            'date': current_asis_date,
            'amount_gross': -750.0,
            'amount_net': -750.0,
            'currency': 'PEN',
            'processor': 'Personal',
            'source': 'Gastos Operativos',
            'income_type': 'Gasto',
            'is_verified': True,
            'commission_processor': 0,
            'commission_chamba': 0,
            'customer_name': 'Asistente Comercial',
            'payment_method': 'Honorarios'
        }])], ignore_index=True)
        current_asis_date += timedelta(days=14)

    # 4. Definir rangos semanales
    start_date = datetime(2026, 3, 3)
    current_start = start_date
    week_count = 1
    pdf_gen = PDFGenerator()
    os.makedirs("reportes_semanales", exist_ok=True)
    summary_list = []

    while current_start <= period_end:
        current_end = current_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        mask = (unified_df['date'] >= current_start) & (unified_df['date'] <= current_end)
        week_df = unified_df.loc[mask].copy()
        
        if not week_df.empty:
            ingresos_brutos = week_df[week_df['income_type'].isin(['Tarjeta', 'Transferencia', 'Efectivo'])]['amount_gross'].sum()
            gastos_fb = abs(week_df[week_df['source'] == 'Facebook Ads']['amount_gross'].sum())
            gastos_sirvoy = abs(week_df[week_df['source'] == 'Sirvoy Software']['amount_gross'].sum())
            gastos_asistente = abs(week_df[week_df['customer_name'] == 'Asistente Comercial']['amount_gross'].sum())
            comision_chamba = week_df['commission_chamba'].sum()
            comision_proc = week_df['commission_processor'].sum()
            neto_semana = ingresos_brutos - gastos_fb - gastos_sirvoy - gastos_asistente - comision_chamba - comision_proc

            stats = {
                'total_gross_income': ingresos_brutos, 'total_facebook_expenses': gastos_fb,
                'total_sirvoy_expenses': gastos_sirvoy, 'total_assistant_expenses': gastos_asistente,
                'total_net_income': neto_semana, 'total_chamba_commission': comision_chamba,
                'total_processor_commission': comision_proc, 'roi_facebook': (neto_semana / gastos_fb * 100) if gastos_fb > 0 else 0,
                'facebook_reported_raw': gastos_fb / 1.1197, 'facebook_tax_adjustment': 0
            }
            
            filename = f"reportes_semanales/Semana_{week_count}_{current_start.strftime('%Y%m%d')}_{current_end.strftime('%Y%m%d')}.pdf"
            pdf_gen.generate_report(week_df, stats, filename)
            summary_list.append({'Semana': f"{current_start.strftime('%d/%m')} - {current_end.strftime('%d/%m')}", 'Bruto': f"S/ {ingresos_brutos:,.2f}", 'Comisión': f"S/ {comision_chamba:,.2f}", 'Gastos': f"S/ {gastos_fb+gastos_sirvoy+gastos_asistente:,.2f}", 'Neto': f"S/ {neto_semana:,.2f}"})
        
        current_start += timedelta(days=7)
        week_count += 1

    print("\n✅ REPORTES SEMANALES FINALIZADOS")
    for s in summary_list: print(f"{s['Semana']:<15} | {s['Bruto']:<12} | {s['Comisión']:<12} | {s['Neto']:<12}")

if __name__ == "__main__":
    generate_weekly_reports()
