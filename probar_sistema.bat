@echo off
title Peña Linda Bungalows - Prueba del Sistema

echo ========================================
echo  Peña Linda Bungalows
echo  Probando Sistema Actualizado
echo ========================================
echo.

REM Buscar Python en ubicaciones comunes
set PYTHON_PATH=

if exist "C:\Python313\python.exe" (
    set PYTHON_PATH=C:\Python313\python.exe
    echo ✅ Python encontrado en C:\Python313\
) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" (
    set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
    echo ✅ Python encontrado en AppData
) else (
    REM Intentar con python en PATH
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_PATH=python
        echo ✅ Python encontrado en PATH
    ) else (
        echo ❌ No se pudo encontrar Python
        echo Por favor verifica la instalación
        pause
        exit /b 1
    )
)

echo.
echo 🧪 Ejecutando prueba del sistema...
echo.

%PYTHON_PATH% test_system.py

echo.
echo ✅ Prueba completada
echo.
echo 🌐 ¿Quieres abrir la interfaz web? (s/n)
set /p web="Respuesta: "

if /i "%web%"=="s" (
    echo Abriendo interfaz web...
    %PYTHON_PATH% -m streamlit run web_interface.py
)

pause