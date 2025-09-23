#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de diferencias entre montos reportados por Facebook y montos realmente cobrados
"""

import pandas as pd

# Datos proporcionados por el usuario
datos_reales = [
    {"fecha": "14/07/2025", "codigo": "XPDH7VYSU2", "monto_real": 751.90},
    {"fecha": "21/07/2025", "codigo": "KCVNZXLSU2", "monto_real": 745.24},
    {"fecha": "17/07/2025", "codigo": "WUPNAVCTU2", "monto_real": 746.03},
    {"fecha": "25/07/2025", "codigo": "7XT63V8TU2", "monto_real": 740.84},
    {"fecha": "28/07/2025", "codigo": "C7LRLWQSU2", "monto_real": 743.33}
]

# Montos reportados por Facebook (del archivo CSV)
datos_facebook = [
    {"fecha": "14/07/2025", "monto_reportado": 676.71},
    {"fecha": "21/07/2025", "monto_reportado": 673.89},
    {"fecha": "17/07/2025", "monto_reportado": 674.43},
    {"fecha": "25/07/2025", "monto_reportado": 670.07},
    {"fecha": "28/07/2025", "monto_reportado": 670.24}
]

print("=" * 80)
print("ANÁLISIS DE DIFERENCIAS FACEBOOK ADS")
print("Montos Reportados vs Montos Realmente Cobrados")
print("=" * 80)
print()

# Crear DataFrame combinado
df_real = pd.DataFrame(datos_reales)
df_facebook = pd.DataFrame(datos_facebook)

# Combinar datos
df_analisis = pd.merge(df_real, df_facebook, on='fecha')

# Calcular diferencias y porcentajes
df_analisis['diferencia'] = df_analisis['monto_real'] - df_analisis['monto_reportado']
df_analisis['porcentaje_aumento'] = (df_analisis['diferencia'] / df_analisis['monto_reportado']) * 100

print("DETALLE POR TRANSACCIÓN:")
print("-" * 80)
print(f"{'Fecha':<12} {'Código':<12} {'Reportado':<10} {'Real':<10} {'Diferencia':<10} {'% Aumento':<10}")
print("-" * 80)

for _, row in df_analisis.iterrows():
    print(f"{row['fecha']:<12} {row['codigo']:<12} S/ {row['monto_reportado']:<7.2f} S/ {row['monto_real']:<7.2f} S/ {row['diferencia']:<7.2f} {row['porcentaje_aumento']:<7.2f}%")

print("-" * 80)

# Estadísticas
promedio_diferencia = df_analisis['diferencia'].mean()
promedio_porcentaje = df_analisis['porcentaje_aumento'].mean()
min_porcentaje = df_analisis['porcentaje_aumento'].min()
max_porcentaje = df_analisis['porcentaje_aumento'].max()
desviacion_porcentaje = df_analisis['porcentaje_aumento'].std()

print()
print("ESTADÍSTICAS:")
print(f"Diferencia promedio: S/ {promedio_diferencia:.2f}")
print(f"Porcentaje promedio de aumento: {promedio_porcentaje:.2f}%")
print(f"Porcentaje mínimo: {min_porcentaje:.2f}%")
print(f"Porcentaje máximo: {max_porcentaje:.2f}%")
print(f"Desviación estándar: {desviacion_porcentaje:.2f}%")

print()
print("CONCLUSIÓN:")
if desviacion_porcentaje < 1.0:
    print(f"✅ El aumento es RELATIVAMENTE FIJO: ~{promedio_porcentaje:.1f}%")
    print(f"   Recomendación: Usar {promedio_porcentaje:.1f}% como factor de ajuste")
else:
    print(f"⚠️ El aumento es VARIABLE: {min_porcentaje:.1f}% - {max_porcentaje:.1f}%")
    print(f"   Promedio: {promedio_porcentaje:.1f}% ± {desviacion_porcentaje:.1f}%")

print()
print("POSIBLES CAUSAS DEL AUMENTO:")
print("• IGV (18% en Perú)")
print("• Comisiones bancarias internacionales")
print("• Tipo de cambio USD -> PEN")
print("• Comisiones de procesamiento de tarjeta")

# Verificar si es aproximadamente 18% (IGV)
if 17 <= promedio_porcentaje <= 19:
    print(f"\n💡 NOTA: El {promedio_porcentaje:.1f}% es muy cercano al IGV peruano (18%)")
    print("   Probablemente el archivo de Facebook no incluye impuestos")