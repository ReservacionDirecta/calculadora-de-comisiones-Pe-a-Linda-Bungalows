import pandas as pd

# Leer el CSV
df = pd.read_csv('payments_export-2025-11-29_10_18_40.csv')

# Filtrar solo transferencias bancarias y efectivo
df_filtered = df[df['Method'].isin(['Transferencia bancaria', 'Efectivo'])]

print(f"Total registros (Transferencia + Efectivo): {len(df_filtered)}")

# Convertir Amount a numérico
def convert_amount(amt_str):
    amt_str = str(amt_str).replace('"', '').strip()
    # Formato europeo: punto para miles, coma para decimales
    if ',' in amt_str and '.' in amt_str:
        amt_str = amt_str.replace('.', '').replace(',', '.')
    elif ',' in amt_str:
        amt_str = amt_str.replace(',', '.')
    return float(amt_str)

df_filtered['Amount_numeric'] = df_filtered['Amount'].apply(convert_amount)

# Separar positivos y negativos
positivos = df_filtered[df_filtered['Amount_numeric'] > 0]
negativos = df_filtered[df_filtered['Amount_numeric'] < 0]

print(f"\nPositivos: {len(positivos)}")
print(f"Negativos: {len(negativos)}")

total_positivos = positivos['Amount_numeric'].sum()
total_negativos = negativos['Amount_numeric'].sum()

print(f"\nTotal positivos: S/ {total_positivos:,.2f}")
print(f"Total negativos: S/ {total_negativos:,.2f}")
print(f"Neto: S/ {total_positivos + total_negativos:,.2f}")

# Buscar la transacción de 230.00
transaccion_230 = df_filtered[df_filtered['Amount_numeric'] == 230.00]
print(f"\n¿Transacción de S/ 230.00 encontrada? {len(transaccion_230) > 0}")
if len(transaccion_230) > 0:
    print(transaccion_230[['Payment Id', 'Date', 'Method', 'Linked To', 'Amount']])

# Verificar reserva 42603
reserva_42603 = df_filtered[df_filtered['Linked To'].str.contains('42603', na=False)]
print(f"\nTransacciones de Reserva 42603:")
print(reserva_42603[['Payment Id', 'Date', 'Method', 'Amount', 'Amount_numeric']])
print(f"Total Reserva 42603: S/ {reserva_42603['Amount_numeric'].sum():,.2f}")
