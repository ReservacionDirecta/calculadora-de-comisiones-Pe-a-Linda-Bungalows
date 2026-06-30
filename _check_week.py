import pandas as pd
from pymongo import MongoClient
cli = MongoClient('mongodb://localhost:27017/')
docs = list(cli['pena_linda']['pagos'].find({}, {"fecha":1,"monto":1,"fuente":1}))
df = pd.DataFrame(docs)
df['date'] = pd.to_datetime(df['fecha'], errors='coerce')
df['date_pe'] = df['date'].dt.tz_localize('UTC', ambiguous='NaT').dt.tz_convert('America/Lima')
df['amount'] = pd.to_numeric(df['monto'], errors='coerce')
df = df.dropna(subset=['date_pe'])
fi = pd.Timestamp("2026-06-16").date()
ff = pd.Timestamp("2026-06-22").date()
filt = df[(df['date_pe'].dt.date >= fi) & (df['date_pe'].dt.date <= ff)]
s = filt[filt['fuente']=='Sirvoy']['amount'].sum()
print(f"Sirvoy Dashboard:   S/ {s:,.2f} ({len(filt[filt['fuente']=='Sirvoy'])} docs)")
print(f"Sirvoy Web Export:  S/ 14,493.43")
print(f"Diferencia:         S/ {abs(s - 14493.43):,.2f}")
print(f"✅ COINCIDEN: {abs(s - 14493.43) < 0.01}")
