#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejemplo de gastos adicionales típicos para un negocio hotelero
"""

import streamlit as st
from datetime import datetime, timedelta

def agregar_gastos_ejemplo():
    """Agrega gastos de ejemplo para demostración"""
    
    gastos_ejemplo = [
        {
            'nombre': 'Mantenimiento de piscina',
            'monto': 450.00,
            'fecha': datetime.now().date() - timedelta(days=5),
            'id': 0
        },
        {
            'nombre': 'Servicios de limpieza',
            'monto': 320.00,
            'fecha': datetime.now().date() - timedelta(days=3),
            'id': 1
        },
        {
            'nombre': 'Suministros de cocina',
            'monto': 180.50,
            'fecha': datetime.now().date() - timedelta(days=2),
            'id': 2
        },
        {
            'nombre': 'Reparación de aire acondicionado',
            'monto': 275.00,
            'fecha': datetime.now().date() - timedelta(days=1),
            'id': 3
        },
        {
            'nombre': 'Jardinería y paisajismo',
            'monto': 200.00,
            'fecha': datetime.now().date(),
            'id': 4
        }
    ]
    
    return gastos_ejemplo

def mostrar_resumen_gastos():
    """Muestra un resumen de tipos de gastos comunes"""
    
    print("=" * 60)
    print("TIPOS DE GASTOS ADICIONALES COMUNES")
    print("Para Negocios Hoteleros/Turísticos")
    print("=" * 60)
    
    categorias_gastos = {
        "🏊 Mantenimiento": [
            "Piscina y áreas acuáticas",
            "Aire acondicionado",
            "Plomería y electricidad",
            "Pintura y reparaciones"
        ],
        "🧹 Servicios": [
            "Limpieza y lavandería",
            "Jardinería",
            "Seguridad",
            "Recepción y atención"
        ],
        "🍽️ Suministros": [
            "Cocina y restaurante",
            "Amenities para huéspedes",
            "Productos de limpieza",
            "Lencería y toallas"
        ],
        "📋 Administrativos": [
            "Servicios profesionales",
            "Seguros",
            "Licencias y permisos",
            "Marketing offline"
        ],
        "⚡ Servicios Básicos": [
            "Electricidad",
            "Agua y desagüe",
            "Internet y telefonía",
            "Gas"
        ]
    }
    
    for categoria, items in categorias_gastos.items():
        print(f"\n{categoria}")
        print("-" * 30)
        for item in items:
            print(f"  • {item}")
    
    print(f"\n💡 CONSEJOS:")
    print("• Registra gastos regularmente para mejor control")
    print("• Categoriza gastos para análisis detallado")
    print("• Mantén respaldos de facturas y comprobantes")
    print("• Revisa tendencias mensuales de gastos")

if __name__ == "__main__":
    mostrar_resumen_gastos()
    
    print(f"\n🧪 GASTOS DE EJEMPLO:")
    gastos = agregar_gastos_ejemplo()
    total = sum([g['monto'] for g in gastos])
    
    print("-" * 60)
    for gasto in gastos:
        print(f"{gasto['fecha']} | {gasto['nombre']:<25} | S/ {gasto['monto']:>8.2f}")
    print("-" * 60)
    print(f"{'TOTAL':<36} | S/ {total:>8.2f}")
    
    print(f"\n🚀 Para probar la funcionalidad:")
    print("   test_gastos_adicionales.bat")