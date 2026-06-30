#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el nuevo formato de Sirvoy (payments_export)
"""

from data_processor import PaymentDataProcessor
import pandas as pd

def test_nuevo_formato_sirvoy():
    """Prueba el procesamiento del nuevo formato de Sirvoy"""
    print("🧪 Prueba del Nuevo Formato de Sirvoy")
    print("=" * 60)
    
    # Inicializar procesador
    processor = PaymentDataProcessor()
    
    # Cargar el nuevo archivo de Sirvoy
    print("\n📁 Cargando archivo payments_export-2025-11-27_17_29_18.csv...")
    try:
        df_sirvoy = processor.load_sirvoy_data("payments_export-2025-11-27_17_29_18.csv")
        
        if not df_sirvoy.empty:
            print(f"✅ Sirvoy: {len(df_sirvoy)} registros cargados")
            print(f"\n📊 Primeras 5 filas:")
            print(df_sirvoy[['fecha', 'monto_eur', 'source']].head())
            print(f"\n💰 Montos:")
            print(f"  Total: {df_sirvoy['monto_eur'].sum():,.2f}")
            print(f"  Promedio: {df_sirvoy['monto_eur'].mean():,.2f}")
            print(f"  Mínimo: {df_sirvoy['monto_eur'].min():,.2f}")
            print(f"  Máximo: {df_sirvoy['monto_eur'].max():,.2f}")
            print(f"\n📅 Rango de fechas:")
            print(f"  Desde: {df_sirvoy['fecha'].min()}")
            print(f"  Hasta: {df_sirvoy['fecha'].max()}")
        else:
            print("❌ No se cargaron registros")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Probar también cargándolo como "Transferencias Directas"
    print("\n" + "=" * 60)
    print("📁 Probando carga como Transferencias Directas...")
    try:
        processor2 = PaymentDataProcessor()
        df_secured = processor2.load_secured_data("payments_export-2025-11-27_17_29_18.csv")
        
        if not df_secured.empty:
            print(f"✅ Transferencias: {len(df_secured)} registros cargados")
            print(f"✅ El archivo se procesó correctamente como Sirvoy")
        else:
            print("❌ No se cargaron registros")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_nuevo_formato_sirvoy()


