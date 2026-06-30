import csv
from datetime import datetime
from pymongo import MongoClient
import hashlib

MONGO_URL = "mongodb://localhost:27017"

payments = []
with open(r'C:\Users\yerct\Downloads\qbo.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 6:
            continue
        date_str, tipo, ref, amt1, amt2, status = row[0], row[1], row[2], row[3], row[4], row[5]
        
        def parse_amt(s):
            if not s: return 0
            s = s.replace('S/', '').replace(',', '').replace(' ', '')
            try:
                return float(s)
            except:
                return 0
        
        try:
            fecha = datetime.strptime(date_str.strip(), '%d/%m/%y')
        except:
            try:
                fecha = datetime.strptime(date_str.strip(), '%d/%m/%Y')
            except:
                continue
        
        if 'Pago' in tipo:
            monto = parse_amt(amt2)
            payments.append({
                'fecha': fecha,
                'ref': ref,
                'monto': monto,
                'estado': status
            })

print(f"Total pagos a importar: {len(payments)}")
print(f"Monto total: S/ {sum(p['monto'] for p in payments):,.2f}")

# Conectar a MongoDB
cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = cli['pena_linda']

inserted = 0
skipped = 0

for p in payments:
    # Generar hash para deduplicación
    raw = f"QBO_ABONO|{p['fecha'].strftime('%Y-%m-%d')}|{p['monto']}|{p['ref']}"
    h = hashlib.md5(raw.encode()).hexdigest()
    
    # Verificar si ya existe
    existing = db.pagos.find_one({'hash': h})
    if existing:
        skipped += 1
        continue
    
    doc = {
        'fuente': 'Abono Chamba',
        'fecha': p['fecha'],
        'monto': p['monto'],
        'moneda': 'PEN',
        'metodo': p['ref'],
        'tipo_pago': 'Abono',
        'categoria': 'Abono',
        'hash': h,
        '_cargado': datetime.now(),
        'origen_importacion': 'QuickBooks'
    }
    
    try:
        db.pagos.insert_one(doc)
        inserted += 1
    except Exception as e:
        if 'duplicate key' in str(e).lower():
            skipped += 1
        else:
            print(f"Error insertando {p['ref']}: {e}")

cli.close()
print(f"\n✅ Insertados: {inserted}")
print(f"⏭️  Omitidos (duplicados): {skipped}")