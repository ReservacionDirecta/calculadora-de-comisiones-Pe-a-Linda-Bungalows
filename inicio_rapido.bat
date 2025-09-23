@echo off
title Peña Linda Bungalows - Inicio Rápido

echo ========================================
echo  Peña Linda Bungalows - Inicio Rápido
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Ejecuta: instalar_completo.bat
    pause
    exit /b 1
)

echo ✅ Python disponible

REM Verificar dependencias críticas
python -c "import pandas, streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ Instalando dependencias faltantes...
    python -m pip install pandas streamlit plotly openpyxl numpy python-dateutil --quiet
    echo ✅ Dependencias instaladas
)

echo.
echo 🚀 ¿Qué quieres hacer?
echo.
echo 1. Probar sistema (recomendado primero)
echo 2. Abrir interfaz web
echo 3. Salir
echo.

set /p choice="Selecciona (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🧪 Probando sistema...
    python test_system.py
    echo.
    echo ¿Quieres abrir la interfaz web ahora? (s/n)
    set /p web="Respuesta: "
    if /i "%web%"=="s" (
        echo 🌐 Abriendo interfaz web...
        streamlit run web_interface.py
    )
) else if "%choice%"=="2" (
    echo.
    echo 🌐 Abriendo interfaz web...
    streamlit run web_interface.py
) else (
    echo ¡Hasta luego!
    exit /b 0
)

pause