#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final del ajuste de Facebook con redondeo
"""

import math
from data_processor import PaymentDataProcessor

def test_final():
    print("=" * 60)
    print("TEST FINAL - FACEBOOK ADS CON REDONDEO")
    print("=" * 60)
    
    # Simulación del cálculo para el 14 de julio
    reportado = 676.71
    real_cobrado = 751.90
    
    factor = 1.1111
    calculado = reportado * factor
    redondeado = math.ceil(calculado)
    
    print(f"📊 CÁLCULO PARA 14 JULIO 2025:")
    print(f"Monto reportado Facebook: S/ {reportado:.2f}")
    print(f"Factor aplicado: {factor} (11.11%)")
    print(f"Calculado: S/ {calculado:.2f}")
    print(f"Redondeado hacia arriba: S/ {redondeado:.2f}")
    print(f"Real cobrado: S/ {real_cobrado:.2f}")
    print(f"Diferencia: S/ {abs(real_cobrado - redondeado):.2f}")
    
    if redondeado >= real_cobrado:
        print("✅ El redondeo cubre el gasto real")
    else:
        print("⚠️ El redondeo no cubre completamente el gasto real")
    
    print(f"\n🧪 PROBANDO CON EL SISTEMA:")
    
    # Probar con el sistema real
    processor = PaymentDataProcessor()
    processor.load_facebook_data("Resumen_Facturación_facebook.csv")
    unified_df = processor.unify_data()
    
    facebook_data = unified_df[unified_df['processor'] == 'Facebook']
    
    # Buscar la transacción del 14 de julio
    import pandas as pd
    fecha_objetivo = pd.to_datetime('2025-07-14')
    
    transaccion_julio = facebook_data[facebook_data['date'].dt.date == fecha_objetivo.date()]
    
    if len(transaccion_julio) > 0:
        row = transaccion_julio.iloc[0]
        print(f"Monto reportado: S/ {row.get('amount_reported', 0):.2f}")
        print(f"Ajuste impuestos: S/ {row.get('tax_adjustment', 0):.2f}")
        print(f"Gasto real calculado: S/ {abs(row.get('amount_gross', 0)):.2f}")
        
        gasto_calculado = abs(row.get('amount_gross', 0))
        if abs(gasto_calculado - 752) < 1:  # 752 es el redondeo de 751.89
            print("✅ Sistema funcionando correctamente")
        else:
            print(f"⚠️ Verificar cálculo: esperado ~752, obtenido {gasto_calculado}")
    else:
        print("❌ No se encontró transacción del 14 julio")
    
    print(f"\n💡 RESUMEN:")
    print(f"• Factor: 11.11% (más preciso para julio)")
    print(f"• Redondeo: Hacia arriba (conservador)")
    print(f"• Resultado: S/ 752.00 vs S/ 751.90 real")
    print(f"• Diferencia: +S/ 0.10 (margen de seguridad)")

if __name__ == "__main__":
    test_final()