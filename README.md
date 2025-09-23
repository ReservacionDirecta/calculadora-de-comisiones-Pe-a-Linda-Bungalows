# Sistema de Procesamiento de Pagos - Peña Linda Bungalows

Sistema integral para procesar y analizar transacciones de pagos de múltiples fuentes: Izipay, Culqi y transferencias bancarias directas.

## 🚀 Características

- **Procesamiento Multi-fuente**: Integra datos de Izipay, Culqi, transferencias directas y Facebook Ads
- **Interfaz Web Intuitiva**: Dashboard interactivo con Streamlit
- **Filtros Avanzados**: Por fecha, procesador, método de pago y montos
- **Visualizaciones**: Gráficos interactivos con Plotly
- **Exportación**: Descarga datos en CSV y Excel
- **Estadísticas en Tiempo Real**: Métricas y KPIs actualizados

## 📋 Estructura de Archivos Soportados

### Izipay (CSV con separador `;`)
- Transacciones de tarjetas de crédito/débito
- Información de comisiones y estados
- Datos de clientes y autorización

### Culqi (CSV con separador `,`)
- Transacciones POS y pagos digitales
- Comisiones detalladas por emisor y procesador
- Información de terminales

### Transferencias Directas (CSV)
- Pagos bancarios directos
- Transferencias y depósitos
- Información de booking

### Facebook Ads (CSV)
- Gastos en publicidad de Facebook/Meta
- Facturación de campañas publicitarias
- Formato de reporte de Meta

## 🛠️ Instalación

### Opción 1: Instalación Automática (Windows)
1. **Descargar todos los archivos del sistema**
2. **Ejecutar el instalador**:
   ```cmd
   install_windows.bat
   ```
   O con PowerShell:
   ```powershell
   .\install_python.ps1
   ```

### Opción 2: Instalación Manual
1. **Instalar Python 3.9 o superior**:
   - Desde Microsoft Store: Buscar "Python 3.11"
   - Desde python.org: https://www.python.org/downloads/
   - ⚠️ **Importante**: Marcar "Add Python to PATH" durante la instalación

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Probar el sistema**:
   ```bash
   python test_system.py
   ```

4. **Ejecutar la interfaz web**:
   ```bash
   streamlit run web_interface.py
   ```

### Inicio Rápido
Usa el archivo `iniciar_sistema.bat` para acceso directo a todas las funciones.

## 📊 Uso

1. **Cargar Archivos**: Usa la barra lateral para subir tus archivos CSV
2. **Aplicar Filtros**: Selecciona rangos de fecha, procesadores y métodos de pago
3. **Analizar Datos**: Revisa las métricas y gráficos generados
4. **Exportar Resultados**: Descarga los datos filtrados en CSV o Excel

## 🔧 Configuración

### Mapeo de Columnas

El sistema mapea automáticamente las columnas de cada fuente:

**Izipay**:
- `Fecha del pago` → Fecha de transacción
- `Importe del pago` → Monto
- `Medio de pago` → Método de pago
- `Estado` → Estado de transacción

**Culqi**:
- `Fecha de la transaccion` + `Hora de la transaccion` → Fecha completa
- `Monto VENTA` → Monto
- `Marca` → Método de pago
- `Estado` → Estado de transacción

**Transferencias**:
- `payment-list-item 2` → Fecha
- `payment-list-item 6` → Monto
- `payment-list-item 3` → Tipo de pago

## 📈 Métricas Disponibles

- **Total de Transacciones**: Número total de operaciones
- **Monto Total**: Suma de todos los pagos
- **Comisiones Totales**: Total de comisiones cobradas
- **Transacción Promedio**: Monto promedio por transacción
- **Distribución por Procesador**: Análisis por fuente de pago
- **Tendencias Temporales**: Evolución diaria de transacciones

## 🔍 Filtros Disponibles

- **Rango de Fechas**: Selecciona período específico
- **Procesador**: Filtra por Izipay, Culqi o Transferencias
- **Método de Pago**: VISA, Mastercard, Yape, etc.
- **Rango de Montos**: Filtra por valor de transacción

## 📁 Archivos del Sistema

- `data_processor.py`: Lógica principal de procesamiento
- `web_interface.py`: Interfaz web con Streamlit
- `requirements.txt`: Dependencias de Python
- `README.md`: Documentación del sistema

## 🚨 Consideraciones Importantes

1. **Formato de Fechas**: El sistema espera fechas en formato DD/MM/YYYY
2. **Separadores Decimales**: Izipay usa punto (.), transferencias usan coma (,)
3. **Encoding**: Todos los archivos deben estar en UTF-8
4. **Tamaño de Archivos**: Recomendado máximo 50MB por archivo

## 🔒 Seguridad

- Los archivos se procesan localmente
- No se almacenan datos en servidores externos
- Los archivos temporales se eliminan automáticamente

## 📞 Soporte

Para problemas técnicos o consultas sobre el sistema, contacta al equipo de desarrollo.

## 📝 Notas de Versión

### v1.0.0
- Procesamiento inicial de múltiples fuentes
- Interfaz web básica
- Filtros y exportación
- Visualizaciones interactivas