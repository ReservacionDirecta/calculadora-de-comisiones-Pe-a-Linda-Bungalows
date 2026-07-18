"""
Script para importar los 4 archivos CSV de Sirvoy correspondientes al período del 01/01/2026 al 08/07/2026.
Los archivos a procesar son:
- payments_export-2026-07-08_19_47_57.csv (Ene-Feb)
- payments_export-2026-07-08_19_48_15.csv (Mar-Abr)
- payments_export-2026-07-08_19_48_33.csv (May-Jun)
- payments_export-2026-07-08_19_48_54.csv (Julio)

Pasos:
1. Eliminar todos los registros de la fuente 'Sirvoy' que estén en el rango del 01/01/2026 al 08/07/2026.
2. Leer y parsear secuencialmente cada uno de los 4 archivos.
3. Insertarlos en MongoDB usando hashes únicos.
"""
from pymongo import MongoClient
import pandas as pd
import hashlib
from datetime import datetime
import json
import os

MONGO_URL = "mongodb://localhost:27017"
cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = cli['pena_linda']
col = db['pagos']

FECHA_LIM_MIN = datetime(2026, 1, 1)
FECHA_LIM_MAX = datetime(2026, 7, 8, 23, 59, 59)

# 1. Eliminar Sirvoy del período en MongoDB
print("=== 1. Limpiando base de datos de registros Sirvoy en 2026 ===")
res_del = col.delete_many({
    'fuente': 'Sirvoy',
    'fecha': {'$gte': FECHA_LIM_MIN, '$lte': FECHA_LIM_MAX}
})
print(f"Se eliminaron {res_del.deleted_count} registros Sirvoy antiguos de 2026.")

def parse_amount(s):
    if pd.isna(s):
        return 0.0
    s = str(s).strip().replace('S/', '').replace(' ', '')
    if ',' in s and '.' in s:
        if s.index('.') < s.index(','):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def parse_date(s):
    for fmt in ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d']:
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except:
            continue
    return None

files_to_import = [
    "payments_export-2026-07-08_19_47_57.csv",
    "payments_export-2026-07-08_19_48_15.csv",
    "payments_export-2026-07-08_19_48_33.csv",
    "payments_export-2026-07-08_19_48_54.csv"
]

total_inserted = 0
total_bruto = 0.0
total_neto = 0.0

# 2. Iterar sobre cada archivo e importar
for fpath in files_to_import:
    if os.path.exists(fpath):
        print(f"\n=== Procesando: {fpath} ===")
        df = pd.read_csv(fpath)
        print(f"Filas en archivo: {len(df)}")
        
        file_inserted = 0
        file_skipped = 0
        
        for _, row in df.iterrows():
            pid = str(row.get('Payment Id', '')).strip()
            date_raw = row.get('Date', '')
            dt = parse_date(date_raw)
            amt = parse_amount(row.get('Amount', '0'))
            method = str(row.get('Method', '')).strip()
            comment = str(row.get('Comment', '')).strip()
            ref = str(row.get('Reference', '')).strip()
            linked = str(row.get('Linked To', '')).strip()
            
            if not dt or not pid:
                continue
                
            # Validar rango de fechas
            if dt < FECHA_LIM_MIN or dt > FECHA_LIM_MAX:
                file_skipped += 1
                continue
                
            # Determinar tipo
            m_lower = method.lower()
            if amt < 0:
                tipo = 'Reversion'
            elif any(w in m_lower for w in ['card', 'tarj', 'visa', 'master', 'amex', 'diners']):
                tipo = 'Tarjeta'
            elif any(w in m_lower for w in ['transferencia', 'transf']):
                tipo = 'Transferencia'
            elif any(w in m_lower for w in ['efectivo', 'cash']):
                tipo = 'Efectivo'
            else:
                tipo = 'Tarjeta'
                
            h = hashlib.md5(f'sirvoy_{pid}'.encode()).hexdigest()
            
            meta = {'PaymentId': pid}
            if amt < 0:
                meta['Motivo'] = 'Devolucion/Reversion'
                
            doc = {
                'fuente': 'Sirvoy',
                'fecha': dt,
                'monto': amt,
                'moneda': 'PEN',
                'metodo': method,
                'categoria': 'Venta',
                'tipo_pago': tipo,
                'es_link': 'link' in comment.lower() or 'link' in ref.lower(),
                'estado_deposito': 'depositado',
                'metadata': json.dumps(meta),
                'hash': h,
                '_cargado': datetime.now()
            }
            
            try:
                col.insert_one(doc)
                file_inserted += 1
                total_inserted += 1
                total_neto += amt
                if amt > 0:
                    total_bruto += amt
            except errors.DuplicateKeyError:
                file_skipped += 1
                
        print(f"Resultado -> Insertados: {file_inserted}, Saltados/Duplicados: {file_skipped}")
    else:
        print(f"No se encontró el archivo: {fpath}")

print("\n=== RESUMEN FINAL ===")
print(f"Total Registros Sirvoy 2026 Insertados: {total_inserted}")
print(f"Total Bruto Calculado: S/ {total_bruto:,.2f}")
print(f"Total Neto Calculado:  S/ {total_neto:,.2f}")

cli.close()
