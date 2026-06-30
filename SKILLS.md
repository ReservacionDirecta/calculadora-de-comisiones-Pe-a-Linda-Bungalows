---
name: conciliacion-pagos-pena-linda
description: Conciliación de pagos, comisiones y costos operativos para Hotel Peña Linda Bungalows. Extrae datos de Sirvoy, Izipay, Culqi, Openpay, Meta/FB Ads y los consolida en MongoDB + dashboard Streamlit.
category: financial
triggers:
  - "conciliar pagos peña linda"
  - "extraer datos sirvoy"
  - "izipay reporte"
  - "costos operativos peña linda"
  - "dashboard conciliación"
---

# Conciliación de Pagos — Peña Linda Bungalows

## Prerequisitos

- Python 3.11+ con: `streamlit`, `pymongo`, `pandas`, `plotly`, `reportlab`, `openpyxl`, `pytz`, `hashlib`
- MongoDB 8.0+ corriendo en `localhost:27017` (o `MONGO_URL` en Railway)
- Acceso a los portales web listados en AGENTS.md
- Chrome con DevTools para scraping de portales

## 1. Extraer datos de SIRVOY

### Objetivo: Obtener export de pagos del hotel

**Portal:** https://secured.sirvoy.com

**Credenciales (variables de entorno):**
- User: `$SIRVOY_USER`
- Pass: `$SIRVOY_PASS`
- 2FA: Código enviado a `$SIRVOY_2FA_EMAIL`

### Pasos (vía Chrome DevTools):

0. Si el agente NO tiene la sesión activa, pedir al usuario el código 2FA.

```
// Navegar a la página de pagos
navigate("https://secured.sirvoy.com/payments?start=2026-01-01&end=2026-06-23")

// Verificar total en la UI
take_snapshot()  →  buscar "Total:" en el snapshot

// Click en Exportar
click(link_exportar)
```

**⚠️ Límites:**
- Export máximo ~1,000 registros
- Para más de 1,000 registros: **dividir en chunks de 2 meses**
- Chunks seguros: Ene-Feb (~932), Mar-Abr (~657), May-Jun (~447)

**Procesamiento del CSV:**
```python
# Columnas del CSV:
# "Payment Id",Date,Method,Reference,Comment,"Linked To","Ledger Account","Value Date",Status,Amount

# Montos en formato europeo (1.234,56)
def parse_amount(s):
    s = str(s).strip().replace('"','')
    if ',' in s and '.' in s:
        if s.rindex(',') > s.rindex('.'):
            s = s.replace('.','').replace(',','.')
        else:
            s = s.replace(',','')
    elif ',' in s:
        s = s.replace(',','.')
    return float(s)
```

**Identificación de Link de Pago:**
```python
es_link = 'link' in str(row.get('Comment','')).lower() or 'link' in str(row.get('Reference','')).lower()
```

**Clasificación de tipo_pago:**
```python
m = method.lower()
tipo = 'Tarjeta' if 'tarjeta' in m or 'card' in m else \
       'Transferencia' if 'transferencia' in m or 'transf' in m else \
       'Efectivo' if 'efectivo' in m or 'cash' in m else 'Otros'
```

## 2. Extraer datos de IZIPAY (Back Office Vendedor)

### Objetivo: Descargar reporte de transacciones procesadas

**Portal:** https://secure.micuentaweb.pe/auth/login

**Credenciales Soles (variables de entorno):**
- User: `$IZIPAY_BO_USER`
- Pass: `$IZIPAY_BO_PASS`
- RUC: `$IZIPAY_RUC`

**Credenciales USD (variables de entorno):**
- User: `$IZIPAY_BO_USD_USER`
- Pass: `$IZIPAY_BO_USD_PASS`

### Pasos (vía browser):

1. Ir a `https://secure.micuentaweb.pe/auth/login`
2. Ingresar credenciales
3. Navegar a **Reportes → Ventas por fecha**
4. Seleccionar el periodo (pueden ser varios meses)
5. Click **Exportar** → CSV
6. El CSV descarga automáticamente

## 3. Extraer datos de IZIPAY POS (Mi Cuenta)

### Objetivo: Reporte de saldos POS

**Portal:** https://micuenta.izipay.pe/seguridad/login

**Credenciales (variables de entorno):**
- User: `$IZIPAY_POS_USER`
- Pass: `$IZIPAY_POS_PASS`

**⚠️ Este portal tiene reCAPTCHA — el login debe hacerlo el usuario manualmente.**

### Pasos:

1. El usuario inicia sesión (reCAPTCHA blocking)
2. Una vez logueado, navegar a **Reportería → Saldos**
3. Seleccionar rango de fechas (máx 3 meses)
4. Descargar Excel (.xlsx)

## 4. Extraer datos de META / FACEBOOK ADS

### Objetivo: Costos de publicidad en Meta

**Portal:** Facebook Business → Facturación

### Pasos:

1. Ir a Business Facebook
2. Navegar a **Facturación → Resumen de facturación**
3. Seleccionar rango de fechas
4. Descargar CSV

**Procesamiento:**
```python
df = pd.read_csv("archivo.csv", encoding='utf-8', skiprows=9, skipfooter=3, engine='python')
df.columns = ['Fecha','ID','Metodo','Importe','Divisa']
# Importe viene como "41,65" — convertir
df['Importe'] = df['Importe'].str.replace(',','.', regex=False).astype(float)
```

## 5. Cargar todo a MongoDB

### Script unificado: seed_completo.py

```python
from pymongo import MongoClient
import hashlib
import pandas as pd

cli = MongoClient('mongodb://localhost:27017/')
db = cli['pena_linda']

# Crear índice único para deduplicación
db['pagos'].create_index("hash", unique=True)

def insertar_doc(doc):
    doc['hash'] = hashlib.md5(str(doc).encode()).hexdigest()
    try:
        db['pagos'].insert_one(doc)
        return 1
    except:
        return 0
```

## 6. Dashboard (panel_control.py)

### Iniciar localmente
```bash
streamlit run panel_control.py --server.port 8501
```

### Variables de entorno
```bash
MONGO_URL=mongodb://localhost:27017/pena_linda  # default local
PORT=8501                                         # Railway auto
```

## 7. Pipelines de cron

### Reporte semanal (martes 10AM)
```bash
python conciliacion_pagos.py weekly
```
- Calcula comisión de la semana (martes→lunes)
- Muestra vendido vs recibido vs pendiente
- Genera alerta si hay pagos no depositados

### Reporte mensual (día 01)
```bash
python conciliacion_pagos.py monthly
```
- Consolidado del mes completo
- Costos operativos del mes
- Comisión + saldo actualizado

## 8. Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Sirvoy export incompleto | Límite 1000 registros | Dividir en chunks de 2 meses |
| TypeError: strftime | String en session_state | Convertir con `pd.Timestamp(v).date()` |
| CAPTCHA en Izipay POS | reCAPTCHA del portal | Usuario debe loguearse manualmente |
| Código 2FA Sirvoy | Autenticación de dos factores | Pedir código al usuario |
| Diferencia Sirvoy web vs dash | Registros faltantes | Re-exportar desde Sirvoy en chunks |

## 9. Reglas de negocio (NO CAMBIAR)

1. ✅ Comisión 5% sobre **bruto** Sirvoy (ventas contabilizadas)
2. ✅ Embargos/retenciones **NO afectan** comisión
3. ✅ Transferencia + Efectivo Sirvoy = **confirmados**
4. ✅ Solo **tarjeta Sirvoy** se contrasta con plataformas
5. ✅ Sirvoy = **registro maestro**, plataformas = **confirmación de depósito**
6. ✅ Link de Pago = **canal**, no estado de depósito
