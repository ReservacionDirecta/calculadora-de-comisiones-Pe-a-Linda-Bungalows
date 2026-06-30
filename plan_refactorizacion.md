# 🏗️ Plan de Refactorización — Peña Linda Dashboard

## 1. Problemas Actuales

| # | Problema | Impacto |
|---|----------|---------|
| 1 | **Monolito de 1,707 líneas** | Dificultad de mantenimiento, errores difíciles de rastrear |
| 2 | **Sin separación de usuarios** | Admin y hotelero ven lo mismo, información no priorizada |
| 3 | **Datos duplicados** | `cobros` y `pagos` mezclan lógica; `adeudado` se recalcula en 2 lugares distintos |
| 4 | **POS pendientes no existe** | No hay interfaz para cargar Izipay/Culqi/Openpay → el "Pendiente de confirmar" no se puede actualizar |
| 5 | **Tabs mal ordenados** | El hotelero necesita ver "¿qué falta?" primero, no gráficos de torta |
| 6 | **CSS inline en f-string** | 120 líneas de CSS dentro de `st.markdown` → difícil de editar |
| 7 | **Conexiones MongoDB dispersas** | Se abre/cierra conexión 4+ veces por render → lento |

---

## 2. Arquitectura Propuesta

```
calculadora/
├── panel_control.py        # Entry point (~60 líneas)
├── config.py               # Tema, colores, CSS, constantes
├── data.py                 # Carga única MongoDB + cálculos
├── components.py           # Componentes reutilizables
├── views/
│   ├── __init__.py
│   ├── kpi_bar.py          # Bento grid de KPIs + alertas
│   ├── ventas.py           # Gráficos + detalle + comisiones
│   ├── costos.py           # Costos operativos
│   ├── conciliacion.py     # Contraste tarjeta + Links + Abonos
│   ├── pos_upload.py       # ✨ NUEVO: Carga reportes POS (Izipay/Culqi/Openpay)
│   ├── historial.py        # Cruce QuickBooks vs abonos
│   └── exportar.py         # Exportación PDF/HTML
```

---

## 3. Nueva Jerarquía de Usuarios

### 🏄 Hotelero Surfista (vista por defecto)
```
┌──────────────────────────────────────────────┐
│ 🏝️ Peña Linda Bungalows                      │
│ 📅 Período: [01/06/2026 - 28/06/2026]        │
├──────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│ │ Vendido│ │Recibido│ │Pendiente│ │ Deuda  │ │
│ │S/84,500│ │S/72,300│ │S/12,200│ │S/8,400 │ │
│ └────────┘ └────────┘ └────────┘ └────────┘ │
├──────────────────────────────────────────────┤
│ ⚠️ ¿Qué necesita atención?                   │
│ ┌──────────────────────────────────────────┐ │
│ │ 📌 POS PENDIENTES: S/ 12,200 de Izipay, │ │
│ │    Culqi y Openpay no están cargados aún  │ │
│ │    📤 Subir reporte bancario →           │ │
│ └──────────────────────────────────────────┘ │
│ ✅ Links por confirmar: 4 (S/ 2,100)        │
├──────────────────────────────────────────────┤
│ [📊 Ventas] [💸 Costos] [📋 Conciliar]       │
└──────────────────────────────────────────────┘
```

### 👔 Admin (vista completa con tabs adicionales)
```
[📊 Dashboard] [📋 Transacciones] [💰 Comisiones] 
[💸 Costos] [🔄 Conciliar] [📤 POS] [📜 Historial]
```

**Diferencia:** El admin ve tabs de edición, carga de POS, y exportación.

---

## 4. Sección ✨ POS Upload (NUEVO)

### Interfaz:
```
┌─────────────────────────────────────────────┐
│ 📤 Cargar Reporte POS                       │
│                                             │
│ Selecciona plataforma:                      │
│ ○ Izipay  ○ Culqi  ○ Openpay               │
│                                             │
│ 📎 Archivo: [Seleccionar...]                │
│   (CSV/Excel del portal bancario)           │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Vista previa de datos extraídos:        │ │
│ │ Fecha       | Monto   | Tarjeta | Ref   │ │
│ │ 15/06/2026  | 420.00  | VISA    | 1234  │ │
│ │ 15/06/2026  | 850.00  | MC      | 5678  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [✅ Confirmar e Importar]                   │
└─────────────────────────────────────────────┘
```

### Flujo:
1. Admin sube reporte CSV/Excel del portal POS
2. Sistema extrae: fecha, monto, tarjeta, referencia
3. Muestra vista previa para confirmar
4. Al confirmar → inserta en `pagos` con `fuente: "Izipay POS"` (o Culqi/Openpay)
5. El KPI de "Recibido" se actualiza automáticamente
6. El "Pendiente" se recalcula: Sirvoy_tarjeta - (Izipay + Culqi + Openpay + POS_importados)

Esto resuelve el problema de: *"el monto pendiente de confirmar es de los POS de Izipay Culqi Openpay y debe ser cargado por el administrador"*

---

## 5. Data Pipeline Simplificado

### Actual (caótico):
```
MongoDB pagos → sv → sv_date_filtered → sv_sales_f → sv_sales_sirvoy
MongoDB cobros → cobros_data → total_abonos, adeudado
MongoDB cobros → (otra conexión) → cobros_extra
```

### Propuesto (una sola carga):
```python
@st.cache_data(ttl=300)
def load_all_data():
    # 1 conexión → todo
    pagos = list(db.pagos.find({}, {'hash':0}))
    cobros = list(db.cobros.find({}))
    
    df = pd.DataFrame(pagos)  # limpia, ordena, filtra
    cobros_df = pd.DataFrame(cobros)
    
    return df, cobros_df

df, cobros_df = load_all_data()
# Todos los cálculos derivan de df y cobros_df
# Sin conexiones adicionales
```

---

## 6. Timeline de Implementación

| Paso | Archivos | Tiempo estimado |
|------|----------|-----------------|
| 1. Crear `config.py` + `components.py` | config.py, components.py | 15 min |
| 2. Crear `data.py` con carga única | data.py | 15 min |
| 3. Split vistas → ventas.py, costos.py | views/ventas.py, views/costos.py | 20 min |
| 4. Split → conciliacion.py | views/conciliacion.py | 15 min |
| 5. ✨ POS Upload view | views/pos_upload.py | 20 min |
| 6. Split → historial.py, exportar.py | views/historial.py, views/exportar.py | 10 min |
| 7. Nuevo `panel_control.py` orquestador | panel_control.py | 10 min |
| 8. Testing y ajustes | - | 15 min |
| **Total estimado** | | **~2 horas** |

---

## 7. Preguntas para decidir

1. **¿Quieres mantener el archivo actual como respaldo** hasta que la refactorización funcione?
2. **¿El POS upload debe ser CSV genérico** o adaptado a cada portal (Izipay vs Culqi vs Openpay)?
3. **¿Quieres que el "hotelero" y "admin" sean dos modos seleccionables** o dos vistas separadas?
4. **¿La sección POS debe cargar archivos manuales** o también permitir pegar datos copiados del portal web?
