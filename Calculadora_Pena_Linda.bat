@echo off
setlocal enabledelayedexpansion
title Calculadora Peña Linda Bungalows - Lanzador

echo ============================================================
echo      Calculadora de Comisiones Peña Linda Bungalows      
echo ============================================================
echo.

:: 1. Verificar Python
echo [1/3] Verificando entorno Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python no encontrado en el PATH. Buscando...
    
    set "PY_PATH="
    if exist "C:\Python313\python.exe" set "PY_PATH=C:\Python313\python.exe"
    if not defined PY_PATH if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY_PATH=%LocalAppData%\Programs\Python\Python313\python.exe"
    if not defined PY_PATH if exist "%LocalAppData%\Microsoft\WindowsApps\python.exe" set "PY_PATH=%LocalAppData%\Microsoft\WindowsApps\python.exe"

    if not defined PY_PATH (
        echo ERROR: No se pudo encontrar Python 3.13 automaticamente.
        echo Por favor, instala Python desde la Microsoft Store o python.org
        pause
        exit /b 1
    )
    set "PYTHON_EXE=!PY_PATH!"
) else (
    set "PYTHON_EXE=python"
)
echo OK: Python detectado.

:: 2. Verificar Dependencias
echo.
echo [2/3] Verificando librerias necesarias...
"%PYTHON_EXE%" -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo Advertencia: Problemas instalando dependencias.
) else (
    echo OK: Librerias listas.
)

:: 3. Crear Acceso Directo (Escritorio)
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Calculadora Pena Linda.lnk"
if not exist "%SHORTCUT_PATH%" (
    echo.
    echo Deseas crear un acceso directo en el Escritorio? (S/N)
    set /p "create_shortcut="
    if /i "!create_shortcut!"=="S" (
        echo Creando acceso directo...
        powershell -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%~f0';$s.WorkingDirectory='%~dp0';$s.Save()"
        echo OK: Acceso directo creado.
    )
)

:: 4. Lanzar Aplicacion
echo.
echo [3/3] Iniciando aplicacion...
echo ------------------------------------------------------------
echo La calculadora se abrira en tu navegador automaticamente.
echo Manten esta ventana abierta mientras uses la aplicacion.
echo ------------------------------------------------------------
echo.

"%PYTHON_EXE%" -m streamlit run web_interface.py --server.headless false

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La aplicacion se cerro inesperadamente.
    pause
)
