# 📋 Informe: Corrección de Datos Sirvoy (03/03 – 29/06/2026)

## 1. Problemas Identificados

### 1.1 `tipo_pago` incorrecto en documentos Sirvoy nuevos
- **Síntoma**: El dashboard mostraba S/ 0.00 en "Ventas Sirvoy"
- **Causa**: El import (`import_final.py`) asignó `tipo_pago = 'Pago'` para pagos positivos y `'Reversion'` para negativos. Pero el dashboard filtra por `['Tarjeta', 'Transferencia', 'Efectivo']`
- **Impacto**: **1,152 transacciones invisibles** para el dashboard
- **Fix**: Script `fix_tipo_pago_v2.py` — mapea cada `metodo` → `tipo_pago` correcto
- **Estado**: ✅ Corregido (1,159 documentos actualizados)

### 1.2 Documentos viejos (pre–marzo 2026) siguen en MongoDB
- **Síntoma**: 4,726 documentos Sirvoy del 2025 y enero–febrero 2026 aún existen
- **Causa**: El DELETE solo cubrió `03/03 – 29/06/2026`
- **Impacto**: Datos históricos se mezclan con nuevos. No afecta reportes del período actual
- **Fix**: Pendiente — borrar si ya no son necesarios
- **Estado**: ⚠️ No se tocaron (fuera del alcance)

### 1.3 Timezone `date_pe` con conversión UTC→Lima incorrecta
- **Síntoma**: `data.py` línea 33 trata `fecha` (hora Perú sin timezone) como UTC y convierte a Lima, restando 5 horas
- **Causa**: Los `fecha` ya están en hora Perú. `tz_localize('UTC').tz_convert('America/Lima')` desplaza 5h
- **Impacto**: Para pagos entre 00:00–04:59 el `date_pe` retrocede un día. Pagos de 05:00–23:59 mantienen fecha correcta
- **Estado**: ⚠️ Bug latente — no causó S/0.00 pero puede desfasar 1 día en madrugadas

### 1.4 Error menor en reportes semanales (filtro regex)
- **Síntoma**: `generate_weekly_mongo.py` usaba `$regex: 'sirvoy'` trayendo 10 documentos "Costo Sirvoy"
- **Causa**: La regex matcheaba "Costo Sirvoy" además de "Sirvoy"
- **Impacto**: Bruto inflado en ~S/ 4,752.44
- **Fix**: Cambiado a filtro exacto `fuente: 'Sirvoy'`
- **Estado**: ✅ Corregido y regenerado

---

## 2. Resumen del Import Final

| Métrica | Valor |
|---|---|
| **Total documentos insertados** | **1,152** |
| **Neto** | **S/ 346,101.83** |
| **Sirvoy Web coincide** | ✅ |
| **Semana 16/06–22/06** | S/ 15,753.13 ✅ |
| **Semana 23/06–29/06** | S/ 17,426.08 ✅ |
| **Export (14/03–29/06) verificado** | ✅ todas las semanas |
| **Scraped temprano (03/03–13/03) verificado** | ✅ |
| **Reversiones mapeadas por booking ref** | ✅ 6 tempranas + 33 del export = 39 total |

### 2.1 Fuentes del Import
| Origen | Docs | Monto |
|---|---|---|
| Export Sirvoy (14/03–29/06) | 1,000 | S/ 302,035.59 |
| Scraped early positives (03/03–13/03) | 140 | S/ 44,242.48 |
| Reversiones early (emparejadas por booking) | 6 | −S/ 1,940.62 |
| Scraped-only 14/03 (antes del 1er export) | 6 | +S/ 1,764.38 |
| **Total** | **1,152** | **S/ 346,101.83** |

---

## 3. Archivos Relacionados

| Archivo | Propósito |
|---|---|
| `import_final.py` | Script de import definitivo (DELETE + INSERT 1,152 docs) |
| `fix_tipo_pago_v2.py` | Corrige `tipo_pago` de 'Pago'/'Reversion' a 'Tarjeta'/'Transferencia'/'Efectivo' |
| `generate_weekly_mongo.py` | Genera reportes semanales PDF + CSV |
| `app_v2/data.py` | `load_all()` + `calc_kpis()` — carga y filtra datos del dashboard |
| `reportes_semanales/` | 17 PDFs + resumen CSV regenerados |

---

## 4. Pendientes / Observaciones

1. **Dashboard v1 (8501) y v2 (8502/8503)**: Ambos deben mostrar S/ 346,101.83 ahora. Si no, refrescar caché Streamlit (TTL 300s o reiniciar)
2. **Datos históricos (pre–marzo)**: 4,726 docs viejos. Si estorban, borrar con:
   ```
   db.pagos.delete_many({'fuente': 'Sirvoy', 'fecha': {'$lt': ISODate('2026-03-03')}})
   ```
3. **Timezone bug en `data.py`**: Línea 33 hace `tz_localize('UTC')` sobre hora Perú. Corregir: omitir conversión, usar `date_pe = date.dt.tz_localize('America/Lima', ambiguous='NaT')` directamente

---

## 5. Acciones Posteriores

### 5.1 Limpieza de datos pre-2026 ✅
- **3,763 documentos** del 2025 borrados de MongoDB
- Quedan **2,115 docs Sirvoy** desde 01/01/2026
- El dashboard ahora solo ve datos desde 2026

### 5.2 Pendiente: verificar datos Ene–Feb 2026
Los 963 docs de enero–febrero 2026 son del import antiguo. Si presentan problemas similares (tipo_pago, fechas), habría que reimportarlos desde Sirvoy.

---

*Generado: 30/06/2026 — Datos desde 01/01/2026*
