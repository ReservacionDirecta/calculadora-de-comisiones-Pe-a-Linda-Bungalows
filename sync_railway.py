from pymongo import MongoClient

LOCAL_URL = "mongodb://localhost:27017/pena_linda"
RAILWAY_URL = "mongodb://mongo:fUvjeTSyEDOyfPAcUDCJBYeuSzYqdAkd@interchange.proxy.rlwy.net:32238/?authSource=admin"
RAILWAY_DB = "pena_linda"

local_cli = MongoClient(LOCAL_URL, serverSelectionTimeoutMS=5000)
local_db = local_cli['pena_linda']

railway_cli = MongoClient(RAILWAY_URL, serverSelectionTimeoutMS=10000)
railway_db = railway_cli[RAILWAY_DB]

for col_name in ['pagos', 'cobros']:
    local_docs = list(local_db[col_name].find())
    railway_db[col_name].drop()
    for doc in local_docs:
        doc.pop('_id', None)
    batch_size = 500
    for i in range(0, len(local_docs), batch_size):
        batch = local_docs[i:i+batch_size]
        railway_db[col_name].insert_many(batch)
    count = railway_db[col_name].count_documents({})
    print(f"{col_name}: {count} docs")

# Verify
r = list(railway_db['pagos'].aggregate([
    {'$match': {'fuente': 'Sirvoy'}},
    {'$group': {'_id': None, 'total': {'$sum': '$monto'}}}
]))
print(f"Sirvoy railway: S/ {r[0]['total']:,.2f}")

local_cli.close()
railway_cli.close()
print("Railway updated")
