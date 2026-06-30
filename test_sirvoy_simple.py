#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
from data_processor import PaymentDataProcessor

processor = PaymentDataProcessor()
df = processor.load_sirvoy_data("payments_export-2025-11-27_17_29_18.csv")
print(f"Registros cargados: {len(df)}")
if not df.empty:
    print("\nPrimeras 3 filas:")
    print(df.head(3))
    print(f"\nColumnas: {list(df.columns)}")
    print(f"\nTotal monto: {df['monto_eur'].sum():,.2f}")


