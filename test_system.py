#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el Sistema de Procesamiento de Pagos
"""

from data_processor import PaymentDataProcessor
import pandas as pd
from datetime import datetime

def test_system():
    """Prueba el sistema con los archivos existentes"""
    print("🏨 Peña Linda Bungalows - Test del Sistema de Pagos")
    print("=" * 60)
    
    # Inicializar procesador
    processor = PaymentDataProcessor()
    
    # Cargar datos
    print("\n📁 Cargando archivos...")
    
    try:
        # Cargar Izipay
        izipay_df = processor.load_izipay_data("Listado_transacciones_capturadas-izipay.csv")
        print(f"✅ Izipay: {len(izipay_df)} transacciones cargadas")
        
        # Cargar Culqi
        culqi_df = processor.load_culqi_data("ventas_20250923_culqi.csv")
        print(f"✅ Culqi: {len(culqi_df)} transacciones cargadas")
        
        # Cargar transferencias
        secured_df = processor.load_secured_data("secured.csv")
        print(f"✅ Transferencias: {len(secured_df)} transacciones cargadas")
        
        # Cargar Facebook Ads
        try:
            facebook_df = processor.load_facebook_data("Resumen_Facturación_facebook.csv")
            print(f"✅ Facebook Ads: {len(facebook_df)} transacciones cargadas")
        except FileNotFoundError:
            print("⚠️ Facebook Ads: Archivo no encontrado (opcional)")
            facebook_df = pd.DataFrame()
        
    except FileNotFoundError as e:
        print(f"❌ Error: Archivo no encontrado - {e}")
        print("   Asegúrate de que los archivos CSV estén en el directorio actual")
        return
    
    # Unificar datos
    print("\n🔄 Unificando datos...")
    unified_df = processor.unify_data()
    print(f"✅ Datos unificados: {len(unified_df)} transacciones totales")
    
    # Mostrar estadísticas
    print("\n📊 Estadísticas Generales:")
    stats = processor.get_summary_stats()
    
    print(f"   Total de transacciones: {stats.get('total_transactions', 0):,}")
    
    # Separar ingresos y gastos
    if unified_df is not None and not unified_df.empty:
        ingresos_brutos = unified_df[unified_df['amount_gross'] > 0]['amount_gross'].sum()
        gastos = abs(unified_df[unified_df['amount_gross'] < 0]['amount_gross'].sum())
        ingresos_netos = unified_df[unified_df['amount_gross'] > 0]['amount_net'].sum()
        comision_chamba = unified_df['commission_chamba'].sum()
        comision_procesadores = unified_df['commission_processor'].sum()
        
        print(f"   Ingresos brutos: S/ {ingresos_brutos:,.2f}")
        print(f"   Gastos (Facebook): S/ {gastos:,.2f}")
        print(f"   Ingresos netos: S/ {ingresos_netos:,.2f}")
        print(f"   Comisión Chamba Digital (5%): S/ {comision_chamba:,.2f}")
        print(f"   Comisión procesadores: S/ {comision_procesadores:,.2f}")
        
        if gastos > 0:
            roi = ((ingresos_brutos - gastos - comision_chamba - comision_procesadores) / gastos) * 100
            print(f"   ROI Publicidad: {roi:.1f}%")
        
        # Análisis específico de Facebook Ads
        facebook_data = unified_df[unified_df['processor'] == 'Facebook']
        if len(facebook_data) > 0:
            print(f"\n📱 Facebook Ads:")
            if 'amount_reported' in facebook_data.columns:
                monto_reportado = facebook_data['amount_reported'].sum()
                print(f"   Monto reportado por Facebook: S/ {monto_reportado:,.2f}")
            if 'tax_adjustment' in facebook_data.columns:
                ajuste_impuestos = facebook_data['tax_adjustment'].sum()
                print(f"   Ajuste por impuestos (10.8%): S/ {ajuste_impuestos:,.2f}")
            print(f"   Gasto real cobrado: S/ {gastos:,.2f}")
            print(f"   Factor de ajuste aplicado: 10.8%")
    
    # Estadísticas por procesador
    print("\n💳 Por Procesador:")
    if unified_df is not None and not unified_df.empty:
        by_processor = unified_df.groupby('processor').agg({
            'amount': ['count', 'sum'],
            'commission': 'sum'
        }).round(2)
        
        for processor_name in by_processor.index:
            count = by_processor.loc[processor_name, ('amount', 'count')]
            total = by_processor.loc[processor_name, ('amount', 'sum')]
            commission = by_processor.loc[processor_name, ('commission', 'sum')]
            
            print(f"   {processor_name}:")
            print(f"     - Transacciones: {count:,}")
            print(f"     - Monto: S/ {total:,.2f}")
            print(f"     - Comisiones: S/ {commission:,.2f}")
    
    # Métodos de pago más utilizados
    print("\n💰 Métodos de Pago Principales:")
    if unified_df is not None and not unified_df.empty:
        payment_methods = unified_df.groupby('payment_method')['amount'].agg(['count', 'sum']).sort_values('sum', ascending=False).head(5)
        
        for method in payment_methods.index:
            count = payment_methods.loc[method, 'count']
            total = payment_methods.loc[method, 'sum']
            print(f"   {method}: {count:,} transacciones, S/ {total:,.2f}")
    
    # Rango de fechas
    print("\n📅 Rango de Fechas:")
    if unified_df is not None and not unified_df.empty and not unified_df['date'].isna().all():
        min_date = unified_df['date'].min()
        max_date = unified_df['date'].max()
        print(f"   Desde: {min_date.strftime('%d/%m/%Y %H:%M')}")
        print(f"   Hasta: {max_date.strftime('%d/%m/%Y %H:%M')}")
    
    # Prueba de filtros
    print("\n🔍 Prueba de Filtros:")
    
    # Filtro por procesador
    izipay_only = processor.filter_by_processor("Izipay")
    print(f"   Solo Izipay: {len(izipay_only)} transacciones")
    
    # Filtro por monto
    high_value = processor.filter_by_amount_range(500, 10000)
    print(f"   Transacciones > S/ 500: {len(high_value)} transacciones")
    
    # Exportar datos de prueba
    print("\n💾 Exportando datos...")
    success = processor.export_unified_data("test_export.csv", "csv")
    if success:
        print("✅ Datos exportados a 'test_export.csv'")
    else:
        print("❌ Error al exportar datos")
    
    print("\n🎉 Prueba completada exitosamente!")
    print("\n📋 Para usar la interfaz web, ejecuta:")
    print("   streamlit run web_interface.py")

def show_sample_data():
    """Muestra ejemplos de la estructura de datos esperada"""
    print("\n📋 Estructura de Datos Esperada:")
    print("\n1. IZIPAY (separador: punto y coma ';')")
    print("   Columnas principales:")
    print("   - Fecha del pago: DD/MM/YYYY HH:MM:SS")
    print("   - Importe del pago: 123.45")
    print("   - Estado: Capturado, Autorizado, etc.")
    print("   - Medio de pago: VISA, MASTERCARD, etc.")
    print("   - Comprador: Nombre del cliente")
    print("   - E-mail comprador: email@ejemplo.com")
    
    print("\n2. CULQI (separador: coma ',')")
    print("   Columnas principales:")
    print("   - Fecha de la transaccion: YYYY-MM-DD")
    print("   - Hora de la transaccion: HH:MM:SS")
    print("   - Monto VENTA: 123.45")
    print("   - Estado: abonada, rechazada, etc.")
    print("   - Marca: Visa, Mastercard, Yape, etc.")
    print("   - Nombres/Apellidos: Datos del cliente")
    
    print("\n3. TRANSFERENCIAS DIRECTAS")
    print("   Columnas:")
    print("   - payment-list-item: ID de transacción")
    print("   - payment-list-item 2: DD/MM/YYYY HH:MM")
    print("   - payment-list-item 3: Tipo de pago")
    print("   - payment-list-item 6: 1.234,56 (formato europeo)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_sample_data()
    else:
        test_system()