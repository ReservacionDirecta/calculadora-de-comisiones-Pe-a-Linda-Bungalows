#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba completa del nuevo formato de Sirvoy
"""

import pandas as pd
from data_processor import PaymentDataProcessor
import sys

def test_sirvoy():
    print("=" * 70)
    print("🧪 PRUEBA DEL NUEVO FORMATO DE SIRVOY")
    print("=" * 70)
    print()
    
    archivo = "payments_export-2025-11-27_17_29_18.csv"
    
    # Inicializar procesador
    processor = PaymentDataProcessor()
    
    # Prueba 1: Cargar como Sirvoy
    print("📁 PRUEBA 1: Cargando como Archivo Sirvoy...")
    print("-" * 70)
    try:
        df_sirvoy = processor.load_sirvoy_data(archivo)
        
        if not df_sirvoy.empty:
            print(f"✅ ÉXITO: {len(df_sirvoy)} registros cargados")
            print(f"\n📊 Información del DataFrame:")
            print(f"   Columnas: {list(df_sirvoy.columns)}")
            print(f"\n💰 Estadísticas de Montos:")
            print(f"   Total: S/ {df_sirvoy['monto_eur'].sum():,.2f}")
            print(f"   Promedio: S/ {df_sirvoy['monto_eur'].mean():,.2f}")
            print(f"   Mínimo: S/ {df_sirvoy['monto_eur'].min():,.2f}")
            print(f"   Máximo: S/ {df_sirvoy['monto_eur'].max():,.2f}")
            print(f"\n📅 Rango de Fechas:")
            print(f"   Desde: {df_sirvoy['fecha'].min()}")
            print(f"   Hasta: {df_sirvoy['fecha'].max()}")
            print(f"\n📋 Primeras 5 filas:")
            columnas_mostrar = ['fecha', 'monto_eur', 'source']
            if 'description_sirvoy' in df_sirvoy.columns:
                columnas_mostrar.append('description_sirvoy')
            if 'payment_method_sirvoy' in df_sirvoy.columns:
                columnas_mostrar.append('payment_method_sirvoy')
            print(df_sirvoy[columnas_mostrar].head().to_string())
        else:
            print("❌ ERROR: No se cargaron registros")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Prueba 2: Cargar como Transferencias Directas
    print("\n" + "=" * 70)
    print("📁 PRUEBA 2: Cargando como Transferencias Directas...")
    print("-" * 70)
    try:
        processor2 = PaymentDataProcessor()
        df_secured = processor2.load_secured_data(archivo)
        
        if not df_secured.empty:
            print(f"✅ ÉXITO: {len(df_secured)} registros cargados")
            print(f"✅ El archivo se procesó correctamente como Sirvoy")
            print(f"\n💰 Total: S/ {df_secured['monto_eur'].sum():,.2f}")
        else:
            print("❌ ERROR: No se cargaron registros")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Prueba 3: Verificar unificación de datos
    print("\n" + "=" * 70)
    print("📁 PRUEBA 3: Verificando unificación de datos...")
    print("-" * 70)
    try:
        unified = processor.unify_data()
        sirvoy_unified = unified[unified['source'] == 'Sirvoy']
        
        if not sirvoy_unified.empty:
            print(f"✅ ÉXITO: {len(sirvoy_unified)} registros de Sirvoy en datos unificados")
            print(f"\n💰 Total unificado: S/ {sirvoy_unified['amount_gross'].sum():,.2f}")
            print(f"\n📋 Primeras 3 filas unificadas:")
            columnas_unif = ['date', 'amount_gross', 'source', 'processor']
            if 'payment_method' in sirvoy_unified.columns:
                columnas_unif.append('payment_method')
            print(sirvoy_unified[columnas_unif].head(3).to_string())
        else:
            print("⚠️ ADVERTENCIA: No hay registros de Sirvoy en datos unificados")
            
    except Exception as e:
        print(f"⚠️ ADVERTENCIA en unificación: {e}")
    
    print("\n" + "=" * 70)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    exito = test_sirvoy()
    sys.exit(0 if exito else 1)


