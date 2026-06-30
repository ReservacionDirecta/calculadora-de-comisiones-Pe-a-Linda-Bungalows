import pandas as pd
from data_processor import PaymentDataProcessor
import sys

# Redirigir salida a archivo
with open('resultado_test.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    
    print("=" * 70)
    print("PRUEBA DEL NUEVO FORMATO DE SIRVOY")
    print("=" * 70)
    print()
    
    archivo = "payments_export-2025-11-27_17_29_18.csv"
    
    processor = PaymentDataProcessor()
    
    print("Cargando archivo como Sirvoy...")
    df_sirvoy = processor.load_sirvoy_data(archivo)
    
    if not df_sirvoy.empty:
        print(f"EXITO: {len(df_sirvoy)} registros cargados")
        print(f"Columnas: {list(df_sirvoy.columns)}")
        print(f"Total monto: {df_sirvoy['monto_eur'].sum():,.2f}")
        print(f"Rango fechas: {df_sirvoy['fecha'].min()} a {df_sirvoy['fecha'].max()}")
        print("\nPrimeras 3 filas:")
        print(df_sirvoy[['fecha', 'monto_eur', 'source']].head(3))
    else:
        print("ERROR: No se cargaron registros")
    
    sys.stdout = sys.__stdout__

print("Prueba completada. Ver resultado_test.txt")


