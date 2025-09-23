@echo off
title Peña Linda Bungalows - Interfaz Web

echo ========================================
echo  Peña Linda Bungalows
echo  Lanzando Interfaz Web...
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado en CMD
    echo Intentando con ruta completa...
    
    REM Intentar rutas comunes de Python
    if exist "C:\Python313\python.exe" (
        set PYTHON_PATH=C:\Python313\python.exe
    ) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" (
        set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
    ) else (
        echo ❌ No se pudo encontrar Python
        echo Por favor ejecuta: inicio_rapido.bat
        pause
        exit /b 1
    )
) else (
    set PYTHON_PATH=python
)

echo ✅ Python encontrado
echo 🌐 Iniciando servidor web...
echo.
echo 📋 INSTRUCCIONES:
echo 1. El navegador se abrirá automáticamente
echo 2. Si no se abre, ve a: http://localhost:8501
echo 3. Para detener el servidor, presiona Ctrl+C
echo.
echo 🚀 Cargando interfaz...

%PYTHON_PATH% -m streamlit run web_interface.py --server.headless true

pause