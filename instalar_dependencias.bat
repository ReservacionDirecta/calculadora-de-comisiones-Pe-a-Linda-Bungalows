@echo off
echo ========================================
echo  Instalando Dependencias Faltantes
echo  Peña Linda Bungalows
echo ========================================
echo.

echo 📦 Instalando pandas...
python -m pip install pandas --quiet
if %errorlevel% equ 0 (echo ✅ pandas instalado) else (echo ❌ Error con pandas)

echo 📦 Instalando numpy...
python -m pip install numpy --quiet
if %errorlevel% equ 0 (echo ✅ numpy instalado) else (echo ❌ Error con numpy)

echo 📦 Instalando streamlit...
python -m pip install streamlit --quiet
if %errorlevel% equ 0 (echo ✅ streamlit instalado) else (echo ❌ Error con streamlit)

echo 📦 Instalando plotly...
python -m pip install plotly --quiet
if %errorlevel% equ 0 (echo ✅ plotly instalado) else (echo ❌ Error con plotly)

echo 📦 Instalando openpyxl...
python -m pip install openpyxl --quiet
if %errorlevel% equ 0 (echo ✅ openpyxl instalado) else (echo ❌ Error con openpyxl)

echo 📦 Instalando python-dateutil...
python -m pip install python-dateutil --quiet
if %errorlevel% equ 0 (echo ✅ python-dateutil instalado) else (echo ❌ Error con python-dateutil)

echo.
echo ✅ ¡Instalación completada!
echo.
echo 🧪 Probando el sistema...
python test_system.py

pause