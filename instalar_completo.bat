@echo off
title Peña Linda Bungalows - Instalador Completo

echo ========================================
echo  Peña Linda Bungalows - Instalador
echo  Sistema de Procesamiento de Pagos
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no está instalado.
    echo.
    echo 📥 Instalando Python desde Microsoft Store...
    echo.
    echo INSTRUCCIONES:
    echo 1. Se abrirá Microsoft Store
    echo 2. Busca "Python 3.11" 
    echo 3. Haz clic en "Obtener"
    echo 4. Espera a que se instale
    echo 5. Cierra Microsoft Store
    echo 6. Ejecuta este script nuevamente
    echo.
    
    set /p install="¿Quieres abrir Microsoft Store ahora? (s/n): "
    if /i "%install%"=="s" (
        start ms-windows-store://pdp/?ProductId=9NRWMJP3717K
    )
    
    echo.
    echo También puedes descargar desde: https://www.python.org/downloads/
    echo ⚠️ IMPORTANTE: Durante la instalación marca "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado:
python --version

echo.
echo 📦 Actualizando pip...
python -m pip install --upgrade pip

echo.
echo 📦 Instalando dependencias del sistema...

REM Lista de paquetes necesarios
set packages=pandas numpy streamlit plotly openpyxl python-dateutil

for %%p in (%packages%) do (
    echo Instalando %%p...
    python -m pip install %%p --quiet
    if !errorlevel! neq 0 (
        echo ⚠️ Reintentando %%p...
        python -m pip install %%p --user --quiet
    )
)

echo.
echo ✅ Dependencias instaladas!

echo.
echo 🧪 Probando el sistema...
python test_system.py

echo.
echo ✅ ¡Instalación completada exitosamente!
echo.
echo 🚀 Para usar el sistema:
echo.
echo   Opción 1 - Menú interactivo:
echo     iniciar_sistema.bat
echo.
echo   Opción 2 - Comandos directos:
echo     python test_system.py          (probar sistema)
echo     streamlit run web_interface.py (interfaz web)
echo.

pause