
import pandas as pd
import re
import io

# --- Funciones de limpieza mínimas requeridas ---

def convert_amount(amt_str):
    """Convierte montos en formato europeo (ej: '1.234,56' o '230,00') a float."""
    if pd.isna(amt_str):
        return 0.0
    amt_str = str(amt_str).strip().replace('"', '')
    # Si tiene punto Y coma, es formato europeo completo
    if '.' in amt_str and ',' in amt_str:
        amt_str = amt_str.replace('.', '').replace(',', '.')
    # Si solo tiene coma, es formato europeo simple
    elif ',' in amt_str:
        amt_str = amt_str.replace(',', '.')
    try:
        return float(amt_str)
    except ValueError:
        return 0.0

def get_booking_id(linked_to_str):
    """Extrae el ID de la reserva (ej: 'Reserva 42603' -> '42603')."""
    if pd.isna(linked_to_str):
        return ''
    match = re.search(r'Reserva\s+(\d+)', str(linked_to_str))
    if match:
        return match.group(1)
    return ''

# --- Script principal ---

print("Iniciando script de verificación de cancelación...")

csv_file = 'payments_export-2025-11-29_10_18_40.csv'
reserva_id_objetivo = "42603"

try:
    # Leer el archivo CSV de forma robusta
    content = None
    with open(csv_file, 'rb') as f:
        content = f.read()

    df = pd.read_csv(io.BytesIO(content), sep=',', encoding='utf-8')
    print(f"Archivo CSV '{csv_file}' leído exitosamente. {len(df)} filas encontradas.")

    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.replace('"', '')

    # Aplicar limpieza a las columnas necesarias
    df['Amount_numeric'] = df['Amount'].apply(convert_amount)
    df['booking_id'] = df['Linked To'].apply(get_booking_id)
    df['Method_clean'] = df['Method'].str.strip()

    # Filtrar por el ID de la reserva
    reserva_df = df[df['booking_id'] == reserva_id_objetivo].copy()

    if reserva_df.empty:
        print(f"Error: No se encontraron transacciones para la Reserva ID: {reserva_id_objetivo}")
    else:
        print(f"\nSe encontraron {len(reserva_df)} transacciones para la Reserva ID {reserva_id_objetivo}:")
        
        cols_to_show = [
            'Payment Id', 
            'Date', 
            'Method_clean', 
            'Amount_numeric', 
            'booking_id', 
            'Linked To',
            'Comment'
        ]
        print(reserva_df[cols_to_show].to_string())

        # Análisis de positivos y negativos
        positivos = reserva_df[reserva_df['Amount_numeric'] > 0]
        negativos = reserva_df[reserva_df['Amount_numeric'] < 0]

        print(f"\nAnálisis para la Reserva {reserva_id_objetivo}:")
        print(f"  - {len(positivos)} transacciones POSITIVAS por un total de: {positivos['Amount_numeric'].sum():.2f}")
        print(f"  - {len(negativos)} transacciones NEGATIVAS por un total de: {negativos['Amount_numeric'].sum():.2f}")
        print(f"  - NETO para esta reserva: {reserva_df['Amount_numeric'].sum():.2f}")

        if not negativos.empty:
            print("\n¡HIPÓTESIS CONFIRMADA!")
            print("Se encontró al menos una transacción negativa para esta reserva.")
            print("Es muy probable que la lógica de cancelación en 'data_processor.py' esté usando la transacción negativa para anular la positiva de 230.00.")
        else:
            print("\nHipótesis no confirmada. No hay transacciones negativas para esta reserva.")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo '{csv_file}'.")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")

print("\nVerificación finalizada.")
