# Panel de Control — Peña Linda Bungalows 🏝️

Dashboard interactivo para la conciliación de pagos, comisiones y costos operativos del Hotel Peña Linda Bungalows (Máncora) y Chamba Digital.

---

## 📊 Dashboard (Streamlit)

**URL local:** `http://localhost:8501`

### Pestañas

| # | Pestaña | Función |
|---|---------|---------|
| 1 | 📈 **Gráficos** | Evolución diaria, distribución por tipo, top métodos de pago |
| 2 | 📋 **Conciliación** | Sirvoy vs Plataformas, comisión, costos, abonos |
| 3 | 📊 **Mes a Mes** | Barras apiladas + tabla mensual por tipo de pago |
| 4 | 🚫 **Links** | Seguimiento de pagos Link pendientes de depósito |
| 5 | 📄 **Detalle** | Transacciones con búsqueda, filtros y revisión |
| 6 | 📊 **Costos** | Detalle de costos operativos + agregar costos manuales |
| 7 | 📤 **Exportar** | PDF / HTML / CSV |
| 8 | 🔍 **Analytics** | Insights, día de semana, estacionalidad, tendencias |

### Sidebar

- **Filtro de período:** Rango / Día / Semana / Mes / Año — persiste al recargar (via query params)
- **Filtro de tipos:** Tarjeta / Transferencia / Efectivo
- **Escala logarítmica** para gráficos
- **Botón ⟳ Refresh** para recargar desde MongoDB

---

## 📦 Datos

### Fuentes

| Fuente | Docs | Período | Rol |
|--------|------|---------|-----|
| **Sirvoy** | ~5,337 | Ene 2025 → Jun 2026 | Registro maestro de ventas |
| **Izipay** | ~592 | Ene → Sep 2025 | Plataforma de pago (Link + POS) |
| **Culqi** | ~573 | Ene → Sep 2025 | Plataforma de pago |
| **Openpay** | ~168 | Oct 2025 → May 2026 | Plataforma de pago (POS principal) |
| **Costos FB Ads** | ~100 | Ene → Jun 2026 | Marketing digital |
| **Costos Sirvoy** | ~13 | Ene → Jun 2026 | Software €149/mes |
| **Costos Asistente** | ~9 | Feb → Jun 2026 | S/750 c/2 semanas |
| **Saldo Base** | 1 | Al 03/03/2026 | S/9,654.83 deuda inicial |
| **Total** | **~6,670** | **Ene 2025 → Jun 2026** | |

### Estructura en MongoDB

**Base:** `pena_linda` · **Colección:** `pagos`

```json
{
  "_id": ObjectId,
  "fuente": "Sirvoy | Izipay | Culqi | Openpay | Costo FB Ads | Costo Sirvoy | Costo Asistente | Saldo Base | Abono Chamba",
  "fecha": ISODate,
  "monto": Number,
  "moneda": "PEN",
  "metodo": "Pago con tarjeta | Transferencia bancaria | ...",
  "tipo_pago": "Tarjeta | Transferencia | Efectivo | Costo",
  "es_link": Boolean,
  "estado_deposito": "depositado | pendiente",
  "conciliado": Boolean,
  "transaction_id": String (Sirvoy ID),
  "referencia": String,
  "hash": String (MD5 para dedup),
  "link_vinculado": "alterno | principal",
  "fecha_depositado": ISODate
}
```

---

## 💰 Comisión Chamba Digital

- **Tasa:** 5% sobre **ventas brutas** de Sirvoy
- **Base:** Todo lo registrado en Sirvoy (tarjeta + transferencia + efectivo)
- No se descuentan retenciones ni embargos
- La comisión se calcula siempre sobre Sirvoy (ventas reales del hotel)

## 🚫 Pagos Link (pendientes de depósito)

- Se identifican por la palabra "link" / "pago link" en el campo `Comment` de Sirvoy
- **Link de Pago = canal de pago normal**, no estado de depósito
- El **embargo** es reciente y afecta solo a la cuenta Link de Izipay
- Los pagos históricos SÍ fueron depositados (541/542)
- El dashboard permite **marcar como depositados** individualmente o en lote

## 📋 Lógica de conciliación

```
Sirvoy (registro maestro)
├── 💳 Tarjeta:  S/ X  ← se contrasta con plataformas
├── 🏦 Transferencia: ✅ confirmado (recibido directo)
└── 💵 Efectivo:      ✅ confirmado

Plataformas (Izipay + Culqi + Openpay): S/ Y → depositado

🚫 Pendiente contraste = Tarjeta(Sirvoy) − Plataformas
✅ Recibido = Plataformas + Transferencia + Efectivo
```

## 💳 Módulo de Abonos (deuda Peña Linda → Chamba Digital)

- **Saldo base:** S/ 9,654.83 al 03/03/2026
- **Adeudado =** Saldo base + Comisión 5% (desde 03/03) + Costos operativos (desde 03/03)
- **Saldo pendiente =** Adeudado − Abonos recibidos
- Los abonos se registran desde la pestaña **📋 Conciliación → 💳 Abonos**

## 📊 Costos operativos

| Categoría | Frecuencia | Conversión |
|-----------|-----------|------------|
| 📱 **Facebook Ads** | Diario (cobros automáticos) | Directo en S/ |
| 🖥️ **Sirvoy** | €149/mes + Google Hotel Ads | EUR → PEN x 4.20 (tc 3.6-3.8 + 11% fees) |
| 👤 **Asistente comercial** | S/750 c/2 semanas | Directo en S/ |

---

## ☁️ Deploy en Railway

### Archivos

| Archivo | Propósito |
|---------|-----------|
| `Dockerfile` | python:3.11-slim + Streamlit en :8501 |
| `railway.json` | Health check /stcore/health, restart policy |
| `requirements.txt` | streamlit, pymongo, plotly, pandas, reportlab, openpyxl, pytz |

### Variables de entorno

| Variable | Valor | Propósito |
|----------|-------|-----------|
| `MONGO_URL` | `mongodb://...` | Conexión a MongoDB (Railway plugin) |
| `PORT` | `8501` | Puerto de Streamlit |

### Comandos

```bash
# Railway automático
git push → Railway detecta Dockerfile → deploy

# Seed inicial
python seed_completo.py
```

---

## 🛠️ Funcionalidades clave

### ✅ Validación de pagos
Desde 📄 **Detalle** → seleccionas transacciones 🚫 → eliges **Aprobado** / **No encontrado** / **Pendiente** → se actualiza MongoDB

### 🔄 Conciliación manual
Desde 📋 **Conciliación** → 🔄 **Conciliar** → ingresas monto → si hay match en Sirvoy + Plataformas → botón para conciliar

### 📅 Persistencia de fecha
El filtro de período se guarda en `st.query_params` → sobrevive a recargas de página (F5)

### 📤 Exportación
- PDF (reportlab)
- HTML
- CSV

---

## 📁 Archivos del proyecto

```
calculadora de comisiones Peña Linda Bungalows/
├── panel_control.py         ← Dashboard principal (Streamlit) 🎯
├── seed_completo.py          ← Seed inicial de MongoDB
├── data_processor.py         ← Limpieza de CSVs
├── conciliacion_pagos.py     ← CLI de conciliación
├── Dockerfile                ← Deploy Railway
├── railway.json              ← Config Railway
├── requirements.txt          ← Dependencias
├── .env.example              ← Variables de entorno
├── sirvoy_global_ene_jun_2026.csv
├── payments_export-*.csv     ← Exports de Sirvoy
├── izipay_soles_*.csv        ← Izipay Back Office
├── culqi.csv                 ← Culqi histórico
├── 2026-01-01--2026-06-24_Resumen_Facturación.csv  ← FB Ads
└── README.md                 ← Este archivo
```

---

## 🔧 Comandos útiles

```bash
# Iniciar dashboard
streamlit run panel_control.py --server.port 8501

# Cargar seed completo
python seed_completo.py

# Reporte semanal
python conciliacion_pagos.py weekly

# Conectar MongoDB
mongosh "mongodb://localhost:27017/pena_linda"
```

---

*Dashboard construido con Streamlit + MongoDB + Plotly · Diseño shadcn/Tailwind · Host Windows · Deploy Railway*
