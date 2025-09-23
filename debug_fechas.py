#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug para verificar fechas específicas
"""

from data_processor import PaymentDataProcessor
import pandas as pd

def debug_fechas():
    print("=" * 60)
    print("DEBUG FECHAS 8-14 JULIO 2025")
    print("=" * 60)
    
    processor = PaymentDataProcessor()
    
    # Cargar todos los datos
    processor.load_facebook_data("Resumen_Facturación_facebook.csv")
    unified_df = processor.unify_data()
    
    # Filtrar Facebook
    facebook_data = unified_df[unified_df['processor'] == 'Facebook']
    
    print("1. Todas las transacciones de Facebook:")
    for idx, row in facebook_data.iterrows():
        fecha = row['date']
        reportado = row.get('amount_reported', 0)
        ajuste = row.get('tax_adjustment', 0)
        real = abs(row.get('amount_gross', 0))
        
        print(f"  {fecha.strftime('%d/%m/%Y')}: Reportado S/ {reportado:,.2f}, Ajuste S/ {ajuste:,.2f}, Real S/ {real:,.2f}")
    
    # Filtrar por fechas 8-14 julio
    start_date = pd.to_datetime('2025-07-08')
    end_date = pd.to_datetime('2025-07-14')
    
    mask = (facebook_data['date'] >= start_date) & (facebook_data['date'] <= end_date)
    facebook_julio = facebook_data[mask]
    
    print(f"\n2. Transacciones Facebook del 8-14 julio ({len(facebook_julio)} registros):")
    
    if len(facebook_julio) > 0:
        for idx, row in facebook_julio.iterrows():
            fecha = row['date']
            reportado = row.get('amount_reported', 0)
            ajuste = row.get('tax_adjustment', 0)
            real = abs(row.get('amount_gross', 0))
            
            print(f"  {fecha.strftime('%d/%m/%Y')}: Reportado S/ {reportado:,.2f}, Ajuste S/ {ajuste:,.2f}, Real S/ {real:,.2f}")
        
        # Totales
        total_reportado = facebook_julio['amount_reported'].sum()
        total_ajuste = facebook_julio['tax_adjustment'].sum()
        total_real = abs(facebook_julio['amount_gross'].sum())
        
        print(f"\n3. Totales del período:")
        print(f"  Total reportado: S/ {total_reportado:,.2f}")
        print(f"  Total ajuste: S/ {total_ajuste:,.2f}")
        print(f"  Total real: S/ {total_real:,.2f}")
    else:
        print("  ❌ No hay transacciones de Facebook en este período")
        
        # Mostrar las fechas más cercanas
        print("\n3. Fechas más cercanas:")
        facebook_sorted = facebook_data.sort_values('date')
        for idx, row in facebook_sorted.head(5).iterrows():
            fecha = row['date']
            real = abs(row.get('amount_gross', 0))
            print(f"  {fecha.strftime('%d/%m/%Y')}: S/ {real:,.2f}")

if __name__ == "__main__":
    debug_fechas()