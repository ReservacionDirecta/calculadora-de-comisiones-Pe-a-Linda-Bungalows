@echo off
echo ========================================
echo  Peña Linda Bungalows - Instalador
echo  Sistema de Procesamiento de Pagos
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no está instalado en este sistema.
    echo.
    echo 📥 Descargando Python...
    echo Por favor, descarga Python desde: https://www.python.org/downloads/
    echo.
    echo Instrucciones:
    echo 1. Ve a https://www.python.org/downloads/
    echo 2. Descarga Python 3.9 o superior
    echo 3. Durante la instalación, marca "Add Python to PATH"
    echo 4. Ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado:
python --version

echo.
echo 📦 Instalando dependencias...
pip install pandas numpy streamlit plotly openpyxl python-dateutil

if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    echo Intentando con pip3...
    pip3 install pandas numpy streamlit plotly openpyxl python-dateutil
)

echo.
echo 🧪 Probando el sistema...
python test_system.py

echo.
echo ✅ Instalación completada!
echo.
echo 🚀 Para ejecutar el sistema:
echo    python test_system.py          (para probar)
echo    streamlit run web_interface.py (para la interfaz web)
echo.
pause