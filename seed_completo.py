#!/usr/bin/env python3
"""
Seed COMPLETO — Pena Linda Bungalows
Carga TODAS las fuentes historicas a MongoDB con deduplicacion.
"""
import pandas as pd, os, sys, warnings, hashlib
from datetime import datetime
from pymongo import MongoClient, errors
warnings.filterwarnings('ignore')

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
from data_processor import PaymentDataProcessor
p = PaymentDataProcessor()

client = MongoClient('mongodb://localhost:27017/')
db = client['pena_linda']
collection = db['pagos']

collection.create_index('hash', unique=True, background=True)
collection.create_index('fecha')
collection.create_index('fuente')

# Clear old Sirvoy payments to ensure clean state
print("Limpiando registros antiguos de Sirvoy...")
collection.delete_many({'fuente': 'Sirvoy'})

def parse_amount(val):
    if pd.isna(val): 
        return 0.0
    val_str = str(val).strip()
    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

def gh(doc):
    raw = f"{doc['fuente']}|{doc.get('transaction_id','')}|{doc.get('fecha','')}|{doc.get('monto',0)}|{doc.get('metodo','')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def insertar(docs, nombre):
    ins, dup, err = 0, 0, 0
    for d in docs:
        d['hash'] = gh(d); d['_cargado'] = datetime.now()
        try: collection.insert_one(d); ins += 1
        except errors.DuplicateKeyError: dup += 1
        except: err += 1
    print(f"  {nombre:<20} {ins:>4} nuevos, {dup:>4} duplicados, {err:>4} errores")
    return ins

print("\n" + "="*55)
print("SEED COMPLETO — Pena Linda Bungalows")
print("="*55)

total = 0

# ═══ 1. SIRVOY OFFICIAL EXPORTS FOR 2026 ═══
print("\n1. SIRVOY (2026 Official Exports)")
sirvoy_2026_files = [
    ('payments_export-2026-06-23_17_10_40.csv', 'Sirvoy Ene-Feb 2026'),
    ('payments_export-2026-06-23_17_11_07.csv', 'Sirvoy Mar-Abr 2026'),
    ('payments_export-2026-06-23_17_11_27.csv', 'Sirvoy May-Jun 2026')
]

for csv_name, label in sirvoy_2026_files:
    filepath = os.path.join(CARPETA, csv_name)
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, encoding='utf-8')
        df['amount'] = df['Amount'].apply(parse_amount)
        df['date_parsed'] = pd.to_datetime(df['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
        df = df.dropna(subset=['date_parsed'])
        docs = []
        for _, r in df.iterrows():
            m = str(r['Method']).lower()
            t = next((x for x in [('tarjeta','Tarjeta'),('card','Tarjeta'),('transferencia','Transferencia'),('transf','Transferencia'),('efectivo','Efectivo'),('cash','Efectivo')] if x[0] in m), ('Otros','Otros'))[1]
            ref_str = str(r.get('Reference', ''))
            comm_str = str(r.get('Comment', ''))
            is_lk = 'link' in ref_str.lower() or 'link' in comm_str.lower()
            docs.append({
                'fuente': 'Sirvoy',
                'transaction_id': str(int(r['Payment Id'])) if pd.notna(r['Payment Id']) else '',
                'fecha': r['date_parsed'],
                'monto': float(r['amount']),
                'metodo': str(r['Method']),
                'tipo_pago': t,
                'es_link': is_lk
            })
        total += insertar(docs, label)
    else:
        print(f"  ⚠️ File not found: {csv_name}")

# ═══ 2b. SIRVOY OCT-ENE (secured 3 - Oct 2025 a Ene 2026) ═══
try:
    df3 = pd.read_csv(os.path.join(CARPETA, 'secured (3).csv'), encoding='utf-8')
    df3 = df3.rename(columns={'align-middle':'payment_id','align-middle href':'url','align-middle 2':'date',
        'align-middle 3':'method','align-middle 4':'reference','align-middle 5':'linked_type',
        'align-middle 6':'linked_id','text-success':'amount_raw'})
    df3['amount'] = df3['amount_raw'].apply(parse_amount)
    df3['date_parsed'] = pd.to_datetime(df3['date'], format='%d/%m/%Y %H:%M', errors='coerce')
    df3 = df3.dropna(subset=['date_parsed'])
    docs = []
    for _, r in df3.iterrows():
        m = str(r['method']).lower()
        t = next((x for x in [('tarjeta','Tarjeta'),('card','Tarjeta'),('transferencia','Transferencia'),('transf','Transferencia'),('efectivo','Efectivo'),('cash','Efectivo')] if x[0] in m), ('Otros','Otros'))[1]
        docs.append({'fuente':'Sirvoy','transaction_id':str(r['payment_id']),'fecha':r['date_parsed'],
            'monto':float(r['amount']),'metodo':str(r['method']),'tipo_pago':t,
            'es_link':'link' in str(r.get('reference','')).lower()})
    total += insertar(docs, 'Sirvoy Oct-Ene')
except Exception as e:
    print(f"  Sirvoy Oct-Ene: ERROR {e}")

# ═══ 2c. SIRVOY JUL-SEP (payments_export - Jul a Sep 2025) ═══
try:
    df4 = pd.read_csv(os.path.join(CARPETA, 'payments_export-2026-06-23_11_07_38.csv'), encoding='utf-8')
    df4['date_parsed'] = pd.to_datetime(df4['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
    df4['amount'] = df4['Amount'].apply(parse_amount)
    df4 = df4.dropna(subset=['date_parsed'])
    docs = []
    for _, r in df4.iterrows():
        m = str(r['Method']).lower()
        t = next((x for x in [('tarjeta','Tarjeta'),('card','Tarjeta'),('transferencia','Transferencia'),('transf','Transferencia'),('efectivo','Efectivo'),('cash','Efectivo')] if x[0] in m), ('Otros','Otros'))[1]
        docs.append({'fuente':'Sirvoy','transaction_id':str(r['Payment Id']),'fecha':r['date_parsed'],
            'monto':float(r['amount']),'metodo':str(r['Method']),'tipo_pago':t,
            'es_link':'link' in str(r.get('Comment','')).lower()})
    total += insertar(docs, 'Sirvoy Jul-Sep')
except Exception as e:
    print(f"  Sirvoy Jul-Sep: ERROR {e}")

# ═══ 2d. SIRVOY MAR-JUN (payments_export - Mar a Jun 2025) ═══
try:
    df5 = pd.read_csv(os.path.join(CARPETA, 'payments_export-2026-06-23_11_10_17.csv'), encoding='utf-8')
    df5['date_parsed'] = pd.to_datetime(df5['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
    df5['amount'] = df5['Amount'].apply(parse_amount)
    df5 = df5.dropna(subset=['date_parsed'])
    docs = []
    for _, r in df5.iterrows():
        m = str(r['Method']).lower()
        t = next((x for x in [('tarjeta','Tarjeta'),('card','Tarjeta'),('transferencia','Transferencia'),('transf','Transferencia'),('efectivo','Efectivo'),('cash','Efectivo')] if x[0] in m), ('Otros','Otros'))[1]
        docs.append({'fuente':'Sirvoy','transaction_id':str(r['Payment Id']),'fecha':r['date_parsed'],
            'monto':float(r['amount']),'metodo':str(r['Method']),'tipo_pago':t,
            'es_link':'link' in str(r.get('Comment','')).lower()})
    total += insertar(docs, 'Sirvoy Mar-Jun')
except Exception as e:
    print(f"  Sirvoy Mar-Jun: ERROR {e}")

# ═══ 2e. SIRVOY ENE-MAR (payments_export - Ene a Mar 2025) ═══
try:
    df6 = pd.read_csv(os.path.join(CARPETA, 'payments_export-2026-06-23_11_10_42.csv'), encoding='utf-8')
    df6['date_parsed'] = pd.to_datetime(df6['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
    df6['amount'] = df6['Amount'].apply(parse_amount)
    df6 = df6.dropna(subset=['date_parsed'])
    docs = []
    for _, r in df6.iterrows():
        m = str(r['Method']).lower()
        t = next((x for x in [('tarjeta','Tarjeta'),('card','Tarjeta'),('transferencia','Transferencia'),('transf','Transferencia'),('efectivo','Efectivo'),('cash','Efectivo')] if x[0] in m), ('Otros','Otros'))[1]
        docs.append({'fuente':'Sirvoy','transaction_id':str(r['Payment Id']),'fecha':r['date_parsed'],
            'monto':float(r['amount']),'metodo':str(r['Method']),'tipo_pago':t,
            'es_link':'link' in str(r.get('Comment','')).lower()})
    total += insertar(docs, 'Sirvoy Ene-Mar')
except Exception as e:
    print(f"  Sirvoy Ene-Mar: ERROR {e}")

# ═══ 3. IZIPAY HISTORICO (560 reg, Ene-Sep 2025) ═══
print("\n2. IZIPAY")
try:
    iz = pd.read_csv(os.path.join(CARPETA, 'izipay.csv'), sep=';', encoding='utf-8')
    iz['fecha'] = pd.to_datetime(iz['Fecha del pago'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    iz['monto'] = pd.to_numeric(iz['Importe del pago'], errors='coerce')
    iz = iz.dropna(subset=['fecha','monto'])
    docs = [{'fuente':'Izipay','transaction_id':str(r.get('Transaccion UUID','')),'fecha':r['fecha'],
        'monto':float(r['monto']),'metodo':str(r.get('Medio de pago','')),'tipo_pago':'Tarjeta',
        'moneda':'PEN','comision':float(r.get('Comision',0)),'comprador':str(r.get('Comprador','')),
        'tarjeta':str(r.get('Numero de tarjeta','')),'es_link':False} for _,r in iz.iterrows()]
    total += insertar(docs, 'Izipay Historico')
except Exception as e: print(f"  Izipay Historico: ERROR {e}")

# ═══ 4. IZIPAY CAPTURADAS (140 reg) ═══
try:
    izc = pd.read_csv(os.path.join(CARPETA, 'Listado_transacciones_capturadas-izipay.csv'), sep=';', encoding='utf-8')
    izc['fecha'] = pd.to_datetime(izc['Fecha del pago'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    izc['monto'] = pd.to_numeric(izc['Importe del pago'], errors='coerce')
    izc = izc.dropna(subset=['fecha','monto'])
    docs = [{'fuente':'Izipay','transaction_id':'','fecha':r['fecha'],'monto':float(r['monto']),
        'metodo':str(r.get('Medio de pago','')),'tipo_pago':'Tarjeta','moneda':'PEN',
        'comision':float(r.get('Comision',0)),'es_link':False} for _,r in izc.iterrows()]
    total += insertar(docs, 'Izipay Capturadas')
except Exception as e: print(f"  Izipay Capturadas: ERROR {e}")

# ═══ 5. IZIPAY USD (9 reg) ═══
try:
    izu = pd.read_csv(os.path.join(CARPETA, 'izipay_22may_22jun_2026.csv'), sep=';', encoding='utf-8')
    # Also load izipay_usd.csv (older - more records)
    try:
        izu_old = pd.read_csv(os.path.join(CARPETA, 'izipay_usd.csv'), sep=';', encoding='utf-8')
        izu = pd.concat([izu, izu_old], ignore_index=True)
    except: pass
    col_m = 'Monto del pago' if 'Monto del pago' in izu.columns else 'Importe del pago'
    izu['fecha'] = pd.to_datetime(izu['Fecha del pago'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    izu['monto'] = pd.to_numeric(izu[col_m], errors='coerce')
    izu = izu.dropna(subset=['fecha','monto'])
    docs = [{'fuente':'Izipay','transaction_id':'','fecha':r['fecha'],'monto':float(r['monto']),
        'metodo':str(r.get('Medio de pago','')),'tipo_pago':'Tarjeta','moneda':'USD',
        'comprador':str(r.get('Comprador','')),'es_link':False} for _,r in izu.iterrows()]
    total += insertar(docs, 'Izipay USD')
except Exception as e: print(f"  Izipay USD: ERROR {e}")

# ═══ 6. CULQI HISTORICO (434 reg) ═══
print("\n3. CULQI")
try:
    cq = pd.read_csv(os.path.join(CARPETA, 'culqi.csv'), encoding='utf-8')
    cq['fecha'] = pd.to_datetime(cq['Fecha de la transaccion'], format='%Y-%m-%d', errors='coerce')
    cq['monto'] = pd.to_numeric(cq['Monto VENTA'], errors='coerce')
    cq = cq.dropna(subset=['fecha','monto'])
    docs = [{'fuente':'Culqi','transaction_id':str(r.get('ID Venta','')),'fecha':r['fecha'],
        'monto':float(r['monto']),'metodo':str(r.get('Marca','')),'tipo_pago':'Tarjeta',
        'comision_culqi':float(r.get('Comision Culqi',0)),
        'comision_total':float(r.get('Comision TOTAL',0)),
        'card_last4':str(r.get('Ult. 4 digitos','')),'comprador':str(r.get('Nombres','')),
        'estado':str(r.get('Estado','')),'es_link':False} for _,r in cq.iterrows()]
    total += insertar(docs, 'Culqi Historico')
except Exception as e: print(f"  Culqi Historico: ERROR {e}")

# ═══ 7. CULQI VENTAS (138 reg) ═══
try:
    cv = pd.read_csv(os.path.join(CARPETA, 'ventasculqi.csv'), encoding='utf-8')
    cv['fecha'] = pd.to_datetime(cv['Fecha de la transaccion'], format='%Y-%m-%d', errors='coerce')
    cv['monto'] = pd.to_numeric(cv['Monto VENTA'], errors='coerce')
    cv = cv.dropna(subset=['fecha','monto'])
    docs = [{'fuente':'Culqi','transaction_id':str(r.get('ID Venta','')),'fecha':r['fecha'],
        'monto':float(r['monto']),'metodo':str(r.get('Marca','')),'tipo_pago':'Tarjeta',
        'comision_culqi':float(r.get('Comision Culqi',0)),
        'card_last4':str(r.get('Ult. 4 digitos','')),'es_link':False} for _,r in cv.iterrows()]
    total += insertar(docs, 'Culqi Ventas')
except Exception as e: print(f"  Culqi Ventas: ERROR {e}")

# ═══ 8. OPENPAY HISTORICO (130 reg, nuevo formato) ═══
print("\n4. OPENPAY")
try:
    op = pd.read_csv(os.path.join(CARPETA, 'openpay copy.csv'), encoding='latin1')
    # Amount conversion
    def conv(m):
        try: return float(str(m).replace(',','.').replace('"',''))
        except: return 0.0
    op['monto'] = op['amount'].apply(conv) if 'amount' in op.columns else 0
    if 'creation_date' in op.columns:
        op['fecha'] = pd.to_datetime(op['creation_date'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    else: op['fecha'] = None
    op = op.dropna(subset=['fecha'])
    op = op[op['monto'] > 0]
    docs = [{'fuente':'Openpay','transaction_id':str(r.get('transaction_id','')),'fecha':r['fecha'],
        'monto':float(r['monto']),'metodo':'Tarjeta','tipo_pago':'Tarjeta',
        'fee':float(r.get('fee',0)),'fee_tax':float(r.get('fee_tax',0)),
        'card_last4':str(r.get('card_number',''))[-4:],'es_link':False} for _,r in op.iterrows()]
    total += insertar(docs, 'Openpay')
except Exception as e: print(f"  Openpay: ERROR {e}")

# ═══ 9b. OPENPAY TIMESTAMP (nuevos archivos con patrón YYYYMMDD-HHMMSS-UUID) ═══
openpay_ts_files = [
    ('20251129-140444ac4a3dc0-0046-4ceb-8ae5-5f7042f1a551.csv', 'Openpay Oct 2025'),
    ('20260530-172659a30c9a73-8dbf-40d2-86df-3a279a204277.csv', 'Openpay Mar 2026'),
]
for ts_file, ts_name in openpay_ts_files:
    try:
        op_ts = pd.read_csv(os.path.join(CARPETA, ts_file), encoding='latin1')
        def conv(m):
            try: return float(str(m).replace(',','.').replace('"',''))
            except: return 0.0
        op_ts['monto'] = op_ts['amount'].apply(conv) if 'amount' in op_ts.columns else 0
        if 'creation_date' in op_ts.columns:
            op_ts['fecha'] = pd.to_datetime(op_ts['creation_date'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        else: op_ts['fecha'] = None
        op_ts = op_ts.dropna(subset=['fecha'])
        op_ts = op_ts[op_ts['monto'] > 0]
        docs = [{'fuente':'Openpay','transaction_id':str(r.get('transaction_id','')),'fecha':r['fecha'],
            'monto':float(r['monto']),'metodo':'Tarjeta','tipo_pago':'Tarjeta',
            'fee':float(r.get('fee',0).replace(",",".").replace('"','')) if isinstance(r.get('fee',0), str) else float(r.get('fee',0)),
            'card_last4':str(r.get('card_number',''))[-4:],'es_link':False} for _,r in op_ts.iterrows()]
        total += insertar(docs, ts_name)
    except Exception as e:
        print(f"  {ts_name}: ERROR {e}")

# ═══ 10. OPENPAY ANTIGUO (47 reg, odd/even) ═══
try:
    op_old = pd.read_csv(os.path.join(CARPETA, 'Openpay.csv'), encoding='latin1', 
                         names=['odd','odd 2','odd 3','even','even 2','even 3'], header=0)
    for _, row in op_old.iterrows():
        docs = []
        for prefix in ['odd','even']:
            if pd.notna(row[prefix]) and pd.notna(row[f'{prefix} 2']) and pd.notna(row[f'{prefix} 3']):
                ds = str(row[prefix]).replace('.','').replace(',','')
                try:
                    fecha = pd.to_datetime(ds, format='%d %b %Y %H:%M:%S', errors='coerce')
                    monto = float(str(row[f'{prefix} 3']).replace('S/','').replace(' ','').replace(',',''))
                    docs.append({'fuente':'Openpay','fecha':fecha,'monto':monto,'metodo':'Tarjeta',
                        'tipo_pago':'Tarjeta','card_last4':str(row[f'{prefix} 2'])[-4:],'es_link':False})
                except: pass
        if docs: total += insertar(docs, 'Openpay Antiguo')
except Exception as e: print(f"  Openpay Antiguo: ERROR {e}")

# ═══ RESUMEN ═══
print(f"\n{'='*55}")
print(f"RESUMEN FINAL")
print(f"{'='*55}")
total_db = collection.count_documents({})
print(f"Total en MongoDB: {total_db:,} documentos")
print()
print("Por fuente:")
for f in sorted(collection.distinct('fuente')):
    cant = collection.count_documents({'fuente': f})
    try:
        mont = list(collection.aggregate([{'$match':{'fuente':f}},{'$group':{'_id':None,'s':{'$sum':'$monto'}}}]))
        print(f"  {f:<20} {cant:>6} docs  S/ {mont[0]['s']:>10,.2f}" if mont else f"  {f:<20} {cant:>6} docs")
    except: print(f"  {f:<20} {cant:>6} docs")

print("\nPor tipo:")
for t in sorted(collection.distinct('tipo_pago')):
    cant = collection.count_documents({'tipo_pago': t})
    print(f"  {t:<20} {cant:>6} docs")

links = collection.count_documents({'es_link': True})
try:
    lm = list(collection.aggregate([{'$match':{'es_link':True}},{'$group':{'_id':None,'s':{'$sum':'$monto'}}}]))
    print(f"\nLinks de Pago: {links} docs, S/ {lm[0]['s']:,.2f}" if lm else f"\nLinks: {links} docs")
except: pass

print(f"\n✅ Seed completo. MongoDB: localhost:27017/pena_linda")
