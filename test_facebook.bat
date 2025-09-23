@echo off
echo ========================================
echo  Test Facebook Ads con Ajuste 10.8%
echo ========================================
echo.

echo 1. Ejecutando análisis de diferencias...
C:\Python313\python.exe analisis_facebook.py

echo.
echo 2. Probando sistema con factor de ajuste...
C:\Python313\python.exe test_system.py

echo.
echo ✅ Análisis completado
echo.
echo 📊 RESUMEN DEL FACTOR DE AJUSTE:
echo • Facebook reporta montos SIN impuestos
echo • El cobro real es 10.8%% mayor
echo • Factor aplicado: 1.108
echo • Causas: IGV, comisiones bancarias, tipo de cambio
echo.

pause