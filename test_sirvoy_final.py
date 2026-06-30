# -*- coding: utf-8 -*-
import pandas as pd
from data_processor import PaymentDataProcessor
import traceback

archivo = "payments_export-2025-11-27_17_29_18.csv"

resultados = []

def agregar(mensaje):
    resultados.append(mensaje)
    print(mensaje)

try:
    agregar("=" * 70)
    agregar("PRUEBA DEL NUEVO FORMATO DE SIRVOY")
    agregar("=" * 70)
    agregar("")
    
    agregar(f"Archivo: {archivo}")
    agregar("Inicializando procesador...")
    processor = PaymentDataProcessor()
    
    agregar("Cargando archivo como Sirvoy...")
    df_sirvoy = processor.load_sirvoy_data(archivo)
    
    if not df_sirvoy.empty:
        agregar(f"✅ ÉXITO: {len(df_sirvoy)} registros cargados")
        agregar(f"")
        agregar(f"Columnas disponibles:")
        for col in df_sirvoy.columns:
            agregar(f"  - {col}")
        agregar(f"")
        agregar(f"Estadísticas:")
        agregar(f"  Total monto EUR: {df_sirvoy['monto_eur'].sum():,.2f}")
        agregar(f"  Promedio: {df_sirvoy['monto_eur'].mean():,.2f}")
        agregar(f"  Mínimo: {df_sirvoy['monto_eur'].min():,.2f}")
        agregar(f"  Máximo: {df_sirvoy['monto_eur'].max():,.2f}")
        agregar(f"")
        agregar(f"Rango de fechas:")
        agregar(f"  Desde: {df_sirvoy['fecha'].min()}")
        agregar(f"  Hasta: {df_sirvoy['fecha'].max()}")
        agregar(f"")
        agregar(f"Primeras 3 registros:")
        for idx, row in df_sirvoy.head(3).iterrows():
            agregar(f"  [{idx}] Fecha: {row['fecha']}, Monto: {row['monto_eur']:.2f}")
            if 'description_sirvoy' in row:
                agregar(f"       Descripción: {row['description_sirvoy']}")
        agregar(f"")
        agregar("✅ PRUEBA EXITOSA - El nuevo formato funciona correctamente")
    else:
        agregar("❌ ERROR: No se cargaron registros")
        
except Exception as e:
    agregar(f"❌ ERROR: {e}")
    agregar("")
    agregar("Traceback:")
    agregar(traceback.format_exc())

# Guardar resultados
with open('test_resultado.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(resultados))

print("\nResultados guardados en test_resultado.txt")


