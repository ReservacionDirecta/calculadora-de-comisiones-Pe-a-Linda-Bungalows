#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug específico para datos de Facebook
"""

from data_processor import PaymentDataProcessor
import pandas as pd

def debug_facebook():
    print("=" * 60)
    print("DEBUG FACEBOOK ADS")
    print("=" * 60)
    
    processor = PaymentDataProcessor()
    
    # Cargar solo Facebook
    print("1. Cargando datos de Facebook...")
    facebook_df = processor.load_facebook_data("Resumen_Facturación_facebook.csv")
    
    if facebook_df.empty:
        print("❌ No se cargaron datos de Facebook")
        return
    
    print(f"✅ Cargados {len(facebook_df)} registros")
    print("\n2. Datos crudos de Facebook:")
    print(facebook_df[['Fecha', 'Importe', 'source']].head())
    
    # Unificar datos
    print("\n3. Unificando datos...")
    unified_df = processor.unify_data()
    
    # Filtrar solo Facebook
    facebook_unified = unified_df[unified_df['processor'] == 'Facebook']
    
    print(f"\n4. Datos unificados de Facebook ({len(facebook_unified)} registros):")
    if len(facebook_unified) > 0:
        print("\nColumnas disponibles:")
        print(facebook_unified.columns.tolist())
        
        print("\nPrimeros registros:")
        cols_to_show = ['date', 'amount_gross', 'amount_reported', 'tax_adjustment', 'processor']
        available_cols = [col for col in cols_to_show if col in facebook_unified.columns]
        print(facebook_unified[available_cols].head())
        
        print("\n5. Verificación de cálculos:")
        for idx, row in facebook_unified.head(3).iterrows():
            print(f"\nRegistro {idx}:")
            print(f"  Fecha: {row.get('date', 'N/A')}")
            print(f"  Monto reportado: {row.get('amount_reported', 'N/A')}")
            print(f"  Ajuste impuestos: {row.get('tax_adjustment', 'N/A')}")
            print(f"  Monto bruto (real): {row.get('amount_gross', 'N/A')}")
            
            # Verificar cálculo
            if 'amount_reported' in row and 'tax_adjustment' in row:
                reportado = row.get('amount_reported', 0)
                ajuste = row.get('tax_adjustment', 0)
                real = abs(row.get('amount_gross', 0))
                calculado = reportado + ajuste
                
                print(f"  Verificación: {reportado} + {ajuste} = {calculado} (esperado: {real})")
                if abs(calculado - real) < 0.01:
                    print("  ✅ Cálculo correcto")
                else:
                    print("  ❌ Error en cálculo")
    else:
        print("❌ No hay datos de Facebook en los datos unificados")
    
    print("\n6. Resumen:")
    if len(facebook_unified) > 0:
        total_reportado = facebook_unified['amount_reported'].sum() if 'amount_reported' in facebook_unified.columns else 0
        total_ajuste = facebook_unified['tax_adjustment'].sum() if 'tax_adjustment' in facebook_unified.columns else 0
        total_real = abs(facebook_unified['amount_gross'].sum())
        
        print(f"  Total reportado: S/ {total_reportado:,.2f}")
        print(f"  Total ajuste: S/ {total_ajuste:,.2f}")
        print(f"  Total real: S/ {total_real:,.2f}")
        print(f"  Factor aplicado: {(total_real/total_reportado) if total_reportado > 0 else 0:.3f}")

if __name__ == "__main__":
    debug_facebook()