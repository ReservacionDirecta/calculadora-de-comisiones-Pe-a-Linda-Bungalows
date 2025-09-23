@echo off
echo ========================================
echo  Test Gastos Adicionales
echo  Peña Linda Bungalows
echo ========================================
echo.

echo 🚀 Abriendo interfaz web con nueva funcionalidad...
echo.
echo 📋 INSTRUCCIONES:
echo 1. En la barra lateral, busca "💸 Gastos Adicionales"
echo 2. Haz clic en "➕ Agregar Gasto"
echo 3. Prueba agregando gastos como:
echo    - Mantenimiento: S/ 500.00
echo    - Servicios: S/ 300.00
echo    - Suministros: S/ 150.00
echo 4. Observa cómo se actualizan las métricas
echo 5. Revisa el gráfico "Desglose de Gastos"
echo 6. Exporta el reporte con gastos incluidos
echo.

C:\Python313\python.exe -m streamlit run web_interface.py

pause