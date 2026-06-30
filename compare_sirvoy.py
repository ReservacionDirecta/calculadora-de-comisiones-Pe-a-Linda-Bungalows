#!/usr/bin/env python3
"""Compare scraped vs exported Sirvoy data, find negatives."""
import pandas as pd

# File 1: Scraped
df1 = pd.read_csv('secured (1).csv')
print("=== secured (1).csv (scraped) ===")
print(f"Rows: {len(df1)}")
print(f"Columns: {list(df1.columns)}")
print()

# Parse amounts from scraped - text-success and text-error columns
def parse_pen(s):
    s = str(s).strip()
    if not s or s == 'nan':
        return 0.0
    s = s.replace('.', '').replace(',', '.')
    return float(s)

df1['monto_positivo'] = df1['text-success'].apply(parse_pen)
df1['monto_negativo'] = df1['text-error'].apply(parse_pen)
df1['monto'] = df1['monto_positivo'] - abs(df1['monto_negativo'])  # net
df1['neto'] = df1['monto_positivo'] - df1['monto_negativo']

print("\nAll rows (scraped):")
for _, r in df1.iterrows():
    pos = r.get('monto_positivo', 0)
    neg = r.get('monto_negativo', 0)
    method = r.get('align-middle 3', '')
    ref = r.get('align-middle 4', '')
    comment = r.get('align-middle 2', '')
    pid = r.get('align-middle', '')
    print(f"  ID {pid:>8} | {comment} | {method:30s} | Ref: {str(ref):20s} | Pos: S/ {pos:>8.2f} | Neg: S/ {neg:>8.2f}")

# File 2: Exported from Sirvoy
df2 = pd.read_csv('payments_export-2026-06-30_09_44_18.csv')
print("\n\n=== payments_export-2026-06-30_09_44_18.csv (exported) ===")
print(f"Rows: {len(df2)}")
print(f"Columns: {list(df2.columns)}")
print()

def parse_pen2(s):
    try:
        s = str(s).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

df2['monto'] = df2['Amount'].apply(parse_pen2)

# Check for negatives
neg = df2[df2['monto'] < 0].copy()
print(f"** Negative amounts: {len(neg)} **")
for _, r in neg.iterrows():
    pid = r['Payment Id']
    fecha = r['Date']
    method = r.get('Method', '')
    comm = r.get('Comment', '')
    linked = r.get('Linked To', '')
    ref = r.get('Reference', '')
    print(f"  ID {pid} | {fecha} | {method} | Ref: {ref} | Comm: {comm} | Linked: {linked} | S/ {r['monto']:.2f}")

# Positive amounts
pos = df2[df2['monto'] > 0].copy()
print(f"\nPositive amounts: {len(pos)}")
print(f"Total positive: S/ {pos['monto'].sum():,.2f}")
print(f"Total negative: S/ {neg['monto'].sum():,.2f}")

# Compare: find scraped rows in exported by PaymentId
print("\n\n=== Comparación por PaymentId ===")
scraped_ids = set(df1['align-middle'].astype(str).str.strip())
exported_ids = set(df2['Payment Id'].astype(str).str.strip())

print(f"Scraped PaymentIds: {sorted(scraped_ids)}")
print(f"In exported: {scraped_ids.intersection(exported_ids)}")
print(f"Not in exported: {scraped_ids - exported_ids}")
print(f"In exported but not scraped: {len(exported_ids - scraped_ids)} rows")

# For matching IDs, compare amounts
print("\n=== Comparación de montos (mismos IDs) ===")
for _, r1 in df1.iterrows():
    pid = str(r1['align-middle']).strip()
    if pid not in exported_ids:
        continue
    r2 = df2[df2['Payment Id'].astype(str).str.strip() == pid].iloc[0]
    m1 = r1['monto_positivo'] - abs(r1['monto_negativo'])  # net scraped
    m2_value = r2['monto']  # exported
    m2 = m2_value if m2_value > 0 else 0
    scraped_neg = abs(r1['monto_negativo'])
    print(f"  ID {pid:>8} | Scraped: S/ {r1['monto_positivo']:>8.2f} (neg: S/ {scraped_neg:>8.2f}) | Exported: S/ {r2['monto']:>8.2f} | Match: {'✅' if abs(r1['monto_positivo'] - m2_value) < 0.01 else '❌'}")
