@echo off
title Diagnóstico del Sistema - Peña Linda Bungalows

echo ========================================
echo  DIAGNÓSTICO DEL SISTEMA
echo  Peña Linda Bungalows
echo ========================================
echo.

echo 🔍 Verificando Python...
python --version 2>nul
if %errorlevel% equ 0 (
    echo ✅ Python está instalado
    python --version
) else (
    echo ❌ Python NO está instalado
    echo.
    echo 💡 Soluciones:
    echo 1. Instalar desde Microsoft Store: ms-windows-store://pdp/?ProductId=9NRWMJP3717K
    echo 2. Descargar desde: https://www.python.org/downloads/
    echo 3. Ejecutar: instalar_completo.bat
)

echo.
echo 🔍 Verificando pip...
python -m pip --version 2>nul
if %errorlevel% equ 0 (
    echo ✅ pip está disponible
) else (
    echo ❌ pip NO está disponible
)

echo.
echo 🔍 Verificando dependencias...

set packages=pandas numpy streamlit plotly openpyxl

for %%p in (%packages%) do (
    python -c "import %%p; print('✅ %%p:', %%p.__version__)" 2>nul && (
        echo ✅ %%p está instalado
    ) || (
        echo ❌ %%p NO está instalado
    )
)

echo.
echo 🔍 Verificando archivos del sistema...

set files=data_processor.py web_interface.py test_system.py

for %%f in (%files%) do (
    if exist "%%f" (
        echo ✅ %%f encontrado
    ) else (
        echo ❌ %%f NO encontrado
    )
)

echo.
echo 🔍 Verificando archivos de datos...

set datafiles=Listado_transacciones_capturadas-izipay.csv ventas_20250923_culqi.csv secured.csv Resumen_Facturación_facebook.csv

for %%f in (%datafiles%) do (
    if exist "%%f" (
        echo ✅ %%f encontrado
    ) else (
        echo ❌ %%f NO encontrado
    )
)

echo.
echo 📊 RESUMEN:
echo.

REM Contar archivos encontrados
set /a found_system=0
set /a found_data=0

for %%f in (%files%) do (
    if exist "%%f" set /a found_system+=1
)

for %%f in (%datafiles%) do (
    if exist "%%f" set /a found_data+=1
)

echo Archivos del sistema: %found_system%/3
echo Archivos de datos: %found_data%/4

echo.
if %found_system% equ 3 (
    if %found_data% geq 1 (
        echo 🎉 El sistema está listo para usar!
        echo.
        echo 🚀 Ejecuta: iniciar_sistema.bat
    ) else (
        echo ⚠️ Faltan archivos de datos
        echo Asegúrate de tener al menos un archivo CSV en el directorio
    )
) else (
    echo ❌ Faltan archivos del sistema
    echo Descarga todos los archivos del proyecto
)

echo.
pause