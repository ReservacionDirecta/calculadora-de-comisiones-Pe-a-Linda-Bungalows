#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Procesamiento de Datos de Pagos - Peña Linda Bungalows
Procesa transacciones de múltiples fuentes: Izipay, Culqi, y transferencias directas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional, Tuple
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PaymentDataProcessor:
    """Procesador principal para datos de pagos de múltiples fuentes"""
    
    def __init__(self):
        self.izipay_data = None
        self.culqi_data = None
        self.secured_data = None
        self.sirvoy_data = None
        self.facebook_data = None
        self.unified_data = None
        
        # Mapeo de columnas para unificación
        self.column_mapping = {
            'izipay': {
                'transaction_id': 'Transacción UUID',
                'date': 'Fecha del pago',
                'amount': 'Importe del pago',
                'status': 'Estado',
                'payment_method': 'Medio de pago',
                'customer_name': 'Comprador',
                'customer_email': 'E-mail comprador',
                'currency': 'Moneda',
                'commission': 'Comisión',
                'card_number': 'Número de tarjeta',
                'authorization_code': 'Número autorización',
                'country': 'País del comprador'
            },
            'culqi': {
                'transaction_id': 'ID Venta',
                'date': 'Fecha de la transaccion',
                'time': 'Hora de la transaccion',
                'amount': 'Monto VENTA',
                'final_amount': 'Venta Final',
                'status': 'Estado',
                'payment_method': 'Marca',
                'customer_name': 'Nombres',
                'customer_lastname': 'Apellidos',
                'customer_email': 'Correo Electronico',
                'currency': 'Moneda',
                'commission_culqi': 'Comision Culqi',
                'commission_issuer': 'Comision Emisor',
                'commission_total': 'Comision TOTAL',
                'card_last4': 'Ult. 4 digitos',
                'authorization_code': 'Codigo Autorizacion',
                'country': 'Pais'
            },
            'secured': {
                'transaction_id': 'payment-list-item',
                'date': 'payment-list-item 2',
                'payment_type': 'payment-list-item 3',
                'description': 'tippy',
                'booking_type': 'payment-list-item 4',
                'booking_id': 'payment-list-item 5',
                'amount': 'payment-list-item 6'
            },
            'facebook': {
                'date': 'Fecha',
                'transaction_id': 'Identificador de la transacción',
                'payment_method': 'Método de pago',
                'amount': 'Importe',
                'currency': 'Divisa'
            },
            'sirvoy': {
                'date': 'fecha',
                'description': 'descripcion',
                'amount': 'monto',
                'currency': 'EUR'
            }
        }
    
    def load_izipay_data(self, file_path: str) -> pd.DataFrame:
        """Carga y procesa datos de Izipay"""
        try:
            # Izipay usa punto y coma como separador
            df = pd.read_csv(file_path, sep=';', encoding='utf-8')
            logger.info(f"Cargados {len(df)} registros de Izipay")
            
            # Limpiar y procesar datos
            df = self._clean_izipay_data(df)
            self.izipay_data = df
            return df
            
        except Exception as e:
            logger.error(f"Error cargando datos de Izipay: {e}")
            return pd.DataFrame()
    
    def load_culqi_data(self, file_path: str) -> pd.DataFrame:
        """Carga y procesa datos de Culqi"""
        try:
            # Culqi usa coma como separador
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Cargados {len(df)} registros de Culqi")
            
            # Limpiar y procesar datos
            df = self._clean_culqi_data(df)
            self.culqi_data = df
            return df
            
        except Exception as e:
            logger.error(f"Error cargando datos de Culqi: {e}")
            return pd.DataFrame()
    
    def load_secured_data(self, file_path: str) -> pd.DataFrame:
        """Carga y procesa datos de transferencias directas"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Cargados {len(df)} registros de transferencias directas")
            
            # Limpiar y procesar datos
            df = self._clean_secured_data(df)
            self.secured_data = df
            return df
            
        except Exception as e:
            logger.error(f"Error cargando datos de transferencias: {e}")
            return pd.DataFrame()
    
    def load_sirvoy_data(self, file_path: str) -> pd.DataFrame:
        """Carga y procesa datos de Sirvoy (cobros mensuales en EUR)"""
        try:
            # Leer archivo CSV
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Renombrar columnas
            df.columns = ['fecha', 'descripcion', 'enlace', 'accion', 'monto', 'detalle']
            
            # Filtrar solo recargas (pagos realizados)
            recargas = df[df['descripcion'].str.contains('Recargar cuenta', na=False)].copy()
            
            if recargas.empty:
                logger.warning("No se encontraron recargas de Sirvoy")
                return pd.DataFrame()
            
            # Limpiar y procesar datos
            df_clean = self._clean_sirvoy_data(recargas)
            self.sirvoy_data = df_clean
            logger.info(f"Cargados {len(df_clean)} registros de Sirvoy")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error cargando datos de Sirvoy: {e}")
            return pd.DataFrame()
    
    def load_facebook_data(self, file_path: str) -> pd.DataFrame:
        """Carga y procesa datos de Facebook Ads"""
        try:
            # Leer todo el archivo para procesarlo manualmente
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Buscar las secciones de datos
            facebook_records = []
            current_section = None
            headers = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Identificar secciones
                if "Pago de Anuncios de Meta" in line:
                    current_section = "payments"
                    continue
                
                # Buscar headers
                if current_section == "payments" and "Fecha,Identificador" in line:
                    headers = line.split(',')
                    continue
                
                # Procesar datos de pagos
                if current_section == "payments" and headers and line and not line.startswith("Método de pago") and not line.startswith("Importe total"):
                    # Verificar si es una línea de datos válida
                    if line.count(',') >= 3 and not line.startswith(','):
                        parts = line.split(',')
                        if len(parts) >= 4 and parts[0] and parts[1]:  # Fecha e ID no vacíos
                            facebook_records.append({
                                'Fecha': parts[0],
                                'Identificador de la transacción': parts[1],
                                'Método de pago': parts[2] if len(parts) > 2 else 'Visa',
                                'Importe': parts[3] if len(parts) > 3 else '0',
                                'Divisa': parts[4] if len(parts) > 4 else 'PEN'
                            })
            
            if not facebook_records:
                logger.warning("No se encontraron transacciones válidas en el archivo de Facebook")
                return pd.DataFrame()
            
            # Crear DataFrame
            df = pd.DataFrame(facebook_records)
            logger.info(f"Cargados {len(df)} registros de Facebook Ads")
            
            # Limpiar y procesar datos
            df = self._clean_facebook_data(df)
            self.facebook_data = df
            return df
            
        except Exception as e:
            logger.error(f"Error cargando datos de Facebook: {e}")
            return pd.DataFrame()
    
    def _clean_izipay_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Izipay"""
        # Convertir fechas
        df['Fecha del pago'] = pd.to_datetime(df['Fecha del pago'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df['Fecha de captura'] = pd.to_datetime(df['Fecha de captura'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        
        # Convertir importes a numérico
        df['Importe del pago'] = pd.to_numeric(df['Importe del pago'], errors='coerce')
        df['Comisión'] = pd.to_numeric(df['Comisión'], errors='coerce')
        
        # Agregar columna de fuente
        df['source'] = 'Izipay'
        
        # Limpiar estados
        df['Estado'] = df['Estado'].str.strip()
        
        return df
    
    def _clean_culqi_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Culqi"""
        # Combinar fecha y hora
        df['datetime'] = pd.to_datetime(
            df['Fecha de la transaccion'] + ' ' + df['Hora de la transaccion'],
            format='%Y-%m-%d %H:%M:%S',
            errors='coerce'
        )
        
        # Convertir importes a numérico
        numeric_columns = ['Monto VENTA', 'Venta Final', 'Comision Culqi', 'Comision Emisor', 'Comision TOTAL']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Agregar columna de fuente
        df['source'] = 'Culqi'
        
        # Combinar nombres
        df['customer_full_name'] = (df['Nombres'].fillna('') + ' ' + df['Apellidos'].fillna('')).str.strip()
        
        return df
    
    def _clean_secured_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de pagos recibidos (solo no-tarjeta)"""
        # Renombrar columnas para mayor claridad
        df.columns = ['transaction_id', 'date', 'payment_type', 'description', 'booking_type', 'booking_id', 'amount']
        
        # Convertir fechas
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y %H:%M', errors='coerce')
        
        # Limpiar y convertir importes (formato europeo con coma decimal)
        df['amount'] = df['amount'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        
        # FILTRAR: Solo pagos que NO sean "Pago con tarjeta"
        # Estos ya están procesados por Izipay/Culqi
        df = df[df['payment_type'] != 'Pago con tarjeta']
        
        # Agregar columna de fuente
        df['source'] = 'Pago Directo'
        
        logger.info(f"Filtrados pagos directos: {len(df)} registros (excluidos pagos con tarjeta)")
        
        return df
    
    def _clean_facebook_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Facebook Ads"""
        if df.empty:
            return df
        
        # Convertir fechas (formato DD/MM/YYYY)
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        
        # Convertir importes a numérico (formato europeo con coma decimal)
        if 'Importe' in df.columns:
            # Limpiar formato: "670,02" -> 670.02
            df['Importe'] = df['Importe'].astype(str).str.replace('"', '').str.replace('.', '').str.replace(',', '.')
            df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce')
        
        # Limpiar método de pago
        if 'Método de pago' in df.columns:
            df['Método de pago'] = df['Método de pago'].astype(str).str.replace('"', '')
        
        # Agregar columna de fuente
        df['source'] = 'Facebook Ads'
        
        # Filtrar filas vacías o con importes inválidos
        df = df.dropna(subset=['Fecha', 'Importe'])
        df = df[df['Importe'] > 0]  # Solo importes positivos
        
        return df
    
    def _clean_sirvoy_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de cobros de la plataforma Sirvoy (EUR)"""
        if df.empty:
            return df
        
        # Convertir fechas (DD/MM/YYYY)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
        
        # Normalizar montos en EUR: admite formatos "€149,00" y "€149.00"
        if 'monto' in df.columns:
            serie = df['monto'].astype(str).str.strip().str.replace('€', '').str.replace(' ', '')
            # Si usa coma como decimal, convertirla a punto. Mantener punto si ya es decimal
            serie = serie.apply(lambda s: s.replace('.', '') if (',' in s and '.' in s and s.find('.') < s.find(',')) else s)
            serie = serie.str.replace(',', '.')
            df['monto_eur'] = pd.to_numeric(serie, errors='coerce')
        
        # Filtrar registros válidos
        df = df.dropna(subset=['fecha', 'monto_eur'])
        df = df[df['monto_eur'] > 0]
        
        # Marcar fuente
        df['source'] = 'Sirvoy'
        
        logger.info(f"Filtrados cobros Sirvoy: {len(df)} registros válidos")
        return df
    
    def unify_data(self) -> pd.DataFrame:
        """Unifica datos de todas las fuentes en un formato común"""
        unified_records = []
        
        # Procesar datos de Izipay
        if self.izipay_data is not None and not self.izipay_data.empty:
            for _, row in self.izipay_data.iterrows():
                amount_gross = row.get('Importe del pago', 0)
                commission_processor = row.get('Comisión', 0)
                commission_chamba = amount_gross * 0.05  # 5% Chamba Digital
                amount_net = amount_gross - commission_processor - commission_chamba
                
                record = {
                    'transaction_id': row.get('Transacción UUID', ''),
                    'date': row.get('Fecha del pago'),
                    'amount_gross': amount_gross,
                    'amount_net': amount_net,
                    'amount': amount_gross,  # Para compatibilidad
                    'amount_reported': amount_gross,  # Para Izipay, reportado = real
                    'tax_adjustment': 0,  # Sin ajuste para Izipay
                    'currency': row.get('Moneda', 'PEN'),
                    'status': row.get('Estado', ''),
                    'payment_method': row.get('Medio de pago', ''),
                    'customer_name': row.get('Comprador', ''),
                    'customer_email': row.get('E-mail comprador', ''),
                    'commission_processor': commission_processor,
                    'commission_chamba': commission_chamba,
                    'commission_total': commission_processor + commission_chamba,
                    'commission': commission_processor,  # Para compatibilidad
                    'card_number': row.get('Número de tarjeta', ''),
                    'authorization_code': row.get('Número autorización', ''),
                    'country': row.get('País del comprador', ''),
                    'source': 'Izipay',
                    'processor': 'Izipay',
                    'category': 'Pago con Tarjeta'
                }
                unified_records.append(record)
        
        # Procesar datos de Culqi
        if self.culqi_data is not None and not self.culqi_data.empty:
            for _, row in self.culqi_data.iterrows():
                amount_gross = row.get('Monto VENTA', 0)
                commission_processor = row.get('Comision TOTAL', 0)
                commission_chamba = amount_gross * 0.05  # 5% Chamba Digital
                amount_net = amount_gross - commission_processor - commission_chamba
                
                record = {
                    'transaction_id': row.get('ID Venta', ''),
                    'date': row.get('datetime'),
                    'amount_gross': amount_gross,
                    'amount_net': amount_net,
                    'amount': amount_gross,  # Para compatibilidad
                    'amount_reported': amount_gross,  # Para Culqi, reportado = real
                    'tax_adjustment': 0,  # Sin ajuste para Culqi
                    'currency': row.get('Moneda', 'PEN'),
                    'status': row.get('Estado', ''),
                    'payment_method': row.get('Marca', ''),
                    'customer_name': row.get('customer_full_name', ''),
                    'customer_email': row.get('Correo Electronico', ''),
                    'commission_processor': commission_processor,
                    'commission_chamba': commission_chamba,
                    'commission_total': commission_processor + commission_chamba,
                    'commission': commission_processor,  # Para compatibilidad
                    'card_number': f"****{row.get('Ult. 4 digitos', '')}",
                    'authorization_code': row.get('Codigo Autorizacion', ''),
                    'country': row.get('Pais', ''),
                    'source': 'Culqi',
                    'processor': 'Culqi',
                    'category': 'Pago con Tarjeta'
                }
                unified_records.append(record)
        
        # Procesar datos de transferencias directas
        if self.secured_data is not None and not self.secured_data.empty:
            for _, row in self.secured_data.iterrows():
                amount_gross = row.get('amount', 0)
                commission_chamba = amount_gross * 0.05  # 5% Chamba Digital
                amount_net = amount_gross - commission_chamba  # Sin comisión de procesador
                
                record = {
                    'transaction_id': row.get('transaction_id', ''),
                    'date': row.get('date'),
                    'amount_gross': amount_gross,
                    'amount_net': amount_net,
                    'amount': amount_gross,  # Para compatibilidad
                    'amount_reported': amount_gross,  # Para pagos directos, reportado = real
                    'tax_adjustment': 0,  # Sin ajuste para pagos directos
                    'currency': 'PEN',
                    'status': 'Completado',
                    'payment_method': row.get('payment_type', ''),
                    'customer_name': '',
                    'customer_email': '',
                    'commission_processor': 0,  # Sin comisión de procesador
                    'commission_chamba': commission_chamba,
                    'commission_total': commission_chamba,
                    'commission': 0,  # Para compatibilidad
                    'card_number': '',
                    'authorization_code': '',
                    'country': 'PE',
                    'source': 'Pago Directo',
                    'processor': 'Directo',
                    'category': row.get('payment_type', 'Pago Directo')
                }
                unified_records.append(record)
        
        # Procesar datos de Facebook Ads
        if self.facebook_data is not None and not self.facebook_data.empty:
            for _, row in self.facebook_data.iterrows():
                amount_reportado = row.get('Importe', 0)
                # Aplicar factor de ajuste del 11.11% por impuestos y comisiones bancarias
                # Basado en datos reales: 676.71 → 751.90 (11.11% adicional)
                factor_ajuste = 1.1111  # 11.11% adicional
                amount_calculado = amount_reportado * factor_ajuste
                
                # Redondear hacia arriba para ser más conservador en los gastos
                import math
                amount_real = math.ceil(amount_calculado)
                
                # Facebook Ads es un GASTO, no un ingreso
                # No aplicamos comisión de Chamba Digital a gastos
                
                record = {
                    'transaction_id': row.get('Identificador de la transacción', ''),
                    'date': row.get('Fecha'),
                    'amount_gross': -amount_real,      # Negativo porque es gasto (monto real)
                    'amount_net': -amount_real,        # Sin comisiones adicionales
                    'amount': -amount_real,            # Para compatibilidad
                    'amount_reported': amount_reportado,  # Monto reportado por Facebook
                    'tax_adjustment': amount_real - amount_reportado,  # Diferencia por impuestos
                    'currency': row.get('Divisa', 'PEN'),
                    'status': 'Completado',
                    'payment_method': row.get('Método de pago', 'Facebook Ads'),
                    'customer_name': 'Facebook Ads',
                    'customer_email': '',
                    'commission_processor': 0,
                    'commission_chamba': 0,  # No aplicamos comisión a gastos
                    'commission_total': 0,
                    'commission': 0,  # Para compatibilidad
                    'card_number': '',
                    'authorization_code': '',
                    'country': 'PE',
                    'source': 'Facebook Ads',
                    'processor': 'Facebook',
                    'category': 'Gasto Publicitario'
                }
                unified_records.append(record)
        
        # Procesar cobros de plataforma Sirvoy (GASTO)
        if self.sirvoy_data is not None and not self.sirvoy_data.empty:
            for _, row in self.sirvoy_data.iterrows():
                amount_eur = row.get('monto_eur', 0)
                # Usamos tasa oficial estimada y un factor de ajuste por cargos/ITF
                # Ejemplo usado: €149.00 -> S/ 580.00 => tipo de cambio ~3.70 y factor ~1.051
                sirvoy_exchange_rate = 3.70
                sirvoy_adjustment_factor = 1.051
                amount_reportado = amount_eur * sirvoy_exchange_rate
                amount_calculado = amount_reportado * sirvoy_adjustment_factor
                import math
                amount_real = math.ceil(amount_calculado)
                
                record = {
                    'transaction_id': '',
                    'date': row.get('fecha'),
                    'amount_gross': -amount_real,      # Negativo porque es gasto
                    'amount_net': -amount_real,        # No aplicamos comisión adicional
                    'amount': -amount_real,            # Para compatibilidad
                    'amount_reported': amount_reportado,  # Coste estimado a TC oficial
                    'tax_adjustment': amount_real - amount_reportado,  # Diferencia por cargos
                    'currency': 'PEN',
                    'status': 'Completado',
                    'payment_method': 'Sirvoy Plataforma',
                    'customer_name': 'Sirvoy',
                    'customer_email': '',
                    'commission_processor': 0,
                    'commission_chamba': 0,
                    'commission_total': 0,
                    'commission': 0,
                    'card_number': '',
                    'authorization_code': '',
                    'country': 'PE',
                    'source': 'Sirvoy',
                    'processor': 'Sirvoy',
                    'category': 'Gasto Plataforma'
                }
                unified_records.append(record)
        
        # Procesar datos de Facebook Ads
        if self.facebook_data is not None and not self.facebook_data.empty:
            for _, row in self.facebook_data.iterrows():
                amount_reportado = row.get('Importe', 0)
                # Aplicar factor de ajuste del 11.11% por impuestos y comisiones bancarias
                # Basado en datos reales: 676.71 → 751.90 (11.11% adicional)
                factor_ajuste = 1.1111  # 11.11% adicional
                amount_calculado = amount_reportado * factor_ajuste
                
                # Redondear hacia arriba para ser más conservador en los gastos
                import math
                amount_real = math.ceil(amount_calculado)
                
                # Facebook Ads es un GASTO, no un ingreso
                # No aplicamos comisión de Chamba Digital a gastos
                
                record = {
                    'transaction_id': row.get('Identificador de la transacción', ''),
                    'date': row.get('Fecha'),
                    'amount_gross': -amount_real,      # Negativo porque es gasto (monto real)
                    'amount_net': -amount_real,        # Sin comisiones adicionales
                    'amount': -amount_real,            # Para compatibilidad
                    'amount_reported': amount_reportado,  # Monto reportado por Facebook
                    'tax_adjustment': amount_real - amount_reportado,  # Diferencia por impuestos
                    'currency': row.get('Divisa', 'PEN'),
                    'status': 'Completado',
                    'payment_method': row.get('Método de pago', 'Facebook Ads'),
                    'customer_name': 'Facebook Ads',
                    'customer_email': '',
                    'commission_processor': 0,
                    'commission_chamba': 0,  # No aplicamos comisión a gastos
                    'commission_total': 0,
                    'commission': 0,  # Para compatibilidad
                    'card_number': '',
                    'authorization_code': '',
                    'country': 'PE',
                    'source': 'Facebook Ads',
                    'processor': 'Facebook',
                    'category': 'Gasto Publicitario'
                }
                unified_records.append(record)
        
        self.unified_data = pd.DataFrame(unified_records)
        logger.info(f"Datos unificados: {len(self.unified_data)} registros totales")
        
        return self.unified_data
    
    def get_summary_stats(self) -> Dict:
        """Genera estadísticas resumidas de los datos"""
        if self.unified_data is None or self.unified_data.empty:
            return {}
        
        stats = {
            'total_transactions': len(self.unified_data),
            'total_amount': self.unified_data['amount'].sum(),
            'total_commission': self.unified_data['commission'].sum(),
            'by_processor': self.unified_data.groupby('processor').agg({
                'amount': ['count', 'sum'],
                'commission': 'sum'
            }).round(2).to_dict(),
            'by_payment_method': self.unified_data.groupby('payment_method')['amount'].agg(['count', 'sum']).to_dict(),
            'date_range': {
                'start': self.unified_data['date'].min(),
                'end': self.unified_data['date'].max()
            }
        }
        
        return stats
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Filtra datos por rango de fechas"""
        if self.unified_data is None:
            return pd.DataFrame()
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        mask = (self.unified_data['date'] >= start) & (self.unified_data['date'] <= end)
        return self.unified_data[mask]
    
    def filter_by_processor(self, processor: str) -> pd.DataFrame:
        """Filtra datos por procesador de pagos"""
        if self.unified_data is None:
            return pd.DataFrame()
        
        return self.unified_data[self.unified_data['processor'] == processor]
    
    def filter_by_amount_range(self, min_amount: float, max_amount: float) -> pd.DataFrame:
        """Filtra datos por rango de montos"""
        if self.unified_data is None:
            return pd.DataFrame()
        
        mask = (self.unified_data['amount'] >= min_amount) & (self.unified_data['amount'] <= max_amount)
        return self.unified_data[mask]
    
    def export_unified_data(self, file_path: str, format: str = 'csv') -> bool:
        """Exporta datos unificados a archivo"""
        if self.unified_data is None or self.unified_data.empty:
            logger.warning("No hay datos para exportar")
            return False
        
        try:
            if format.lower() == 'csv':
                self.unified_data.to_csv(file_path, index=False, encoding='utf-8')
            elif format.lower() == 'excel':
                self.unified_data.to_excel(file_path, index=False)
            
            logger.info(f"Datos exportados a {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")
            return False


# Ejemplo de uso
if __name__ == "__main__":
    processor = PaymentDataProcessor()
    
    # Cargar datos de las diferentes fuentes
    processor.load_izipay_data("Listado_transacciones_capturadas-izipay.csv")
    processor.load_culqi_data("ventas_20250923_culqi.csv")
    processor.load_secured_data("secured.csv")
    processor.load_sirvoy_data("cobros sirvoy.csv")
    
    # Unificar datos
    unified_df = processor.unify_data()
    
    # Obtener estadísticas
    stats = processor.get_summary_stats()
    print("Estadísticas generales:")
    print(f"Total transacciones: {stats.get('total_transactions', 0)}")
    print(f"Monto total: S/ {stats.get('total_amount', 0):,.2f}")
    print(f"Comisiones totales: S/ {stats.get('total_commission', 0):,.2f}")
    
    # Exportar datos unificados
    processor.export_unified_data("transacciones_unificadas.csv")