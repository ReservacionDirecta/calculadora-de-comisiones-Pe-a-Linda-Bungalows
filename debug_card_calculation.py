import pandas as pd
from data_processor import PaymentDataProcessor
# from pathlib import Path # Ya no es necesario si se carga directamente
# import json # Ya no es necesario si se carga directamente

# Initialize processor
processor = PaymentDataProcessor()

# Cargar datos de las diferentes fuentes directamente
processor.load_izipay_data("izipay 2.csv") # Usar el nuevo archivo
processor.load_culqi_data("culqi 2.csv")   # Usar el nuevo archivo
processor.load_secured_data("secured.csv")
processor.load_sirvoy_data("sirvoy.csv") # Usar sirvoy.csv directamente
processor.load_openpay_data("Openpay.csv") # Cargar Openpay.csv
print('All files loaded directly:')
print(f'Loaded Izipay: {len(processor.izipay_data)} records')
print(f'Loaded Culqi: {len(processor.culqi_data)} records')
print(f'Loaded Secured: {len(processor.secured_data)} records')
print(f'Loaded Sirvoy: {len(processor.sirvoy_data)} records')
print(f'Loaded Openpay: {len(processor.openpay_data)} records')

# Unify data
unified_data = processor.unify_data()
print(f'\nUnified data: {len(unified_data)} records')

# Filter for card payments
card_payments = unified_data[(unified_data['income_type'] == 'Tarjeta') & (unified_data['amount_gross'] > 0)]
print(f'\nCard payments: {len(card_payments)} records')

# Filtrar para el período del 16 al 22 de septiembre para pagos con tarjeta
start_date = pd.to_datetime('2025-09-16')
end_date = pd.to_datetime('2025-09-22')

card_payments_filtered = card_payments[(card_payments['date'] >= start_date) & (card_payments['date'] <= end_date)]

print(f'\nCard payments (16-22 Sept): {len(card_payments_filtered)} records')
if not card_payments_filtered.empty:
    print(f'Card payments (16-22 Sept) total net: S/ {card_payments_filtered["amount_net"].sum():,.2f}')
    print(f'Card payments (16-22 Sept) total gross: S/ {card_payments_filtered["amount_gross"].sum():,.2f}')

# Izipay card payments
izipay_cards = card_payments[card_payments['processor'] == 'Izipay']

# Culqi card payments
culqi_cards = card_payments[card_payments['processor'] == 'Culqi']

# Total received from cards
total_received = izipay_cards['amount_net'].sum() + culqi_cards['amount_net'].sum()
print(f'\nTotal received from cards: S/ {total_received:,.2f}')

# Sirvoy card amounts (reported)
sirvoy_cards = unified_data[(unified_data['processor'] == 'Sirvoy') & (unified_data['income_type'] == 'Tarjeta')]
if not sirvoy_cards.empty:
    sirvoy_reported = sirvoy_cards['amount_reported'].sum()
    print(f'Sirvoy reported card amounts: S/ {sirvoy_reported:,.2f}')
else:
    print('No Sirvoy card data found')

# Check if there are any Sirvoy records at all
sirvoy_all = unified_data[unified_data['processor'] == 'Sirvoy']
print(f'Total Sirvoy records: {len(sirvoy_all)}')
if not sirvoy_all.empty:
    print(f'Sirvoy total amount_reported: S/ {sirvoy_all["amount_reported"].sum():,.2f}')
    print(f'Sirvoy total amount_gross: S/ {sirvoy_all["amount_gross"].sum():,.2f}')

    # Check for positive Sirvoy amounts (income)
    sirvoy_income = sirvoy_all[sirvoy_all['amount_gross'] > 0]
    if not sirvoy_income.empty:
        print(f'Sirvoy INCOME records: {len(sirvoy_income)}')
        print(f'Sirvoy total income: S/ {sirvoy_income["amount_gross"].sum():,.2f}')
    else:
        print('No Sirvoy income records found (all are expenses/costs)')

    # Show sample Sirvoy data
    print('\n=== SAMPLE SIRVOY DATA ===')
    sample_sirvoy = sirvoy_all[['amount_gross', 'amount_reported', 'processor', 'income_type']].head()
    print(sample_sirvoy.to_string())

# Show sample data
print('\n=== SAMPLE IZIPAY CARD DATA ===')
if not izipay_cards.empty:
    sample_izipay = izipay_cards[['amount_gross', 'amount_net', 'processor', 'income_type', 'commission_processor', 'commission_chamba']].head()
    print(sample_izipay.to_string())

    # Check for NaN values in amount_net
    nan_count = izipay_cards['amount_net'].isna().sum()
    print(f'\nIzipay records with NaN amount_net: {nan_count}')

    # Show raw Izipay data before processing
    print('\n=== RAW IZIPAY DATA BEFORE PROCESSING ===')
    if processor.izipay_data is not None and not processor.izipay_data.empty:
        raw_sample = processor.izipay_data[['Importe del pago', 'Comisión']].head()
        print(raw_sample.to_string())

print('\n=== SAMPLE CULQI CARD DATA ===')
if not culqi_cards.empty:
    sample_culqi = culqi_cards[['amount_gross', 'amount_net', 'processor', 'income_type', 'commission_processor', 'commission_chamba']].head()
    print(sample_culqi.to_string())

# Eliminar la llamada a export_unified_data si no es necesaria
# processor.export_unified_data("transacciones_unificadas.csv")
