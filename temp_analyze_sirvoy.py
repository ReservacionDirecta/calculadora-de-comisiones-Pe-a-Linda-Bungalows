import pandas as pd

# Leer archivo Sirvoy para analizar su estructura
df = pd.read_csv('data_persistente/sirvoy_20250930_113408_64218e95.csv')

print(f'Número de columnas: {len(df.columns)}')
print(f'Nombres de columnas: {list(df.columns)}')
print(f'Primeras 3 filas:')
print(df.head(3))
print(f'Tipo de datos de cada columna:')
print(df.dtypes)