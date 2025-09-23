@echo off
echo ========================================
echo  Prueba Rápida del Sistema
echo ========================================
echo.

REM Usar la ruta completa de Python que sabemos que funciona
C:\Python313\python.exe test_system.py

echo.
echo ¿Abrir interfaz web? (s/n)
set /p web="Respuesta: "

if /i "%web%"=="s" (
    echo Abriendo interfaz web...
    C:\Python313\python.exe -m streamlit run web_interface.py
)

pause