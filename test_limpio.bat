@echo off
echo ========================================
echo  Test Sistema Limpio - Sin Errores
echo ========================================
echo.

echo 1. Probando sistema actualizado...
C:\Python313\python.exe test_system.py

echo.
echo 2. Abriendo interfaz web limpia...
echo   - Sin mensajes de debug
echo   - Sin warnings de Streamlit
echo   - Cálculos de Facebook corregidos
echo.

C:\Python313\python.exe -m streamlit run web_interface.py

pause