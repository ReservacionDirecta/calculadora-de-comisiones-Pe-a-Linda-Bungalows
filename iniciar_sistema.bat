@echo off
title Peña Linda Bungalows - Sistema de Pagos

echo ========================================
echo  Peña Linda Bungalows
echo  Sistema de Procesamiento de Pagos
echo ========================================
echo.

REM Verificar si Python está disponible
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Ejecuta install_windows.bat primero.
    pause
    exit /b 1
)

echo Selecciona una opción:
echo.
echo 1. Probar el sistema con archivos existentes
echo 2. Abrir interfaz web interactiva
echo 3. Ver ayuda sobre formatos de archivo
echo 4. Salir
echo.

set /p choice="Ingresa tu opción (1-4): "

if "%choice%"=="1" (
    echo.
    echo 🧪 Ejecutando prueba del sistema...
    python test_system.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 🌐 Verificando Streamlit...
    
    REM Verificar si Streamlit está instalado
    streamlit --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Streamlit no está instalado. Instalando...
        pip install streamlit
        if %errorlevel% neq 0 (
            echo ❌ Error instalando Streamlit
            echo Intenta ejecutar: pip install streamlit
            pause
            goto :eof
        )
    )
    
    echo ✅ Streamlit disponible
    echo 🌐 Abriendo interfaz web...
    echo La interfaz se abrirá en tu navegador en unos segundos...
    echo Presiona Ctrl+C para detener el servidor
    echo.
    streamlit run web_interface.py
) else if "%choice%"=="3" (
    echo.
    python test_system.py --help
    pause
) else if "%choice%"=="4" (
    echo.
    echo ¡Hasta luego!
    exit /b 0
) else (
    echo.
    echo ❌ Opción inválida
    pause
)

goto :eof