# AGENTS.md — Peña Linda Bungalows · Sistema de Conciliación

Este archivo documenta todos los flujos, credenciales y procedimientos para que CUALQUIER agente (IA o humano) pueda:
1. Extraer datos de los portales (Sirvoy, Izipay, Culqi, Openpay, Meta Ads)
2. Procesarlos e integrarlos al dashboard
3. Mantener la base de datos actualizada

---

## 🔐 Credenciales y accesos

| Portal | URL | Usuario | Contraseña | Notas |
|--------|-----|---------|------------|-------|
| **Sirvoy** (Web) | https://secured.sirvoy.com/login | `Reservaciondirecta` | `Oliver@2601` | Envía código 2FA al email `yerctech@gmail.com` |
| **Izipay BO** (Back Office) | https://secure.micuentaweb.pe/auth/login | `jzapataramos@chamba.pe` | `Suzukisamurai@1213` | RUC 20525260942 — portal Soles |
| **Izipay BO (USD)** | https://secure.micuentaweb.pe/auth/login | `jzapataramos@gmail.com` | `Suzukisamurai@1213` | Portal USD — mismo login, cambiar cuenta |
| **Izipay POS** (Mi Cuenta) | https://micuenta.izipay.pe/seguridad/login | `penalinda@yahoo.com` | `Suzukisamurai@1213` | Tiene reCAPTCHA — requiere login manual |
| **Culqi** | https://panel.culqi.pe/#/login | `yerctech@gmail.com` | `Suzukisamurai@1213` | Exportar reportes |
| **Openpay** | https://dashboard.openpay.pe/login | `yerctech@gmail.com` | `Suzukisamurai@1213` | Exportar reportes |
| **Meta/FB Ads** | https://business.facebook.com/ | `yerctech@gmail.com` | — | Descargar resumen de facturación |
| **MongoDB Local** | `mongodb://localhost:27017/pena_linda` | — | — | Base local |
| **MongoDB Railway** | Via `MONGO_URL` env var | — | — | Base en producción |

> ⚠️ **NUNCA** incluir credenciales en código fuente. Usar variables de entorno o `.env`.

---

## 🧩 Flujos de extracción por portal

### 1. SIRVOY (Registro maestro de ventas)

**Propósito:** Obtener todas las transacciones registradas en el hotel.

**URL export:** `https://secured.sirvoy.com/payments/export?start=YYYY-MM-DD&end=YYYY-MM-DD`

**Procedimiento:**

1. Navegar a `https://secured.sirvoy.com/login` e iniciar sesión
2. Ingresar código 2FA enviado al email (solicitar al usuario)
3. Navegar a Pagos → filtrar por fecha deseada
4. **Límite:** Exportación máxima de **1,000 registros** por rango
5. Si hay más de 1,000 registros, dividir en chunks de 2 meses (ej: Ene-Feb, Mar-Abr, May-Jun)
6. Hacer clic en **"Exportar"** para descargar CSV
7. El CSV se guarda en `~/Downloads/payments_export-{timestamp}.csv`
8. Copiar a la carpeta del proyecto

**Formato del CSV exportado:**
```csv
"Payment Id",Date,Method,Reference,Comment,"Linked To","Ledger Account","Value Date",Status,Amount
```

**Mapeo a MongoDB:**
| Campo Sirvoy | Campo MongoDB | Notas |
|-------------|---------------|-------|
| Payment Id | `transaction_id` | ID único |
| Date | `fecha` | Parsear `%d/%m/%Y %H:%M` |
| Method | `metodo` | "Pago con tarjeta", "Transferencia bancaria", "Efectivo" |
| Reference | `referencia` | Número de referencia |
| Comment | — | Usado para detectar "link" (es_link) |
| Amount | `monto` | Formato europeo: `1.234,56` → `1234.56` |
| — | `tipo_pago` | Derivado de Method: Tarjeta/Transferencia/Efectivo |
| — | `es_link` | `true` si Comment o Reference contiene "link" |
| — | `estado_deposito` | Siempre "depositado" por defecto |
| — | `link_vinculado` | "alterno" si es Link alterno, "" si no |

**Tipo de pago (derivado de Method):**
```python
if 'tarjeta' in method or 'card' in method: tipo = 'Tarjeta'
elif 'transferencia' in method or 'transf' in method: tipo = 'Transferencia'
elif 'efectivo' in method or 'cash' in method: tipo = 'Efectivo'
else: tipo = 'Otros'
```

---

### 2. IZIPAY BACK OFFICE (secure.micuentaweb.pe)

**Propósito:** Obtener detalle de pagos con tarjeta procesados (Link + POS).

**Dos perfiles:**
- **Soles:** `jzapataramos@chamba.pe` — RUC 20525260942
- **USD:** `jzapataramos@gmail.com`

**Procedimiento:**

1. Ir a `https://secure.micuentaweb.pe/auth/login`
2. Ingresar credenciales
3. Ir a **Reportes → Ventas por fecha**
4. Seleccionar rango de fechas (máx. 3 meses)
5. Click en **"Exportar"** → seleccionar formato CSV
6. Descargar archivo

**Columnas relevantes del CSV:**
```csv
"Fecha","Número de pedido","Monto","Moneda","Método de pago","Fuente pago","Estado","Tarjeta","Código de comercio"
```

- `Fuente pago` = "Pago por formulario de recolección de datos" (todos los canales)
- `Método de pago` = "Visa", "Mastercard", etc.
- Diferenciar POS vs Link: el `Comment` en Sirvoy indica si es "link"

---

### 3. IZIPAY POS (micuenta.izipay.pe)

**Propósito:** Reporte de saldos POS (retiros, comisiones, ventas físicas).

**Procedimiento:**

1. Ir a `https://micuenta.izipay.pe/seguridad/login`
2. **⚠️ Tiene reCAPTCHA** — el usuario debe iniciar sesión manualmente
3. Navegar a **Reportería → Saldos**
4. Seleccionar rango de fechas (máx. 3 meses)
5. Descargar reporte Excel (.xlsx)

**Formato del Excel:** Contiene:
- VENTA IZIPAY (cobros POS positivos)
- RETIRO INMEDIATO / RETIRO EN 24 HRS (retiros negativos)
- COBRO OPERATIVO (comisiones)
- REG. ABONOS RECHAZADOS

---

### 4. CULQI (panel.culqi.pe)

**Procedimiento estándar:** Exportar reporte de transacciones por fecha.

---

### 5. OPENPAY (dashboard.openpay.pe)

**Procedimiento estándar:** Exportar reporte de transacciones por fecha.

---

### 6. META ADS / FACEBOOK ADS

**Propósito:** Obtener costos de publicidad en Facebook/Instagram.

**Procedimiento:**

1. Ir a Business Facebook
2. Navegar a **Facturación → Resumen de facturación**
3. Seleccionar rango de fechas (Ene 2025 → Jun 2026)
4. Descargar CSV

**Formato del CSV:**
```csv
Fecha,Identificador de la transacción,Método de pago,Importe,Divisa
22/6/2026,275388...,Visa .... 2851,"41,65",PEN
```

- `Importe` en formato texto con separador decimal `,` (ej: "41,65")
- Cancelaciones tienen Importe negativo
- Todos los montos están en PEN (soles)
- El archivo tiene 9 líneas de header antes de los datos y 3 líneas de footer

---

## 🔄 Procesamiento e importación

### Pipeline de importación

```python
1. Leer CSV/Excel
2. Parsear fechas (formato peruano: dd/mm/YYYY)
3. Parsear montos (formato europeo: 1.234,56 → número)
4. Clasificar tipo_pago (Tarjeta/Transferencia/Efectivo/Costo)
5. Calcular hash MD5 para deduplicación
6. Insertar en MongoDB (skip si hash existe)
```

### Deduplicación

Cada documento tiene un campo `hash` calculado como:
```python
hash = md5(f"{fuente}|{transaction_id}|{fecha}|{monto}|{metodo}")
```

El hash tiene un índice único en MongoDB. Si se intenta insertar un duplicado, MongoDB lo rechaza silenciosamente.

---

## 📊 Cálculos clave del dashboard

### Comisión Chamba Digital
```
Comisión = Sirvoy_total × 5%
Siempre sobre bruto (ventas contabilizadas), sin descontar embargos.
```

### Contraste de tarjeta
```
Pendiente = Sirvoy_tarjeta − (Izipay + Culqi + Openpay)
Solo aplica a pagos con tarjeta (Transferencia y Efectivo están confirmados).
```

### Recibido confirmado
```
Recibido = Plataformas + Sirvoy_transferencia + Sirvoy_efectivo
```

### Saldo deudor (Peña Linda → Chamba Digital)
```
Adeudado  = 9,654.83 (saldo base al 03/03/2026)
           + Comisión_5%_desde_03/03
           + Costos_FB_desde_03/03
           + Costos_Sirvoy_desde_03/03
           + Costos_Asistente_desde_03/03

Saldo_Pendiente = Adeudado − Abonos_Recibidos
```

---

## 🚨 Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `KeyError: 'Amount'` | CSV exportado con otro formato | Verificar columnas del CSV |
| `ValueError: could not convert string to float: '1.234,56'` | Formato europeo | Usar `parse_amount()` que maneja ambos separadores |
| Sirvoy web ≠ dashboard | Export limitado a 1,000 registros | Dividir en chunks de 2 meses |
| date_input error: `strftime` | String en session_state | Convertir con `pd.Timestamp(v).date()` |
| reCAPTCHA en login | Portal de Izipay POS | Pedir al usuario que inicie sesión manualmente |
| Sirvoy 2FA code | Autenticación de dos factores | Solicitar código al usuario (llega a `yerctech@gmail.com`) |

---

## 📁 Archivos del proyecto

```
C:\Users\yerct\calculadora de comisiones Peña Linda Bungalows\
├── panel_control.py              ← DASHBOARD PRINCIPAL
├── seed_completo.py              ← Seed MongoDB (todas las fuentes)
├── conciliacion_pagos.py         ← CLI conciliación semanal/mensual
├── data_processor.py             ← Limpieza CSVs
├── generar_pdf_semanal.py        ← Reporte PDF semanal
├── Dockerfile                    ← Deploy Railway
├── railway.json                  ← Config Railway
├── requirements.txt              ← Dependencias Python
├── README.md                     ← Documentación general
├── AGENTS.md                     ← Este archivo (flujos para agentes)
├── SKILLS.md                     ← Skills para Hermes Agent
└── *.csv / *.xlsx                ← Datos fuente
```

---

## 🎯 Reglas de negocio inmutables

1. **Comisión al 5% sobre BRUTO** (ventas generadas contabilizadas en Sirvoy)
2. **Embargos/retenciones NO afectan la comisión**
3. **Link de Pago = canal, no estado** — la mayoría se depositaron normalmente
4. **Transferencia + Efectivo en Sirvoy están confirmados** — no necesitan contraste
5. **Solo tarjeta Sirvoy se contrasta** con plataformas (Izipay, Culqi, Openpay)
6. **Sirvoy es el registro maestro** — las plataformas confirman el depósito digital
