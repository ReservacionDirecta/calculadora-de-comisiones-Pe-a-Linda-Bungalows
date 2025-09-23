@echo off
echo ========================================
echo  Test Período 8-14 Julio 2025
echo ========================================
echo.

echo 1. Debug de fechas específicas...
C:\Python313\python.exe debug_fechas.py

echo.
echo 2. Abriendo interfaz web...
echo   - Filtra por fechas: 8-14 julio 2025
echo   - Revisa la sección "Facebook Ads"
echo.

C:\Python313\python.exe -m streamlit run web_interface.py

pause