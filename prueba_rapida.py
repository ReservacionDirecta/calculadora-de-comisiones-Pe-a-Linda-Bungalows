# -*- coding: utf-8 -*-
import pandas as pd
from data_processor import PaymentDataProcessor

archivo = "payments_export-2025-11-27_17_29_18.csv"

print("Iniciando prueba...")
processor = PaymentDataProcessor()

try:
    df = processor.load_sirvoy_data(archivo)
    print(f"Registros cargados: {len(df)}")
    
    if not df.empty:
        print(f"Columnas disponibles: {', '.join(df.columns[:5])}")
        print(f"Total monto EUR: {df['monto_eur'].sum():,.2f}")
        print(f"Fecha minima: {df['fecha'].min()}")
        print(f"Fecha maxima: {df['fecha'].max()}")
        print("\nPrimeras 3 registros:")
        for idx, row in df.head(3).iterrows():
            print(f"  Fecha: {row['fecha']}, Monto: {row['monto_eur']:.2f}, Source: {row.get('source', 'N/A')}")
        print("\n✅ PRUEBA EXITOSA")
    else:
        print("❌ No se cargaron registros")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()


