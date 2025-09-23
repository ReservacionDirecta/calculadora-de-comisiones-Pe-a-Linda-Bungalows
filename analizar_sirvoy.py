#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de cobros de Sirvoy para calcular el factor de ajuste EUR -> PEN
"""

import pandas as pd
import re
from datetime import datetime

def analizar_sirvoy():
    print("=" * 60)
    print("ANÁLISIS DE COBROS SIRVOY")
    print("Cálculo del Factor de Ajuste EUR -> PEN")
    print("=" * 60)
    
    # Leer archivo
    df = pd.read_csv("cobros sirvoy.csv")
    
    # Limpiar y procesar datos
    df.columns = ['fecha', 'descripcion', 'enlace', 'accion', 'monto', 'detalle']
    
    # Convertir fechas
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
    
    # Filtrar solo recargas (pagos realizados)
    recargas = df[df['descripcion'].str.contains('Recargar cuenta', na=False)].copy()
    
    # Limpiar montos (formato europeo €149,00)
    def limpiar_monto_eur(monto_str):
        if pd.isna(monto_str) or monto_str == '':
            return 0
        # Remover € y convertir coma a punto
        monto_clean = str(monto_str).replace('€', '').replace(',', '.').strip()
        try:
            return float(monto_clean)
        except:
            return 0
    
    recargas['monto_eur'] = recargas['monto'].apply(limpiar_monto_eur)
    
    # Filtrar montos válidos
    recargas = recargas[recargas['monto_eur'] > 0]
    
    print(f"📊 DATOS ENCONTRADOS:")
    print(f"Total de recargas: {len(recargas)}")
    print(f"Período: {recargas['fecha'].min().strftime('%d/%m/%Y')} - {recargas['fecha'].max().strftime('%d/%m/%Y')}")
    
    # Mostrar últimas recargas
    print(f"\n💰 ÚLTIMAS RECARGAS (EUR):")
    print("-" * 60)
    print(f"{'Fecha':<12} {'Monto EUR':<12} {'Descripción'}")
    print("-" * 60)
    
    for _, row in recargas.head(10).iterrows():
        fecha_str = row['fecha'].strftime('%d/%m/%Y') if pd.notna(row['fecha']) else 'N/A'
        print(f"{fecha_str:<12} €{row['monto_eur']:<11.2f} Recarga cuenta")
    
    # Análisis de montos más comunes
    montos_comunes = recargas['monto_eur'].value_counts().head(5)
    print(f"\n📈 MONTOS MÁS FRECUENTES:")
    print("-" * 30)
    for monto, frecuencia in montos_comunes.items():
        print(f"€{monto:>6.2f}: {frecuencia:>3} veces")
    
    # Estadísticas
    total_eur = recargas['monto_eur'].sum()
    promedio_eur = recargas['monto_eur'].mean()
    
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"Total recargado: €{total_eur:,.2f}")
    print(f"Promedio por recarga: €{promedio_eur:.2f}")
    
    # Estimación del tipo de cambio y factor
    print(f"\n💡 PARA CALCULAR EL FACTOR DE AJUSTE:")
    print("Necesitamos los montos reales cobrados en PEN")
    print("Ejemplo:")
    print("- Si €149.00 se cobra como S/ 580.00")
    print("- Tipo de cambio implícito: 580/149 = 3.89 PEN/EUR")
    print("- Si el tipo de cambio oficial es 3.70, el factor sería: 3.89/3.70 = 1.051 (5.1% adicional)")
    
    # Sugerencia de montos para verificar
    monto_comun = montos_comunes.index[0]
    print(f"\n🎯 SUGERENCIA:")
    print(f"Verifica cuánto se cobra realmente en PEN por €{monto_comun:.2f}")
    print("Con esa información podremos calcular el factor exacto")
    
    return recargas

if __name__ == "__main__":
    recargas_df = analizar_sirvoy()