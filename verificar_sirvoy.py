import pandas as pd
import io

# Leer el archivo directamente
with open('payments_export-2025-11-27_17_29_18.csv', 'rb') as f:
    content = f.read()

# Intentar leer con diferentes codificaciones
for enc in ['utf-8', 'latin1', 'cp1252']:
    try:
        df = pd.read_csv(io.BytesIO(content), encoding=enc, header=0)
        print(f"Codificación {enc}: OK")
        print(f"Columnas: {list(df.columns)}")
        print(f"Filas: {len(df)}")
        print(f"\nPrimeras 2 filas:")
        print(df.head(2))
        print(f"\nVerificando detección:")
        print(f"'Payment Id' in columns: {'Payment Id' in df.columns}")
        print(f"'Date' in columns: {'Date' in df.columns}")
        print(f"'Amount' in columns: {'Amount' in df.columns}")
        break
    except Exception as e:
        print(f"Error con {enc}: {e}")


