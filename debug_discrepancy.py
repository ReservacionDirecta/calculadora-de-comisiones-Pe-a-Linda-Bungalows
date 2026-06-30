import pandas as pd
import logging
from data_processor import PaymentDataProcessor
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_discrepancies():
    processor = PaymentDataProcessor()
    
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        # Redirigir stdout al archivo
        sys.stdout = f
        
        # 0. Ver formato crudo de Culqi
        print("\n--- FORMATO CRUDO CULQI ---")
        try:
            with open('culqi.csv', 'r', encoding='utf-8') as raw_f:
                for i in range(5):
                    print(raw_f.readline().strip())
        except Exception as e:
            print(f"Error leyendo raw culqi.csv: {e}")

        target_start = pd.Timestamp('2025-09-30')
        target_end = pd.Timestamp('2025-10-06 23:59:59')
        
        # 1. Analizar Archivos Potenciales de Culqi
        culqi_candidates = ['Listado_transacciones_capturadas (3).csv']
        
        for c_file in culqi_candidates:
            print(f"\n--- ANALIZANDO CANDIDATO CULQI: {c_file} ---")
            
            # Ver formato crudo
            print("  Primeras 10 líneas crudas:")
            try:
                with open(c_file, 'r', encoding='utf-8') as raw_f:
                    for i in range(10):
                        print(f"    {raw_f.readline().strip()}")
            except Exception as e:
                print(f"    Error leyendo raw: {e}")

            try:
                # Intentar cargar con separador ; (común en Izipay/Culqi exports)
                df_culqi = pd.read_csv(c_file, sep=';', encoding='utf-8')
                
                if len(df_culqi.columns) < 2:
                     # Si falla, intentar con ,
                     df_culqi = pd.read_csv(c_file, sep=',', encoding='utf-8')

                print(f"  Cargado con éxito. Columnas: {list(df_culqi.columns)}")
                print(f"  Total registros: {len(df_culqi)}")
                
                # Normalizar nombres de columnas para búsqueda
                # Buscar columna de monto y fecha
                col_monto = next((c for c in df_culqi.columns if 'monto' in c.lower() or 'importe' in c.lower() or 'amount' in c.lower()), None)
                col_fecha = next((c for c in df_culqi.columns if 'fecha' in c.lower() or 'date' in c.lower()), None)
                col_estado = next((c for c in df_culqi.columns if 'estado' in c.lower() or 'status' in c.lower()), None)
                
                print(f"  Columnas detectadas: Fecha={col_fecha}, Monto={col_monto}, Estado={col_estado}")

                if col_monto and col_fecha:
                    # Convertir monto
                    df_culqi[col_monto] = pd.to_numeric(df_culqi[col_monto].astype(str).str.replace(',', '.'), errors='coerce')
                    
                    # Convertir fecha
                    df_culqi['datetime'] = pd.to_datetime(df_culqi[col_fecha], dayfirst=True, errors='coerce')
                    
                    # Filtrar rango
                    mask = (df_culqi['datetime'] >= target_start) & (df_culqi['datetime'] <= target_end)
                    df_range = df_culqi[mask]
                    
                    total_range = df_range[col_monto].sum()
                    print(f"  Total en rango ({target_start.date()} - {target_end.date()}): S/ {total_range:,.2f}")
                    
                    print("  Transacciones en rango:")
                    for idx, row in df_range.iterrows():
                        print(f"    {row['datetime']} | {row[col_monto]} | {row.get(col_estado, 'N/A')}")
                    
                    # Buscar monto de diferencia (152.60)
                    diff_amount = 152.60
                    print(f"\n  Buscando monto exacto {diff_amount} en TODO el archivo:")
                    df_diff = df_culqi[df_culqi[col_monto].between(diff_amount - 0.01, diff_amount + 0.01)]
                    for idx, row in df_diff.iterrows():
                        print(f"    ENCONTRADO: {row['datetime']} | {row[col_monto]} | {row.get(col_estado, 'N/A')}")

            except Exception as e:
                print(f"Error analizando {c_file}: {e}")

        # 2. Analizar Openpay
        print("\n--- ANALIZANDO OPENPAY ---")
        openpay_files = ['Openpay.csv', 'openpay copy.csv']
        
        for file in openpay_files:
            print(f"\nLeyendo archivo: {file}")
            try:
                df_openpay = processor.load_openpay_data(file)
                if df_openpay.empty:
                    print("  Archivo vacío.")
                    continue
                    
                # Filtrar rango
                # Asegurar que 'date' sea datetime
                df_openpay['date'] = pd.to_datetime(df_openpay['date'])
                mask = (df_openpay['date'] >= target_start) & (df_openpay['date'] <= target_end)
                df_range = df_openpay[mask]
                
                total_range = df_range['amount'].sum()
                print(f"  Total en rango ({target_start.date()} - {target_end.date()}): S/ {total_range:,.2f}")
                
                print("  Transacciones en rango:")
                for idx, row in df_range.iterrows():
                    print(f"    {row['date']} | {row['amount']} | {row.get('status', 'N/A')}")
                
                # Buscar monto de diferencia (561.03)
                diff_amount = 561.03
                print(f"\n  Buscando monto exacto {diff_amount} en TODO el archivo:")
                df_diff = df_openpay[df_openpay['amount'].between(diff_amount - 0.01, diff_amount + 0.01)]
                for idx, row in df_diff.iterrows():
                    print(f"    ENCONTRADO: {row['date']} | {row['amount']} | {row.get('status', 'N/A')}")

            except Exception as e:
                print(f"  Error leyendo {file}: {e}")
        
        # Restaurar stdout
        sys.stdout = sys.__stdout__

if __name__ == "__main__":
    analyze_discrepancies()
