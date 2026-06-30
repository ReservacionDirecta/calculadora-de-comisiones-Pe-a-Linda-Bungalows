#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script FINAL para procesar los reportes de Marzo a Mayo 2026.
Periodo estricto: 03/03/2026 al 30/05/2026.
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

def process_reports():
    print(f"🚀 Iniciando procesamiento ESTRICTO (03 Mar - 30 May 2026)...")
    
    processor = PaymentDataProcessor()
    
    # 1-7. Cargar datos (mismo flujo robusto)
    processor.load_izipay_data("izipay_pen.csv")
    df_usd = processor._read_csv_robust("izipay_usd.csv", sep=';')
    if df_usd is not None:
        df_usd['Moneda'] = 'USD'
        if 'Monto del pago' in df_usd.columns: df_usd = df_usd.rename(columns={'Monto del pago': 'Importe del pago'})
        cleaned_usd = processor._clean_izipay_data(df_usd)
        processor.izipay_data = pd.concat([processor.izipay_data, cleaned_usd], ignore_index=True) if processor.izipay_data is not None else cleaned_usd

    processor.load_culqi_data("ventasculqi.csv")
    openpay_files = ["20260530-172659a30c9a73-8dbf-40d2-86df-3a279a204277.csv", "20260530-172727dc9d8d78-4a3d-4f81-b172-52663c57df65.csv"]
    combined_openpay = []
    for file in openpay_files:
        if os.path.exists(file):
            df = processor.load_openpay_data(file)
            if df is not None and not df.empty: combined_openpay.append(df)
    if combined_openpay: processor.openpay_data = pd.concat(combined_openpay, ignore_index=True)
    
    processor.load_sirvoy_data("sirvoy_income_2026.csv")
    processor.sirvoy_expenses = processor.load_sirvoy_expenses("sirvoy_gastos.csv")
    processor.load_facebook_data("Resumen_Facturación_facebook_completo.csv")
    
    # 8. Unificar y FILTRAR POR PERIODO ESTRICTO
    unified_df = processor.unify_data()
    if unified_df.empty: return
    
    start_filter = datetime(2026, 3, 3)
    end_filter = datetime(2026, 5, 30, 23, 59, 59)
    unified_df = unified_df[(unified_df['date'] >= start_filter) & (unified_df['date'] <= end_filter)].copy()
    
    # 9. Calcular Estadísticas y Métricas BI
    print("📊 Calculando métricas de negocio...")
    
    saldo_anterior = 9654.83
    # Abonos validados por Vision AI (62 vouchers válidos, excluyendo los observados)
    total_abonos = 31514.25
    
    # Asistente: 03/03 se cobra, cada 14 días
    assistant_payments = []
    curr_asis = datetime(2026, 3, 3)
    period_end = unified_df['date'].max()
    while curr_asis <= period_end:
        assistant_payments.append({'date': curr_asis, 'amount': 750.0})
        unified_df = pd.concat([unified_df, pd.DataFrame([{
            'transaction_id': f"ASIS_{curr_asis.strftime('%Y%m%d')}", 'date': curr_asis,
            'amount_gross': -750.0, 'amount_net': -750.0, 'currency': 'PEN',
            'processor': 'Personal', 'source': 'Gastos Operativos', 'income_type': 'Gasto',
            'is_verified': True, 'commission_processor': 0, 'commission_chamba': 0,
            'customer_name': 'Asistente Comercial', 'payment_method': 'Honorarios'
        }])], ignore_index=True)
        curr_asis += timedelta(days=14)
    
    gastos_asis = sum(p['amount'] for p in assistant_payments)
    
    # KPIs Básicos
    ventas_brutas = unified_df[unified_df['income_type'].isin(['Tarjeta', 'Transferencia', 'Efectivo'])]['amount_gross'].sum()
    gastos_fb = abs(unified_df[unified_df['source'] == 'Facebook Ads']['amount_gross'].sum())
    gastos_sv = abs(unified_df[unified_df['source'] == 'Sirvoy Software']['amount_gross'].sum())
    comision_chamba = unified_df['commission_chamba'].sum()
    comision_proc = unified_df['commission_processor'].sum()
    
    neto_periodo = ventas_brutas - gastos_fb - gastos_sv - gastos_asis - comision_chamba - comision_proc
    total_liquidacion = comision_chamba + gastos_fb + gastos_sv + gastos_asis + saldo_anterior
    saldo_neto_pendiente = total_liquidacion - total_abonos

    # --- MÉTRICAS BI ---
    df_income = unified_df[unified_df['amount_gross'] > 0]
    unique_customers = df_income['customer_name'].nunique()
    cac = gastos_fb / unique_customers if unique_customers > 0 else 0
    ltv = ventas_brutas / unique_customers if unique_customers > 0 else 0
    mrr = ventas_brutas / 3 # Marzo, Abril, Mayo
    
    unified_df['month'] = unified_df['date'].dt.month
    monthly_rev = unified_df[unified_df['amount_gross'] > 0].groupby('month')['amount_gross'].sum()
    mom_growth = []
    prev_rev = 0
    month_names = {3: 'Marzo', 4: 'Abril', 5: 'Mayo'}
    for m in [3, 4, 5]:
        rev = monthly_rev.get(m, 0)
        growth = round(((rev - prev_rev) / prev_rev) * 100, 1) if prev_rev > 0 else 0
        mom_growth.append({'month': month_names[m], 'revenue': rev, 'growth': growth})
        prev_rev = rev

    report_stats = {
        'total_gross_income': ventas_brutas, 
        'total_facebook_expenses': gastos_fb,
        'total_sirvoy_expenses': gastos_sv, 
        'total_assistant_expenses': gastos_asis,
        'total_net_income': neto_periodo, 
        'total_chamba_commission': comision_chamba,
        'total_processor_commission': comision_proc, 
        'pending_balance': saldo_anterior,
        'total_abonos': total_abonos,
        'total_to_pay': total_liquidacion,
        'net_balance': saldo_neto_pendiente,
        'roi_facebook': (neto_periodo / gastos_fb * 100) if gastos_fb > 0 else 0,
        'cac': cac, 'ltv': ltv, 'mrr': mrr, 'mom_growth': mom_growth
    }

    # 10. Generar Reporte
    pdf_gen = PDFGenerator()
    pdf_filename = f"reporte_consolidado_PLB_03Mar_30May_FINAL.pdf"
    pdf_gen.generate_report(unified_df, report_stats, pdf_filename)
    
    print(f"\n✅ PROCESO COMPLETADO")
    print(f"Total Liquidación: S/ {total_liquidacion:,.2f}")
    print(f"Comisión 5%:      S/ {comision_chamba:,.2f}")
    print(f"Saldo Anterior:   S/ {saldo_anterior:,.2f}")

if __name__ == "__main__":
    process_reports()
