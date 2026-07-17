from pymongo import MongoClient
from urllib.parse import quote_plus

LOCAL_URL = "mongodb://localhost:27017/pena_linda"
RAILWAY_URL = "mongodb://mongo:fUvjeTSyEDOyfPAcUDCJBYeuSzYqdAkd@interchange.proxy.rlwy.net:32238/?authSource=admin"
RAILWAY_DB = "pena_linda"

print("=== SEED RAILWAY MONGODB ===\n")

local_cli = MongoClient(LOCAL_URL, serverSelectionTimeoutMS=5000)
local_db = local_cli['pena_linda']

railway_cli = MongoClient(RAILWAY_URL, serverSelectionTimeoutMS=10000)
railway_db = railway_cli[RAILWAY_DB]

collections = ['pagos', 'cobros', 'comisiones_futuras', 'qb_historico']

for col_name in collections:
    print(f"--- {col_name} ---")
    local_docs = list(local_db[col_name].find())
    print(f"  Local: {len(local_docs)} docs")

    if not local_docs:
        print("  Saltando")
        continue

    # Drop and recreate
    railway_db[col_name].drop()
    print(f"  Railway: dropped")

    # Remove _id and insert
    for doc in local_docs:
        doc.pop('_id', None)

    batch_size = 500
    for i in range(0, len(local_docs), batch_size):
        batch = local_docs[i:i+batch_size]
        railway_db[col_name].insert_many(batch)
        print(f"  Batch {i//batch_size + 1}: {len(batch)} inserted")

    count = railway_db[col_name].count_documents({})
    print(f"  Railway final: {count} docs\n")

# Create indexes
print("Creating indexes...")
railway_db['pagos'].create_index('fuente')
railway_db['pagos'].create_index('fecha')
railway_db['pagos'].create_index('tipo_pago')
try:
    railway_db['pagos'].create_index('hash', unique=True, sparse=True)
except:
    pass

railway_db['cobros'].create_index('tipo')
railway_db['cobros'].create_index('fecha')
try:
    railway_db['cobros'].create_index('hash', unique=True, sparse=True)
except:
    pass

railway_db['comisiones_futuras'].create_index('tipo')
railway_db['qb_historico'].create_index('fecha')
print("Indexes created\n")

# Verify totals
print("=== VERIFICACION ===")
for col_name in collections:
    lc = local_db[col_name].count_documents({})
    rc = railway_db[col_name].count_documents({})
    status = "OK" if lc == rc else "MISMATCH"
    print(f"  {col_name}: local={lc}, railway={rc} [{status}]")

sv_local = list(local_db['pagos'].aggregate([
    {'$match': {'fuente': 'Sirvoy'}},
    {'$group': {'_id': None, 'total': {'$sum': '$monto'}}}
]))
sv_railway = list(railway_db['pagos'].aggregate([
    {'$match': {'fuente': 'Sirvoy'}},
    {'$group': {'_id': None, 'total': {'$sum': '$monto'}}}
]))
lt = sv_local[0]['total'] if sv_local else 0
rt = sv_railway[0]['total'] if sv_railway else 0
print(f"\nSirvoy local: S/ {lt:,.2f}")
print(f"Sirvoy railway: S/ {rt:,.2f}")
print(f"Match: {'YES' if abs(lt-rt) < 0.01 else 'NO'}")

local_cli.close()
railway_cli.close()
print("\n=== SEED COMPLETADO ===")
