#!/usr/bin/env python3
"""Encontrar montos de reversiones emparejando por booking ref en scraped."""
import pandas as pd

sc = pd.read_csv('secured (3).csv')
sc['monto'] = pd.to_numeric(sc['text-success'].str.replace('.','',regex=False).str.replace(',','.',regex=False), errors='coerce')
sc['PaymentId'] = sc['align-middle'].astype(str)
sc['fecha'] = pd.to_datetime(sc['align-middle 2'], dayfirst=True, errors='coerce')

# Las 6 reversiones (empty entries) con sus booking refs y métodos
reversions = [
    {'id': '16537235', 'booking': '43824', 'metodo': 'Transferencia bancaria', 'fecha': '08/03/2026 15:25'},
    {'id': '16527665', 'booking': '43851', 'metodo': 'Transferencia bancaria', 'fecha': '06/03/2026 20:07'},
    {'id': '16526948', 'booking': '43806', 'metodo': 'Transferencia bancaria', 'fecha': '06/03/2026 15:52'},
    {'id': '16510139', 'booking': '43813', 'metodo': 'Pago con tarjeta', 'fecha': '03/03/2026 20:01'},
    {'id': '16510135', 'booking': '43814', 'metodo': 'Pago con tarjeta', 'fecha': '03/03/2026 20:00'},
    {'id': '16510109', 'booking': '43817', 'metodo': 'Pago con tarjeta', 'fecha': '03/03/2026 19:50'},
]

print("=" * 80)
print("EMPARENANDO REVERSIONES CON PAGOS ORIGINALES POR BOOKING REF")
print("=" * 80)

total_neg = 0
for rev in reversions:
    print(f"\n📋 Reversión: {rev['id']}  ({rev['fecha']})  {rev['metodo']}  Booking: {rev['booking']}")
    
    # Buscar pagos relacionados con el mismo booking
    bk = rev['booking']
    matches = sc[sc['align-middle 6'].astype(str) == bk]
    
    # Buscar el pago original (positivo, mismo método, más antiguo)
    orig = matches[(sc['monto'] > 0) & (sc['metodo' if 'metodo' in sc.columns else 'align-middle 3'] == rev['metodo'])]
    # Actually just show all
    for _, mr in matches.iterrows():
        m = mr['monto'] if pd.notna(mr['monto']) else 0
        pid = str(mr['PaymentId'])
        mt = str(mr.get('align-middle 3', ''))
        fc = str(mr.get('align-middle 2', ''))
        is_rev = '⚠️ REVERSIÓN' if pid == rev['id'] else ''
        is_orig = '⟵ ORIGINAL?' if (m > 0 and pid != rev['id']) else ''
        print(f"    {pid:>8}  S/ {m:>+8.2f}  {fc:>20}  {mt:30s}  {is_rev} {is_orig}")
    
    # Best guess: the reversion amount = the matching positive payment's amount (same booking, same method, different ID)
    # BUT the original payment for the reversion might be positive AND already in the 140 early positives
    # The reversion is a separate entry with negative of that amount
    # Look for the most likely original: same booking, same method, positive amount, not the reversion itself
    same_bk_method = matches[(sc['align-middle 3'] == rev['metodo']) & (matches['PaymentId'] != rev['id']) & (matches['monto'] > 0)]
    if len(same_bk_method) > 0:
        likely_orig = same_bk_method.iloc[0]
        print(f"    ⟹ MONTO REVERSIÓN ESTIMADO: S/ -{likely_orig['monto']:.2f}")
        total_neg -= likely_orig['monto']
    else:
        # Try any positive payment for same booking
        any_pos = matches[matches['monto'] > 0]
        if len(any_pos) > 0:
            likely = any_pos.iloc[0]
            print(f"    ⟹ MONTO REVERSIÓN ESTIMADO (de otros métodos): S/ -{likely['monto']:.2f}")
            total_neg -= likely['monto']
        else:
            print(f"    ⚠️ NO SE PUEDE DETERMINAR MONTO")
            
print(f"\n{'='*70}")
print(f"TOTAL 6 REVERSIONES: S/ {total_neg:,.2f}")
print(f"Esperado: S/ -1,940.62")
print(f"{'='*70}")
