
import pandas as pd
from data_processor import PaymentDataProcessor

# Silenciar los logs para una salida más limpia
import logging
logging.basicConfig(level=logging.WARNING)

print("Iniciando depuración del proceso de cancelación de Sirvoy...")

# 1. Instanciar el procesador
processor = PaymentDataProcessor()

# 2. Cargar los datos de Sirvoy
# Usar el mismo archivo que se usó en el script de depuración anterior.
sirvoy_file = "payments_export-2025-11-29_10_18_40.csv"
print(f"Cargando datos desde: {sirvoy_file}")

# Esto ejecuta la lógica de load_sirvoy_data y _clean_sirvoy_data
# que filtra por 'Transferencia bancaria' y 'Efectivo'.
cleaned_sirvoy_df = processor.load_sirvoy_data(sirvoy_file)

if cleaned_sirvoy_df is None or cleaned_sirvoy_df.empty:
    print("Error: No se pudieron cargar o limpiar los datos de Sirvoy.")
else:
    print(f"Datos de Sirvoy cargados y limpiados: {len(cleaned_sirvoy_df)} registros.")

    # 3. Filtrar por la reserva en cuestión ANTES de la lógica de unificación
    # El booking_id se extrae en _clean_sirvoy_data
    if 'booking_id_sirvoy' in cleaned_sirvoy_df.columns:
        reserva_id = "42603"
        print(f"\nFiltrando transacciones para la Reserva ID: {reserva_id}")

        reserva_df = cleaned_sirvoy_df[
            cleaned_sirvoy_df['booking_id_sirvoy'].astype(str).str.contains(reserva_id, na=False)
        ]

        if reserva_df.empty:
            print(f"No se encontraron transacciones para la Reserva {reserva_id}.")
        else:
            print(f"Se encontraron {len(reserva_df)} transacciones para la Reserva {reserva_id}:")
            
            # Columnas relevantes para la depuración de la cancelación
            cols_to_show = [
                'sirvoy_transaction_id', 
                'fecha', 
                'payment_method_sirvoy', 
                'monto_eur', 
                'booking_id_sirvoy', 
                'description_sirvoy'
            ]
            
            # Asegurarse de que las columnas existan antes de imprimir
            cols_existentes = [col for col in cols_to_show if col in reserva_df.columns]
            
            print(reserva_df[cols_existentes].to_string())

            # 4. Simular la separación de positivos y negativos que ocurre en unify_data
            positivos = reserva_df[reserva_df['monto_eur'] > 0]
            negativos = reserva_df[reserva_df['monto_eur'] < 0]

            print(f"\nAnálisis para la Reserva {reserva_id}:")
            print(f"  - {len(positivos)} transacciones positivas encontradas.")
            print(f"  - {len(negativos)} transacciones negativas encontradas.")

            if not negativos.empty:
                print("\nDetalle de transacciones negativas:")
                print(negativos[cols_existentes].to_string())
                print("\nEstas transacciones negativas podrían estar cancelando las positivas.")
            else:
                print("No se encontraron transacciones negativas para esta reserva.")

    else:
        print("Error: La columna 'booking_id_sirvoy' no se encontró en el DataFrame limpio.")

print("\nDepuración finalizada.")
