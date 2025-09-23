#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar el nuevo factor de ajuste del 11.11%
"""

import pandas as pd

def verificar_ajuste():
    print("=" * 60)
    print("VERIFICACIÓN DEL NUEVO FACTOR DE AJUSTE")
    print("=" * 60)
    
    # Datos reales proporcionados
    datos_verificacion = [
        {"fecha": "14/07/2025", "reportado": 676.71, "real": 751.90},
        {"fecha": "21/07/2025", "reportado": 673.89, "real": 745.24},
        {"fecha": "17/07/2025", "reportado": 674.43, "real": 746.03},
        {"fecha": "25/07/2025", "reportado": 670.07, "real": 740.84},
        {"fecha": "28/07/2025", "reportado": 670.24, "real": 743.33}
    ]
    
    factor_anterior = 1.108   # 10.8%
    factor_nuevo = 1.1111     # 11.11%
    
    print("COMPARACIÓN DE FACTORES:")
    print("-" * 60)
    print(f"{'Fecha':<12} {'Reportado':<10} {'Real':<10} {'Factor 10.8%':<12} {'Factor 11.11%':<12} {'Mejor':<8}")
    print("-" * 60)
    
    total_error_anterior = 0
    total_error_nuevo = 0
    
    for dato in datos_verificacion:
        reportado = dato['reportado']
        real = dato['real']
        
        calculado_anterior = reportado * factor_anterior
        calculado_nuevo = reportado * factor_nuevo
        
        error_anterior = abs(real - calculado_anterior)
        error_nuevo = abs(real - calculado_nuevo)
        
        mejor = "Nuevo" if error_nuevo < error_anterior else "Anterior"
        
        print(f"{dato['fecha']:<12} S/ {reportado:<7.2f} S/ {real:<7.2f} S/ {calculado_anterior:<9.2f} S/ {calculado_nuevo:<9.2f} {mejor:<8}")
        
        total_error_anterior += error_anterior
        total_error_nuevo += error_nuevo
    
    print("-" * 60)
    print(f"Error total anterior (10.8%): S/ {total_error_anterior:.2f}")
    print(f"Error total nuevo (11.11%): S/ {total_error_nuevo:.2f}")
    print(f"Mejora: S/ {total_error_anterior - total_error_nuevo:.2f}")
    
    print(f"\n✅ El factor 11.11% es {'MEJOR' if total_error_nuevo < total_error_anterior else 'PEOR'}")
    
    # Verificación específica para el 14 de julio
    print(f"\n🎯 VERIFICACIÓN ESPECÍFICA (14 julio):")
    reportado_julio = 676.71
    real_julio = 751.90
    calculado_nuevo_julio = reportado_julio * factor_nuevo
    
    print(f"Reportado: S/ {reportado_julio:.2f}")
    print(f"Real cobrado: S/ {real_julio:.2f}")
    print(f"Calculado (11.11%): S/ {calculado_nuevo_julio:.2f}")
    print(f"Diferencia: S/ {abs(real_julio - calculado_nuevo_julio):.2f}")
    
    if abs(real_julio - calculado_nuevo_julio) < 1.0:
        print("✅ Excelente precisión (diferencia < S/ 1.00)")
    elif abs(real_julio - calculado_nuevo_julio) < 5.0:
        print("✅ Buena precisión (diferencia < S/ 5.00)")
    else:
        print("⚠️ Precisión mejorable")

if __name__ == "__main__":
    verificar_ajuste()