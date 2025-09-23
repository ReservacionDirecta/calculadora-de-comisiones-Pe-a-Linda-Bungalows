# 🔧 Guía de Solución de Problemas
## Sistema de Procesamiento de Pagos - Peña Linda Bungalows

### 🚨 Problema: "Python was not found"

**Síntomas:**
```
Python was not found; run without arguments to install from the Microsoft Store
```

**Soluciones (en orden de preferencia):**

#### ✅ Solución 1: Microsoft Store (Recomendada)
1. Presiona `Win + R`
2. Escribe: `ms-windows-store://pdp/?ProductId=9NRWMJP3717K`
3. Presiona Enter
4. Haz clic en "Obtener"
5. Espera a que se instale
6. Reinicia el símbolo del sistema

#### ✅ Solución 2: Instalador Automático
```cmd
instalar_completo.bat
```

#### ✅ Solución 3: Descarga Manual
1. Ve a: https://www.python.org/downloads/
2. Descarga Python 3.9 o superior
3. **IMPORTANTE**: Durante la instalación marca "Add Python to PATH"
4. Reinicia el símbolo del sistema

### 🚨 Problema: Streamlit no funciona

**Síntomas:**
- La opción 2 del menú no abre la interfaz web
- Error: "streamlit: command not found"

**Solución:**
```cmd
python -m pip install streamlit
streamlit run web_interface.py
```

### 🚨 Problema: Error en archivo Facebook

**Síntomas:**
```
Error tokenizing data. C error: Expected 1 fields in line 10, saw 5
```

**Solución:**
- ✅ **YA SOLUCIONADO** en la última versión
- El sistema ahora procesa correctamente el formato de Facebook

### 🚨 Problema: "No module named 'pandas'"

**Síntomas:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Solución:**
```cmd
python -m pip install pandas numpy streamlit plotly openpyxl python-dateutil
```

### 🚨 Problema: Archivos CSV no se cargan

**Síntomas:**
- "0 transacciones cargadas"
- Errores de encoding

**Soluciones:**
1. **Verificar encoding**: Los archivos deben estar en UTF-8
2. **Verificar separadores**:
   - Izipay: punto y coma (;)
   - Culqi: coma (,)
   - Transferencias: coma (,)
   - Facebook: coma (,)
3. **Verificar nombres de archivo**:
   - `Listado_transacciones_capturadas-izipay.csv`
   - `ventas_20250923_culqi.csv`
   - `secured.csv`
   - `Resumen_Facturación_facebook.csv`

### 🛠️ Herramientas de Diagnóstico

#### Diagnóstico Completo
```cmd
diagnostico.bat
```

#### Probar Sistema
```cmd
python test_system.py
```

#### Verificar Instalación
```cmd
python --version
python -m pip list
```

### 📞 Pasos de Solución Rápida

1. **Ejecutar diagnóstico:**
   ```cmd
   diagnostico.bat
   ```

2. **Si Python no está instalado:**
   ```cmd
   instalar_completo.bat
   ```

3. **Si hay errores de dependencias:**
   ```cmd
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. **Probar el sistema:**
   ```cmd
   python test_system.py
   ```

5. **Usar la interfaz web:**
   ```cmd
   streamlit run web_interface.py
   ```

### 🎯 Resultados Esperados

**Test exitoso debe mostrar:**
- ✅ Izipay: 140+ transacciones
- ✅ Culqi: 185+ transacciones  
- ✅ Transferencias: 900+ transacciones
- ✅ Facebook Ads: 19+ transacciones
- ✅ Total: 1,200+ transacciones
- ✅ Monto total: S/ 500,000+

### 📧 Si Nada Funciona

1. Ejecuta `diagnostico.bat` y toma captura de pantalla
2. Verifica que todos los archivos estén en el mismo directorio
3. Intenta reinstalar Python completamente
4. Usa PowerShell como administrador si es necesario

### 🔄 Reinstalación Completa

Si todo falla, sigue estos pasos:

1. **Desinstalar Python** (si está instalado)
2. **Limpiar variables de entorno**
3. **Instalar Python fresco** desde Microsoft Store
4. **Ejecutar** `instalar_completo.bat`
5. **Probar** con `python test_system.py`