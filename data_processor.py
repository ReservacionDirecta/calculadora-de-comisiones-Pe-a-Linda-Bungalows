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
import io # Importar el módulo io

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
        self.sirvoy_expenses = None
        self.facebook_data = None
        self.openpay_data = None # Inicializar openpay_data
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
            },
            'openpay': {
                'date_odd': 'odd',
                'card_odd': 'odd 2',
                'amount_odd': 'odd 3',
                'date_even': 'even',
                'card_even': 'even 2',
                'amount_even': 'even 3'
            }
        }
    
    def _read_csv_robust(self, file_input, sep=',', encoding='utf-8', header='infer', names=None):
        """Lee un CSV de forma robusta, aceptando UploadedFile o Path, y probando codificaciones."""
        content = None
        if hasattr(file_input, 'getvalue'):  # Es un UploadedFile de Streamlit
            content = file_input.getvalue()
        elif isinstance(file_input, (str, bytes)):  # Es una ruta de archivo
            with open(file_input, 'rb') as f:
                content = f.read()
        else:
            raise ValueError("file_input debe ser una ruta de archivo o un objeto UploadedFile.")

        # Intentar con la codificación principal, luego con alternativas
        encodings_to_try = [encoding, 'latin1', 'cp1252']
        for enc in encodings_to_try:
            try:
                logger.info(f"Intentando leer CSV con codificación: {enc}")
                # Usar BytesIO para leer el contenido binario como si fuera un archivo
                df = pd.read_csv(io.BytesIO(content), sep=sep, encoding=enc, header=header, names=names)
                logger.info(f"CSV leído exitosamente con codificación: {enc}. Filas: {df.shape[0]}, Columnas: {df.shape[1]}")
                return df
            except UnicodeDecodeError as e:
                logger.warning(f"Fallo de decodificación con {enc}: {e}, intentando el siguiente.")
                continue
            except Exception as e:
                logger.error(f"Error al leer CSV con codificación {enc}: {e}")
                raise e

        raise UnicodeDecodeError(f"No se pudo decodificar el archivo con las codificaciones intentadas: {encodings_to_try}")

    def load_izipay_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de Izipay"""
        try:
            df = self._read_csv_robust(file_input, sep=';', encoding='utf-8')
            logger.info(f"Cargados {len(df)} registros de Izipay")
            df = self._clean_izipay_data(df)
            self.izipay_data = df
            return df
        except Exception as e:
            logger.error(f"Error cargando datos de Izipay: {e}")
            self.izipay_data = pd.DataFrame()
            return pd.DataFrame()
    
    def load_culqi_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de Culqi"""
        try:
            df = self._read_csv_robust(file_input, encoding='utf-8')
            logger.info(f"Cargados {len(df)} registros de Culqi")
            df = self._clean_culqi_data(df)
            self.culqi_data = df
            return df
        except Exception as e:
            logger.error(f"Error cargando datos de Culqi: {e}")
            self.culqi_data = pd.DataFrame()
            return pd.DataFrame()
    
    def load_secured_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de transferencias directas o nuevo formato de Sirvoy"""
        try:
            # Leer el archivo CSV primero para detectar el formato
            df_raw = self._read_csv_robust(file_input, encoding='utf-8', header=0)
            
            # Limpiar nombres de columnas (remover comillas y espacios)
            df_raw.columns = df_raw.columns.str.strip().str.replace('"', '')
            
            # Verificar si es el nuevo formato de exportación de Sirvoy (Payment Id, Date, Method, Amount, etc.)
            if 'Payment Id' in df_raw.columns or 'Date' in df_raw.columns or 'Amount' in df_raw.columns:
                logger.info("Detectado nuevo formato de exportación de Sirvoy en Transferencias Directas, procesando como Sirvoy...")
                # Procesar como Sirvoy usando la misma lógica
                return self.load_sirvoy_data(file_input)
            else:
                # Formato antiguo de transferencias directas
                df = self._read_csv_robust(file_input, encoding='utf-8')
                logger.info(f"Cargados {len(df)} registros de transferencias directas")
                df = self._clean_secured_data(df)
                self.secured_data = df
                return df
        except Exception as e:
            logger.error(f"Error cargando datos de transferencias: {e}")
            self.secured_data = pd.DataFrame()
            return pd.DataFrame()
    
    def load_sirvoy_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de Sirvoy (todos los pagos)"""
        try:
            # Intentar leer primero con coma, luego con tabulación si falla
            try:
                df_raw = self._read_csv_robust(file_input, encoding='utf-8', header=0, sep=',')
            except Exception:
                # Si falla con coma, intentar con tabulación (formato de facturación)
                logger.info("Intentando leer Sirvoy con separador de tabulación...")
                df_raw = self._read_csv_robust(file_input, encoding='utf-8', header=0, sep='\t')
            
            # Limpiar nombres de columnas (remover comillas y espacios)
            df_raw.columns = df_raw.columns.str.strip().str.replace('"', '')
            
            logger.info(f"Columnas originales después de limpiar: {list(df_raw.columns)}")
            
            # Obtener nombres de columnas normalizados (sin espacios, en minúsculas) para comparación
            columnas_normalizadas = [col.strip().replace('"', '').lower() for col in df_raw.columns]
            
            logger.info(f"Columnas normalizadas: {columnas_normalizadas}")

            # Verificar si es el nuevo formato de exportación (Payment Id, Date, Method, Amount, etc.)
            # Buscar en columnas normalizadas para mayor robustez
            tiene_payment_id = any('payment' in col and 'id' in col for col in columnas_normalizadas)
            tiene_date = 'date' in columnas_normalizadas
            tiene_amount = 'amount' in columnas_normalizadas
            
            # Verificar si es el formato de facturación/cobros (tablescraper-selected-row, text-right, etc.)
            tiene_tablescraper = any('tablescraper' in col for col in columnas_normalizadas)
            tiene_text_right = 'text-right' in columnas_normalizadas or any('text-right' in col for col in columnas_normalizadas)
            tiene_flex = 'flex' in columnas_normalizadas or any('flex' in col for col in columnas_normalizadas)
            
            # Verificar si es el formato "payment-list-item" (Sirvoy antiguo/Secured)
            tiene_payment_list = any('payment-list-item' in col for col in columnas_normalizadas)
            
            logger.info(f"Detección: tiene_payment_id={tiene_payment_id}, tiene_date={tiene_date}, tiene_amount={tiene_amount}")
            logger.info(f"Detección formato facturación: tiene_tablescraper={tiene_tablescraper}, tiene_text_right={tiene_text_right}, tiene_flex={tiene_flex}")
            logger.info(f"Detección formato payment-list: tiene_payment_list={tiene_payment_list}")
            
            df = pd.DataFrame()

            # 1) NUEVO FORMATO payments_export (INGRESOS)
            if tiene_payment_id or tiene_date or tiene_amount:
                logger.info("Detectado nuevo formato de exportación de Sirvoy (payments_export), procesando...")
                
                # Crear mapeo de nombres de columnas normalizados a nombres reales
                col_map = {}
                for col in df_raw.columns:
                    col_normalized = col.strip().replace('"', '').lower()
                    col_map[col_normalized] = col
                
                # Función auxiliar para obtener valor de columna
                def get_col_value(row, col_name_normalized, default=''):
                    if col_name_normalized in col_map:
                        real_col = col_map[col_name_normalized]
                        return str(row.get(real_col, default)) if real_col in df_raw.columns else default
                    return default
                
                sirvoy_records = []
                for idx, row in df_raw.iterrows():
                    try:
                        payment_id = get_col_value(row, 'payment id') or get_col_value(row, 'paymentid')
                        fecha_str = get_col_value(row, 'date')
                        method = get_col_value(row, 'method')
                        reference = get_col_value(row, 'reference')
                        comment = get_col_value(row, 'comment')
                        linked_to = get_col_value(row, 'linked to') or get_col_value(row, 'linkedto')
                        monto_str = get_col_value(row, 'amount', '0')
                        
                        if not fecha_str or fecha_str == 'nan' or fecha_str.strip() == '': continue
                        if not monto_str or monto_str == 'nan' or monto_str.strip() == '' or monto_str == '0': continue
                        
                        booking_id = ''
                        if linked_to and 'Reserva' in linked_to:
                            match = re.search(r'Reserva\s+(\d+)', linked_to)
                            if match: booking_id = match.group(1)
                        
                        description_parts = []
                        if linked_to: description_parts.append(linked_to)
                        if comment and comment != 'nan' and comment.strip(): description_parts.append(comment)
                        if reference and reference != 'nan' and reference.strip(): description_parts.append(f"Ref: {reference}")
                        description = ' - '.join(description_parts) if description_parts else linked_to or 'Pago Sirvoy'
                        
                        record = {
                            'sirvoy_transaction_id': payment_id,
                            'fecha_sirvoy': fecha_str,
                            'payment_method_sirvoy': method,
                            'description_sirvoy': description,
                            'booking_id_sirvoy': booking_id,
                            'monto_eur_sirvoy': monto_str,
                            'reference_sirvoy': reference,
                            'comment_sirvoy': comment
                        }
                        sirvoy_records.append(record)
                    except Exception as e:
                        logger.warning(f"Error procesando fila de Sirvoy: {e}")
                        continue
                
                if sirvoy_records:
                    df = pd.DataFrame(sirvoy_records)
            
            # 2) FORMATO "PAYMENT-LIST-ITEM" (Sirvoy antiguo/Secured)
            elif tiene_payment_list:
                logger.info("Detectado formato de Sirvoy 'payment-list-item', procesando...")
                sirvoy_records = []
                for _, row in df_raw.iterrows():
                    try:
                        record = {
                            'sirvoy_transaction_id': str(row.iloc[0]),
                            'fecha_sirvoy': str(row.iloc[1]),
                            'payment_method_sirvoy': str(row.iloc[2]),
                            'description_sirvoy': str(row.iloc[3]),
                            'booking_type_sirvoy': str(row.iloc[4]),
                            'booking_id_sirvoy': str(row.iloc[5]),
                            'monto_eur_sirvoy': str(row.iloc[6])
                        }
                        sirvoy_records.append(record)
                    except Exception as e:
                        logger.warning(f"Error procesando fila de Sirvoy (payment-list-item): {e}")
                        continue
                
                if sirvoy_records:
                    df = pd.DataFrame(sirvoy_records)

            # 3) FORMATO FACTURACIÓN / COBROS (tablescraper)
            elif len(df_raw.columns) >= 5 and (tiene_tablescraper or tiene_text_right or tiene_flex):
                logger.info("Detectado formato de facturación de Sirvoy (tablescraper/cobros), procesando...")
                sirvoy_records = []
                for _, row in df_raw.iterrows():
                    try:
                        fecha_str = str(row.iloc[0]) if len(row) > 0 else ''
                        if 'tablescraper' in fecha_str.lower(): continue
                        
                        monto_str = '0'
                        if len(row) > 4:
                            monto_str = str(row.iloc[4])
                        else:
                            for idx, val in enumerate(row):
                                val_str = str(val)
                                if '€' in val_str or (',' in val_str and any(c.isdigit() for c in val_str)):
                                    monto_str = val_str
                                    break
                
                        descripcion = str(row.iloc[1]) if len(row) > 1 else ''
                        descripcion_adicional = str(row.iloc[5]) if len(row) > 5 else ''
                        descripcion_completa = descripcion
                        if descripcion_adicional and descripcion_adicional != 'nan' and descripcion_adicional.strip():
                            descripcion_completa = f"{descripcion_completa} - {descripcion_adicional}" if descripcion_completa else descripcion_adicional
                
                        url_sirvoy = str(row.iloc[2]) if len(row) > 2 else ''
                
                        record = {
                            'fecha_sirvoy': fecha_str,
                            'description_sirvoy': descripcion_completa,
                            'monto_eur_sirvoy': monto_str,
                            'url_sirvoy': url_sirvoy,
                            'tipo_sirvoy': descripcion_adicional,
                            'sirvoy_transaction_id': '',
                            'payment_method_sirvoy': '',
                            'booking_id_sirvoy': '',
                            'reference_sirvoy': '',
                            'comment_sirvoy': ''
                        }
                        sirvoy_records.append(record)
                    except Exception as e:
                        logger.warning(f"Error procesando fila de Sirvoy (formato facturación): {e}")
                        continue
                
                if sirvoy_records:
                    df = pd.DataFrame(sirvoy_records)

            # 4) FORMATO ESTÁNDAR ANTIGUO (fallback)
            else:
                logger.info("Intentando leer formato estándar de Sirvoy como último recurso...")
                expected_columns = ['sirvoy_transaction_id', 'fecha_sirvoy', 'payment_method_sirvoy', 'description_sirvoy', 'booking_id_sirvoy', 'monto_eur_sirvoy']
                # Si el número de columnas no coincide, no forzar nombres
                if len(df_raw.columns) == len(expected_columns):
                    df = df_raw.copy()
                    df.columns = expected_columns
                else:
                    logger.warning(f"Número de columnas ({len(df_raw.columns)}) no coincide con el esperado ({len(expected_columns)}).")
                    df = df_raw.copy()

            if df.empty:
                logger.warning("DataFrame de Sirvoy vacío después de la detección de formato.")
                self.sirvoy_data = pd.DataFrame()
                return pd.DataFrame()

            df = df.reset_index(drop=True)
            df_clean = self._clean_sirvoy_data(df)
            self.sirvoy_data = df_clean
            return df_clean

        except Exception as e:
            logger.error(f"Error cargando datos de Sirvoy: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.sirvoy_data = pd.DataFrame()
            return pd.DataFrame()

            self.sirvoy_data = pd.DataFrame()
            return pd.DataFrame()

    def load_openpay_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de Openpay"""
        try:
            # Leer el archivo CSV primero para detectar el formato
            df_raw = self._read_csv_robust(file_input, encoding='utf-8', header=0)
            
            # Limpiar nombres de columnas (remover caracteres especiales)
            df_raw.columns = df_raw.columns.str.strip()
            
            # Verificar si es el nuevo formato (con columnas como transaction_id, amount, fee)
            tiene_transaction_id = 'transaction_id' in df_raw.columns
            tiene_amount = 'amount' in df_raw.columns
            tiene_fee = 'fee' in df_raw.columns
            tiene_status = 'status' in df_raw.columns
            
            if tiene_transaction_id or (tiene_amount and tiene_fee):
                logger.info("Detectado nuevo formato de Openpay (con transaction_id, amount, fee), procesando...")
                df = self._clean_openpay_data_new_format(df_raw)
            else:
                # Formato antiguo con columnas odd/even
                logger.info("Detectado formato antiguo de Openpay, procesando...")
                openpay_columns = ["odd","odd 2","odd 3","even","even 2","even 3"]
                df = self._read_csv_robust(file_input, encoding='latin1', names=openpay_columns, header=0)
                df = self._clean_openpay_data(df)
            
            logger.info(f"DataFrame de Openpay (después de limpiar): Filas: {df.shape[0]}, Columnas: {df.shape[1]}")
            logger.info(f"Primeras 5 filas del DataFrame limpio de Openpay:\n{df.head()}")

            if df.empty:
                logger.warning("DataFrame de Openpay vacío después de la limpieza.")
                self.openpay_data = pd.DataFrame()
                return pd.DataFrame()

            self.openpay_data = df
            logger.info(f"Cargados {len(df)} registros de Openpay")
            return df
        except Exception as e:
            logger.error(f"Error cargando datos de Openpay: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.openpay_data = pd.DataFrame()
            return pd.DataFrame()
    
    def load_sirvoy_expenses(self, file_input) -> pd.DataFrame:
        """Carga y limpia datos de gastos de Sirvoy (software fees en EUR)"""
        df = self._read_csv_robust(file_input)
        if df is None or df.empty:
            return pd.DataFrame()
            
        logger.info(f"Cargados gastos de Sirvoy: {len(df)} registros.")
        
        # Caso 1: Formato Scraper (tablescraper-selected-row, flex, text-right)
        if 'tablescraper-selected-row' in df.columns and 'text-right' in df.columns:
            logger.info("Detectado formato 'scraper' para gastos de Sirvoy.")
            df = df.rename(columns={
                'tablescraper-selected-row': 'date',
                'flex': 'description',
                'text-right': 'amount_raw',
                'text-left': 'details'
            })
            # Si la descripción está vacía, usar el detalle
            df['description'] = df['description'].fillna(df['details'])
            df['currency'] = 'EUR'
        else:
            # Caso 2: Formato estándar (Fecha, Descripción, Monto, Divisa)
            df = df.rename(columns={
                'Fecha': 'date',
                'Descripción': 'description',
                'Monto': 'amount_raw',
                'Divisa': 'currency'
            })
        
        df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
        
        # Convertir montos a numérico y PEN (EUR to PEN ~ 4.10)
        def clean_and_convert(row):
            try:
                val_str = str(row['amount_raw']).replace('€', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
                # En el scraper, 149,00 es positivo para recargas, -149,00 para cuotas.
                # Queremos el valor absoluto del gasto real.
                amount = abs(float(val_str))
                
                # Tipo de cambio
                if 'currency' in row and row['currency'] == 'EUR':
                    return amount * 4.10
                return amount
            except:
                return 0.0
            
        df['amount'] = df.apply(clean_and_convert, axis=1)
        
        # FILTRADO CRÍTICO: Evitar duplicidad.
        # Sirvoy registra la RECARGA (ingreso de dinero al sistema) y la CUOTA (consumo del saldo).
        # Para el flujo de caja, usamos las recargas ("Recargar cuenta").
        if 'description' in df.columns:
            df = df[df['description'].str.contains('Recargar|Software', case=False, na=False)].copy()
            logger.info(f"Gastos Sirvoy filtrados (solo recargas/software): {len(df)} registros.")

        df['amount_gross'] = df['amount'] * -1 # Es un gasto para el hotel
        
        # Campos estándar
        df['source'] = 'Sirvoy Software'
        df['processor'] = 'Sirvoy'
        df['category'] = 'Software de Gestión'
        df['income_type'] = 'Gasto'
        df['status'] = 'Completado'
        
        return df

    def load_facebook_data(self, file_input) -> pd.DataFrame:
        """Carga y procesa datos de Facebook Ads desde múltiples formatos."""
        try:
            # Leer el archivo completo como texto primero para detectar el formato
            if hasattr(file_input, 'getvalue'):  # Es un UploadedFile de Streamlit
                content_bytes = file_input.getvalue()
                try:
                    content = content_bytes.decode('utf-8')
                except:
                    content = content_bytes.decode('latin1')
                file_input.seek(0)  # Resetear para lecturas posteriores
            elif isinstance(file_input, str):  # Es una ruta de archivo
                with open(file_input, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # Intentar leer como archivo abierto
                try:
                    content = file_input.read().decode('utf-8')
                except:
                    file_input.seek(0)
                    content = file_input.read().decode('latin1')
                file_input.seek(0)
            
            lines = content.split('\n')
            logger.info(f"Facebook: Archivo tiene {len(lines)} líneas")
            
            # Buscar la línea de encabezados real (que contiene "Fecha" e "Identificador")
            header_row = None
            payment_method_global = "Visa" # Valor por defecto
            
            for i, line in enumerate(lines):
                # Intentar extraer método de pago global si aparece antes de los datos
                if 'Método de pago:' in line:
                    try:
                        parts = line.split(':')
                        if len(parts) > 1:
                            payment_method_global = parts[1].strip().replace('····', '').strip()
                    except:
                        pass
                
                # Detectar línea de encabezados
                if 'Fecha' in line and 'Identificador' in line:
                    header_row = i
                    logger.info(f"Facebook: Encontrada línea de encabezados en línea {i+1}")
                    break
            
            # Detectar formato y procesar
            df = None
            if header_row is not None:
                # Formato Resumen_Facturación.csv con encabezados detectados
                logger.info("Detectado formato de Facebook 'Resumen_Facturación.csv'.")
                
                try:
                    # Leer desde la línea de encabezados
                    # Unir las líneas desde header_row en un solo string para read_csv
                    content_data = '\n'.join(lines[header_row:])
                    df = pd.read_csv(io.StringIO(content_data), encoding='utf-8')
                    logger.info(f"Facebook: DataFrame leído con {len(df)} filas y columnas: {list(df.columns)}")
                except Exception as e:
                    logger.error(f"Error leyendo CSV de Facebook: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
                
                # Filtrar filas inválidas (totales, vacías, etc.)
                # Eliminar filas donde Fecha está vacía (esto filtra totales y líneas de VAT)
                if 'Fecha' in df.columns:
                    initial_count = len(df)
                    df = df[df['Fecha'].notna()]
                    df = df[df['Fecha'] != '']  # También eliminar strings vacíos
                    # Filtrar líneas de VAT y totales
                    df = df[~df['Fecha'].astype(str).str.contains('VAT|total|Total', case=False, na=False)]
                    logger.info(f"Facebook: Filtradas {initial_count - len(df)} filas inválidas (totales/VAT)")
                
                if 'Importe' in df.columns:
                    initial_count = len(df)
                    df = df[df['Importe'].notna()]
                    # Filtrar filas donde Importe contiene "total" o está vacío
                    df = df[~df['Importe'].astype(str).str.contains('total|Total', case=False, na=False)]
                    logger.info(f"Facebook: Filtradas {initial_count - len(df)} filas con Importe inválido")
                
                if df.empty:
                    logger.warning("Facebook: DataFrame vacío después de filtrar")
                    self.facebook_data = pd.DataFrame()
                    return pd.DataFrame()
                
                df = df.rename(columns={
                    'Fecha': 'date_str',
                    'Identificador de la transacción': 'transaction_id',
                    'Método de pago': 'payment_method',
                    'Importe': 'amount_str',
                    'Divisa': 'currency'
                })
                
                # Si payment_method no existe después del rename (porque no estaba en el CSV), usar el global
                if 'payment_method' not in df.columns:
                    if 'Método de pago' in df.columns:
                         df['payment_method'] = df['Método de pago']
                    else:
                        logger.info(f"Facebook: Columna 'Método de pago' no encontrada, usando valor global: '{payment_method_global}'")
                        df['payment_method'] = payment_method_global
                
                # Limpiar método de pago (remover puntos y espacios extra)
                if 'payment_method' in df.columns:
                    df['payment_method'] = df['payment_method'].astype(str).str.replace('····', '').str.strip()
                    # Si está vacío o es NaN, usar 'Visa' por defecto
                    df['payment_method'] = df['payment_method'].fillna('Visa')
                    df.loc[df['payment_method'] == '', 'payment_method'] = 'Visa'
                
                df['status'] = 'Pagado' # Asumir que todas son pagadas en este formato
            
            # Si no se detectó el formato anterior, intentar otros formatos
            if df is None:
                # Intentar leer con _read_csv_robust para otros formatos
                df = self._read_csv_robust(file_input)
                
                if 'xt0psk2' in df.columns: # Formato business.csv
                    logger.info("Detectado formato de Facebook 'business.csv'.")
                    df = df.rename(columns={
                        'xt0psk2': 'transaction_id',
                        'x8t9es0': 'date_str',
                        'x8t9es0 2': 'amount_str',
                        'x8t9es0 3': 'payment_method',
                        'x8t9es0 5': 'status'
                    })
                    # Filtrar solo transacciones pagadas
                    df = df[df['status'] == 'Pagado']
                
                elif df.shape[1] == 1: # Nuevo formato con una sola columna de montos
                    logger.info("Detectado formato de Facebook con una sola columna de montos.")
                    df.columns = ['amount_str']
                    # Generar datos faltantes
                    df['date_str'] = pd.to_datetime('today').strftime('%d/%m/%Y')
                    df['transaction_id'] = [f"FB_GASTO_{i+1}" for i in range(len(df))]
                    df['payment_method'] = 'Tarjeta'
                    df['status'] = 'Pagado'
                
                else:
                    raise ValueError(f"Formato de archivo de Facebook no reconocido. Columnas encontradas: {list(df.columns)}")
            
            if df is None or df.empty:
                logger.error("Facebook: No se pudo procesar el archivo o está vacío")
                self.facebook_data = pd.DataFrame()
                return pd.DataFrame()

            # Limpieza y conversión
            if 'amount' not in df.columns:
                # Procesar formato europeo: "255,33" o "5.793,12" -> 255.33 o 5793.12
                # Formato: punto para miles, coma para decimales
                amount_series = df['amount_str'].astype(str)
                # Remover comillas y espacios
                amount_series = amount_series.str.replace('"', '').str.replace('S/', '').str.replace(' ', '').str.strip()
                # Detectar si tiene punto (miles) y coma (decimales)
                # Si tiene punto Y coma: formato europeo completo (ej: "5.793,12")
                # Si solo tiene coma: formato europeo simple (ej: "255,33")
                # Si solo tiene punto: formato americano (ej: "255.33")
                def convert_european_amount(amount_str):
                    if pd.isna(amount_str) or amount_str == '' or 'nan' in str(amount_str).lower():
                        return None
                    amount_str = str(amount_str).strip()
                    # Remover comillas y espacios
                    amount_str = amount_str.replace('"', '').replace('S/', '').replace(' ', '')
                    # Si tiene punto Y coma, es formato europeo completo
                    if '.' in amount_str and ',' in amount_str:
                        # "5.793,12" -> "5793.12"
                        amount_str = amount_str.replace('.', '').replace(',', '.')
                    elif ',' in amount_str and '.' not in amount_str:
                        # "255,33" -> "255.33"
                        amount_str = amount_str.replace(',', '.')
                    # Si solo tiene punto, asumir formato americano (ya está bien)
                    try:
                        return float(amount_str)
                    except:
                        return None
                
                df['amount'] = amount_series.apply(convert_european_amount)
            
            if 'date' not in df.columns:
                df['date'] = pd.to_datetime(df['date_str'], errors='coerce', dayfirst=True)
            
            # Filtrar registros no válidos
            df = df.dropna(subset=['date', 'amount'])
            df = df[df['amount'] != 0]

            # Asignar valores negativos
            df['amount'] = df['amount'].abs() * -1

            # Agregar columnas estándar
            df['source'] = 'Facebook Ads'
            df['processor'] = 'Facebook'
            df['category'] = 'Gasto Publicitario'
            df['income_type'] = 'Gasto'

            self.facebook_data = df
            logger.info(f"Cargados {len(df)} registros de Facebook Ads.")
            return df

        except Exception as e:
            logger.error(f"Error cargando datos de Facebook: {e}")
            self.facebook_data = pd.DataFrame()
            return pd.DataFrame()
    
    def _clean_izipay_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Izipay"""
        df = df.copy()
        # Convertir fechas
        if 'Fecha del pago' in df.columns:
            df['Fecha del pago'] = pd.to_datetime(df['Fecha del pago'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        if 'Fecha de captura' in df.columns:
            df['Fecha de captura'] = pd.to_datetime(df['Fecha de captura'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        
        # Convertir importes a numérico
        # Soporta tanto 'Importe del pago' (Izipay Soles) como 'Monto del pago' (Izipay USD)
        amount_col = None
        for col_name in ['Importe del pago', 'Monto del pago']:
            if col_name in df.columns:
                amount_col = col_name
                break
        
        if amount_col:
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
            # Estandarizar a 'Importe del pago' para el resto del pipeline
            if amount_col != 'Importe del pago':
                df['Importe del pago'] = df[amount_col]
        else:
            df['Importe del pago'] = 0.0
        
        if 'Comisión' in df.columns:
            df['Comisión'] = pd.to_numeric(df['Comisión'], errors='coerce')
        else:
            df['Comisión'] = 0.0
        
        # Agregar columna de fuente
        df['source'] = 'Izipay'
        
        # Limpiar estados
        if 'Estado' in df.columns:
            df['Estado'] = df['Estado'].str.strip()
        
        return df
    
    def _clean_culqi_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Culqi"""
        df = df.copy()
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
        
        # Filtrar transacciones exitosas
        if 'Estado' in df.columns:
            original_count = len(df)
            # Normalizar estado
            estados = df['Estado'].astype(str).str.strip().str.lower()
            # Definir estados de rechazo explícitos
            estados_rechazo = ['rechazada', 'denegada', 'fallida', 'expirada', 'anulada']
            # Filtrar: Mantener solo si NO está en la lista de rechazos
            df = df[~estados.isin(estados_rechazo)]
            
            filtered_count = original_count - len(df)
            if filtered_count > 0:
                logger.info(f"Culqi: Filtradas {filtered_count} transacciones rechazadas/anuladas. Registros restantes: {len(df)}")

        return df
    
    def _clean_secured_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de pagos recibidos (solo no-tarjeta)"""
        df = df.copy()
        # Renombrar columnas para mayor claridad
        df.columns = ['transaction_id', 'date', 'payment_type', 'description', 'booking_type', 'booking_id', 'amount']

        # Convertir fechas
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y %H:%M', errors='coerce')

        # Función para convertir formato europeo a float
        def convertir_monto_europeo(monto_str):
            if pd.isna(monto_str) or monto_str == '':
                return 0.0
            # Remover puntos de miles y convertir coma decimal a punto
            monto_str = str(monto_str).strip()
            monto_str = monto_str.replace('.', '').replace(',', '.')
            try:
                return float(monto_str)
            except:
                return 0.0

        # Limpiar y convertir importes (formato europeo con coma decimal)
        df['amount'] = df['amount'].apply(convertir_monto_europeo)

        # FILTRAR: Solo pagos que NO sean "Pago con tarjeta"
        # Estos ya están procesados por Izipay/Culqi
        df = df[df['payment_type'] != 'Pago con tarjeta']

        # Agregar columna de fuente
        df['source'] = 'Pago Directo'

        logger.info(f"Filtrados pagos directos: {len(df)} registros (excluidos pagos con tarjeta)")

        return df

    def _clean_openpay_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Openpay"""
        records = []
        for _, row in df.iterrows():
            # Procesar columnas 'odd'
            if pd.notna(row['odd']) and pd.notna(row['odd 2']) and pd.notna(row['odd 3']):
                records.append({
                    'date_str': row['odd'],
                    'card_number': row['odd 2'],
                    'amount_str': row['odd 3']
                })
            # Procesar columnas 'even'
            if pd.notna(row['even']) and pd.notna(row['even 2']) and pd.notna(row['even 3']):
                records.append({
                    'date_str': row['even'],
                    'card_number': row['even 2'],
                    'amount_str': row['even 3']
                })
        
        if not records:
            return pd.DataFrame()

        df_clean = pd.DataFrame(records)

        # Convertir fechas
        def parse_openpay_date(date_str):
            try:
                # "23 Sep. 25, 20:02:33" -> "23 Sep 2025 20:02:33"
                date_str = date_str.replace('.', '').replace(',', '')
                # Asumiendo que '25' es 2025, '24' es 2024, etc.
                year_prefix = '20' if int(date_str.split(' ')[2]) < 50 else '19'
                return pd.to_datetime(date_str.replace(date_str.split(' ')[2], year_prefix + date_str.split(' ')[2]), format='%d %b %Y %H:%M:%S', errors='coerce')
            except Exception as e:
                logger.warning(f"Error parseando fecha de Openpay '{date_str}': {e}")
                return pd.NaT

        df_clean.loc[:, 'date'] = df_clean['date_str'].apply(parse_openpay_date) # Usar .loc
        # Convertir montos
        def clean_openpay_amount(amount_str):
            if pd.isna(amount_str) or str(amount_str).strip() == '':
                return 0.0
            amount_str = str(amount_str).replace('S/', '').replace(' ', '').replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                return 0.0
        
        df_clean.loc[:, 'amount'] = df_clean['amount_str'].apply(clean_openpay_amount) # Usar .loc

        # Filtrar registros válidos
        df_clean = df_clean.dropna(subset=['date', 'amount'])
        df_clean = df_clean[df_clean['amount'] != 0.0]

        # Agregar columnas estándar
        df_clean.loc[:, 'transaction_id'] = df_clean.apply(lambda r: f"OPENPAY_{r['date'].strftime('%Y%m%d%H%M%S') if pd.notna(r['date']) else 'NO_DATE'}_{str(r['card_number'])[-4:]}", axis=1) # Usar .loc
        df_clean.loc[:, 'currency'] = 'PEN' # Usar .loc
        df_clean.loc[:, 'status'] = 'Completado' # Usar .loc
        df_clean.loc[:, 'payment_method'] = 'Tarjeta' # Usar .loc
        df_clean.loc[:, 'customer_name'] = '' # Usar .loc
        df_clean.loc[:, 'customer_email'] = '' # Usar .loc
        df_clean.loc[:, 'commission_processor'] = 0 # Se calculará en unify_data si es necesario # Usar .loc
        df_clean.loc[:, 'commission_chamba'] = 0 # Usar .loc
        df_clean.loc[:, 'commission_total'] = 0 # Usar .loc
        df_clean.loc[:, 'card_last4'] = df_clean['card_number'].apply(lambda x: str(x)[-4:]) # Usar .loc
        df_clean.loc[:, 'authorization_code'] = '' # Usar .loc
        df_clean.loc[:, 'country'] = 'PE' # Usar .loc
        df_clean.loc[:, 'source'] = 'Openpay' # Usar .loc
        df_clean.loc[:, 'processor'] = 'Openpay' # Usar .loc
        df_clean.loc[:, 'category'] = 'Pago con Tarjeta' # Usar .loc
        df_clean.loc[:, 'income_type'] = 'Tarjeta' # Nuevo campo para desglose de ingresos # Usar .loc

        return df_clean
    
    def _clean_openpay_data_new_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Openpay en el nuevo formato (con transaction_id, amount, fee, etc.)"""
        
        # Filtrar solo transacciones completadas
        if 'status' in df.columns:
            df = df[df['status'].astype(str).str.lower() == 'completed'].copy()
        
        # Filtrar solo pagos con tarjeta
        if 'method' in df.columns:
            df = df[df['method'].astype(str).str.lower() == 'card'].copy()
        
        # Filtrar transacciones no reembolsadas
        if 'refunded' in df.columns:
            # Convertir a string y verificar que no sea 'true' (case insensitive)
            df = df[df['refunded'].astype(str).str.lower() != 'true'].copy()
        
        if df.empty:
            logger.warning("No hay transacciones válidas de Openpay después del filtrado")
            return pd.DataFrame()
        
        logger.info(f"Transacciones de Openpay después de filtros: {len(df)}")
        
        # Convertir fechas
        if 'creation_date' in df.columns:
            df['date'] = pd.to_datetime(df['creation_date'], errors='coerce', format='%Y-%m-%d %H:%M:%S')
        else:
            df['date'] = pd.NaT
        
        # Convertir montos (formato europeo: "173,92")
        def convertir_monto_openpay(monto_str):
            if pd.isna(monto_str) or str(monto_str).strip() == '':
                return 0.0
            monto_str = str(monto_str).strip().replace('"', '')
            # Formato europeo: 173,92 -> 173.92
            monto_str_cleaned = monto_str.replace('.', '').replace(',', '.')
            try:
                return float(monto_str_cleaned)
            except ValueError:
                return 0.0
        
        if 'amount' in df.columns:
            # Convertir a float64 explícitamente para evitar error de dtype string
            df = df.copy()
            df['amount'] = df['amount'].apply(convertir_monto_openpay).astype(float)
        else:
            df['amount'] = 0.0
        
        # Convertir comisiones (fee y fee_tax)
        def convertir_comision(comision_str):
            if pd.isna(comision_str) or str(comision_str).strip() == '':
                return 0.0
            comision_str = str(comision_str).strip().replace('"', '')
            comision_str_cleaned = comision_str.replace('.', '').replace(',', '.')
            try:
                return float(comision_str_cleaned)
            except ValueError:
                return 0.0
        
        if 'fee' in df.columns:
            df['fee'] = df['fee'].apply(convertir_comision).astype(float)
        else:
            df['fee'] = 0.0
        
        if 'fee_tax' in df.columns:
            df['fee_tax'] = df['fee_tax'].apply(convertir_comision).astype(float)
        else:
            df['fee_tax'] = 0.0
        
        # Calcular comisión total del procesador
        df.loc[:, 'commission_processor'] = df['fee'] + df['fee_tax']
        
        # Extraer últimos 4 dígitos de tarjeta
        if 'card_number' in df.columns:
            df.loc[:, 'card_last4'] = df['card_number'].astype(str).str.replace('*', '').str.strip()
            # Si tiene formato como "421410******8904", extraer los últimos 4
            df.loc[:, 'card_last4'] = df['card_last4'].str.extract(r'(\d{4})$')[0].fillna('')
        else:
            df.loc[:, 'card_last4'] = ''
        
        # Extraer código de autorización
        if 'authorization' in df.columns:
            df.loc[:, 'authorization_code'] = df['authorization'].astype(str).fillna('')
        else:
            df.loc[:, 'authorization_code'] = ''
        
        # Obtener transaction_id
        if 'transaction_id' in df.columns:
            df.loc[:, 'transaction_id'] = df['transaction_id'].astype(str)
        else:
            df.loc[:, 'transaction_id'] = df.apply(
                lambda r: f"OPENPAY_{r['date'].strftime('%Y%m%d%H%M%S') if pd.notna(r['date']) else 'NO_DATE'}_{r['card_last4']}", 
                axis=1
            )
        
        # Filtrar registros válidos
        df = df.dropna(subset=['date', 'amount'])
        df = df[df['amount'] > 0]  # Solo montos positivos
        
        # Log para verificar el total
        if not df.empty:
            total_amount = df['amount'].sum()
            logger.info(f"Openpay: {len(df)} transacciones válidas, Total amount (bruto): S/ {total_amount:,.2f}")
        
        # Agregar columnas estándar
        if 'currency' in df.columns:
            df['currency'] = df['currency'].astype(str).str.lower().replace('pen', 'PEN').replace('usd', 'USD')
        else:
            df['currency'] = 'PEN'
        
        df['status'] = 'Completado'
        df['payment_method'] = 'Tarjeta'
        df['customer_name'] = ''
        df['customer_email'] = ''
        df['commission_chamba'] = 0  # Se calculará en unify_data
        df['commission_total'] = df['commission_processor']
        df['country'] = 'PE'
        df['source'] = 'Openpay'
        df['processor'] = 'Openpay'
        df['category'] = 'Pago con Tarjeta'
        df['income_type'] = 'Tarjeta'
        
        return df
    
    def _clean_facebook_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de Facebook Ads, manejando múltiples formatos."""
        
        # Detectar formato basado en las columnas
        if 'xt0psk2' in df.columns: # Formato business.csv
            logger.info("Limpiando formato de Facebook 'business.csv'.")
            df = df.rename(columns={
                'xt0psk2': 'transaction_id',
                'x8t9es0': 'date_str',
                'x8t9es0 2': 'amount_str',
                'x8t9es0 3': 'payment_method',
                'x8t9es0 5': 'status'
            })
            df = df[df['status'] == 'Pagado']
            df['date'] = pd.to_datetime(df['date_str'], errors='coerce', dayfirst=True)
            df['amount'] = df['amount_str'].astype(str).str.replace('S/', '').str.replace(',', '.').str.strip()
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        elif 'Fecha' in df.columns and 'Identificador de la transacción' in df.columns: # Formato Resumen_Facturación.csv
            logger.info("Limpiando formato de Facebook 'Resumen_Facturación.csv'.")
            df = df.rename(columns={
                'Fecha': 'date',
                'Identificador de la transacción': 'transaction_id',
                'Importe': 'amount',
                'Divisa': 'currency'
            })
            df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce', dayfirst=True)
            df['amount'] = df['amount'].astype(str).str.replace('"', '').str.replace(' ', '').str.replace('.', '').str.replace(',', '.')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        else:
            logger.error("Formato de archivo de Facebook no reconocido durante la limpieza.")
            return pd.DataFrame()

        # Filtrar registros válidos
        df = df.dropna(subset=['date', 'amount'])
        df = df[df['amount'] != 0.0]

        # Agregar columnas estándar
        df['source'] = 'Facebook Ads'
        df['processor'] = 'Facebook'
        df['category'] = 'Gasto Publicitario'
        df['income_type'] = 'Gasto'
        df['amount'] = df['amount'].abs() * -1

        return df

    def _clean_sirvoy_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza datos de cobros de la plataforma Sirvoy"""
        
        logger.info(f"_clean_sirvoy_data: Recibido DataFrame con {len(df)} filas y columnas: {list(df.columns)}")

        # Convertir fechas - manejar diferentes formatos
        if 'fecha_sirvoy' in df.columns:
            # Intentar primero formato con hora: "DD/MM/YYYY HH:MM"
            df.loc[:, 'fecha'] = pd.to_datetime(df['fecha_sirvoy'], format='%d/%m/%Y %H:%M', errors='coerce', dayfirst=True)
            
            # Si hay errores, intentar formato sin hora: "DD/MM/YYYY"
            if df['fecha'].isnull().any():
                mask_null = df['fecha'].isnull()
                df.loc[mask_null, 'fecha'] = pd.to_datetime(df.loc[mask_null, 'fecha_sirvoy'], format='%d/%m/%Y', errors='coerce', dayfirst=True)
            
            # Si aún hay errores, intentar formato flexible
            if df['fecha'].isnull().any():
                mask_null = df['fecha'].isnull()
                df.loc[mask_null, 'fecha'] = pd.to_datetime(df.loc[mask_null, 'fecha_sirvoy'], errors='coerce', dayfirst=True)
        else:
            df.loc[:, 'fecha'] = pd.NaT # Asignar NaT si la columna no existe

        # Procesar montos - manejar diferentes formatos
        monto_col = None
        if 'monto_eur_sirvoy' in df.columns:
            monto_col = 'monto_eur_sirvoy'
        elif 'monto_eur' in df.columns:
            monto_col = 'monto_eur'
        
        # Si no hay columna de monto, buscar en otras columnas
        if monto_col is None:
            for col in df.columns:
                if 'monto' in col.lower() or 'amount' in col.lower():
                    monto_col = col
                    break

        if monto_col:
            # Función para convertir formato europeo a float
            def convertir_monto_europeo(monto_str):
                if pd.isna(monto_str) or str(monto_str).strip() == '':
                    logger.debug(f"convertir_monto_europeo: Valor vacío o NaN: {monto_str}")
                    return 0.0
                
                monto_original = str(monto_str).strip()
                # Remover puntos de miles y convertir coma decimal a punto
                monto_str = monto_original.replace('€', '').replace('"', '').strip()
                
                # Manejar números negativos
                sign = -1 if monto_str.startswith('-') else 1
                monto_str = monto_str.replace('-', '')
                
                # Limpiar y convertir (formato europeo: 1.546,00 -> 1546.00)
                # Si tiene punto y coma, es formato europeo (1.546,00)
                # Si solo tiene coma, es formato europeo simple (546,00)
                # Si tiene punto pero no coma, podría ser formato inglés (1546.00)
                if ',' in monto_str and '.' in monto_str:
                    # Formato europeo con miles: 1.546,00
                    monto_str_cleaned = monto_str.replace('.', '').replace(',', '.')
                elif ',' in monto_str:
                    # Formato europeo simple: 546,00
                    monto_str_cleaned = monto_str.replace(',', '.')
                else:
                    # Formato inglés o sin separadores: 1546.00 o 1546
                    monto_str_cleaned = monto_str
                
                try:
                    resultado = float(monto_str_cleaned) * sign
                    logger.debug(f"convertir_monto_europeo: '{monto_original}' -> {resultado}")
                    return resultado
                except ValueError as e:
                    logger.warning(f"convertir_monto_europeo: Error convirtiendo '{monto_original}': {e}")
                    return 0.0

            df.loc[:, 'monto_eur'] = df[monto_col].apply(convertir_monto_europeo)
            logger.info(f"_clean_sirvoy_data: Montos convertidos. Valores únicos (primeros 10): {df['monto_eur'].unique()[:10]}")
        else:
            df.loc[:, 'monto_eur'] = 0.0 # Asignar 0.0 si la columna no existe o está vacía

        # Filtrar registros válidos (se necesita la columna 'fecha' y 'monto_eur')
        # Solo filtrar si las columnas existen
        logger.info(f"_clean_sirvoy_data: Antes de filtrar - {len(df)} registros")
        if 'fecha' in df.columns and 'monto_eur' in df.columns:
            logger.info(f"_clean_sirvoy_data: Valores de monto_eur antes de filtrar: {df['monto_eur'].head(10).tolist()}")
            df = df.dropna(subset=['fecha', 'monto_eur'])
            logger.info(f"_clean_sirvoy_data: Después de dropna - {len(df)} registros")
            df = df[df['monto_eur'] != 0.0] # Filtrar montos que son 0.0 después de la conversión
            logger.info(f"_clean_sirvoy_data: Después de filtrar monto_eur != 0.0 - {len(df)} registros")
        else:
            logger.warning(f"Columnas faltantes en Sirvoy: fecha={'fecha' in df.columns}, monto_eur={'monto_eur' in df.columns}")
            logger.warning(f"Columnas disponibles: {list(df.columns)}")

        if df.empty:
            logger.warning("_clean_sirvoy_data: DataFrame vacío después de filtrar")
            return df

        # Marcar fuente
        df.loc[:, 'source'] = 'Sirvoy'
        
        # Detectar si es formato de facturación/cobros (tiene url_sirvoy o tipo_sirvoy)
        # Estos son GASTOS del servicio, no ingresos
        if 'url_sirvoy' in df.columns or 'tipo_sirvoy' in df.columns:
            df.loc[:, 'es_facturacion'] = True
            logger.info("Sirvoy: Detectado formato de facturación/cobros - se tratará como GASTOS")
        else:
            df.loc[:, 'es_facturacion'] = False

            # NO FILTRAR PAGOS: Mantener todos los registros (incluyendo Tarjetas) para conciliación.
            if 'payment_method_sirvoy' in df.columns:
                # Mostrar distribución de métodos para información
                methods_stat = df['payment_method_sirvoy'].fillna('').astype(str).str.strip().value_counts()
                logger.info(f"Sirvoy: Distribución de métodos de pago cargados:")
                for method, count in methods_stat.items():
                    logger.info(f"  - '{method}': {count} registros")
                
                # Normalizar método de pago para uso posterior
                df.loc[:, 'payment_method_sirvoy_clean'] = df['payment_method_sirvoy'].fillna('').astype(str).str.strip().str.lower()
        
        return df
    
    def unify_data(self) -> pd.DataFrame:
        """Unifica datos de todas las fuentes con conciliación estricta Sirvoy-Pasarelas"""
        unified_records = []
        
        # 1. Preparar "Maestro de Pagos" de Sirvoy
        sirvoy_card_master = pd.DataFrame()
        sirvoy_direct_master = pd.DataFrame()
        
        if self.sirvoy_data is not None and not self.sirvoy_data.empty:
            # Filtrar solo ingresos (no facturación/gastos)
            sirvoy_income = self.sirvoy_data[self.sirvoy_data['es_facturacion'] == False].copy()
            
            # Clasificar Sirvoy: Tarjetas vs Directos (Transferencia/Efectivo)
            if 'payment_method_sirvoy_clean' in sirvoy_income.columns:
                sirvoy_card_master = sirvoy_income[
                    sirvoy_income['payment_method_sirvoy_clean'].str.contains('tarjeta|card|openpay|izipay|culqi', na=False)
                ].copy()
                sirvoy_direct_master = sirvoy_income[
                    sirvoy_income['payment_method_sirvoy_clean'].str.contains('transferencia|efectivo|cash|bank', na=False)
                ].copy()
                logger.info(f"Conciliación: {len(sirvoy_card_master)} registros de tarjeta y {len(sirvoy_direct_master)} directos en Sirvoy.")

        # Lógica de emparejamiento para Tarjetas
        def get_sirvoy_match(amount, ref_id=""):
            if sirvoy_card_master.empty:
                return None
            
            # Match por monto (tolerancia 1.00 por redondeos/TC)
            mask = (sirvoy_card_master['monto_eur'] >= (amount - 1.0)) & (sirvoy_card_master['monto_eur'] <= (amount + 1.0))
            matches = sirvoy_card_master[mask]
            
            if not matches.empty:
                return matches.index[0]
            
            return None

        # 2. Procesar Pasarelas (Izipay, Culqi, Openpay)
        # ---------------------------------------------
        # Izipay
        if self.izipay_data is not None and not self.izipay_data.empty:
            for _, row in self.izipay_data.iterrows():
                amount_raw = row.get('Importe del pago', 0)
                currency = row.get('Moneda', 'PEN')
                tc = 3.60 if currency == 'USD' else 1.0
                amount_gross = amount_raw * tc
                comm_proc = (row.get('Comisión', 0) or 0) * tc
                trans_id = row.get('Transacción UUID', '')
                
                sirvoy_idx = get_sirvoy_match(amount_gross, trans_id)
                is_verified = sirvoy_idx is not None
                if is_verified: sirvoy_card_master.drop(sirvoy_idx, inplace=True)
                
                comm_chamba = amount_gross * 0.05 if is_verified else 0.0
                unified_records.append({
                    'transaction_id': trans_id,
                    'date': row.get('Fecha del pago'),
                    'amount_gross': amount_gross,
                    'amount_net': amount_gross - comm_proc - comm_chamba,
                    'currency': currency,
                    'status': row.get('Estado', 'Completado'),
                    'processor': 'Izipay',
                    'source': 'Izipay',
                    'category': 'Pago con Tarjeta',
                    'income_type': 'Tarjeta',
                    'is_verified': is_verified,
                    'commission_processor': comm_proc,
                    'commission_chamba': comm_chamba,
                    'customer_name': row.get('Comprador', ''),
                    'payment_method': row.get('Medio de pago', 'Tarjeta')
                })

        # Culqi
        if self.culqi_data is not None and not self.culqi_data.empty:
            for _, row in self.culqi_data.iterrows():
                amount_gross = row.get('Monto VENTA', 0)
                comm_proc = row.get('Comision TOTAL', 0)
                trans_id = row.get('ID Venta', '')
                
                sirvoy_idx = get_sirvoy_match(amount_gross, trans_id)
                is_verified = sirvoy_idx is not None
                if is_verified: sirvoy_card_master.drop(sirvoy_idx, inplace=True)
                
                comm_chamba = amount_gross * 0.05 if is_verified else 0.0
                unified_records.append({
                    'transaction_id': trans_id,
                    'date': pd.to_datetime(row.get('Fecha de la transaccion')),
                    'amount_gross': amount_gross,
                    'amount_net': amount_gross - comm_proc - comm_chamba,
                    'currency': 'PEN',
                    'status': 'Completado',
                    'processor': 'Culqi',
                    'source': 'Culqi',
                    'category': 'Pago con Tarjeta',
                    'income_type': 'Tarjeta',
                    'is_verified': is_verified,
                    'commission_processor': comm_proc,
                    'commission_chamba': comm_chamba,
                    'customer_name': f"{row.get('Nombres', '')} {row.get('Apellidos', '')}",
                    'payment_method': row.get('Marca', 'Tarjeta')
                })

        # Openpay
        if self.openpay_data is not None and not self.openpay_data.empty:
            for _, row in self.openpay_data.iterrows():
                # CORRECCIÓN: Openpay cleaner usa 'amount', no 'amount_gross'
                amount_gross = row.get('amount', 0)
                comm_proc = row.get('commission_processor', 0)
                trans_id = row.get('transaction_id', '')
                
                sirvoy_idx = get_sirvoy_match(amount_gross, trans_id)
                is_verified = sirvoy_idx is not None
                if is_verified: sirvoy_card_master.drop(sirvoy_idx, inplace=True)
                
                comm_chamba = amount_gross * 0.05 if is_verified else 0.0
                unified_records.append({
                    'transaction_id': trans_id,
                    'date': row.get('date'),
                    'amount_gross': amount_gross,
                    'amount_net': amount_gross - comm_proc - comm_chamba,
                    'currency': 'PEN',
                    'status': 'Completado',
                    'processor': 'Openpay',
                    'source': 'Openpay',
                    'category': 'Pago con Tarjeta',
                    'income_type': 'Tarjeta',
                    'is_verified': is_verified,
                    'commission_processor': comm_proc,
                    'commission_chamba': comm_chamba,
                    'customer_name': row.get('customer_name', ''),
                    'payment_method': row.get('payment_method', 'Tarjeta')
                })

        # 3. Procesar Ingresos Directos (Transferencias/Efectivo de Sirvoy)
        # --------------------------------------------------------------
        if not sirvoy_direct_master.empty:
            sirvoy_ingresos = sirvoy_direct_master[sirvoy_direct_master['monto_eur'] > 0].copy()
            sirvoy_negativos = sirvoy_direct_master[sirvoy_direct_master['monto_eur'] < 0].copy()
            
            correcciones = {}
            for _, r in sirvoy_negativos.iterrows():
                key = str(r.get('booking_id_sirvoy', '')) or str(r.get('reference_sirvoy', '')) or "S_REF"
                if key not in correcciones: correcciones[key] = []
                correcciones[key].append(r)
            
            for _, row in sirvoy_ingresos.iterrows():
                amount = row['monto_eur']
                key = str(row.get('booking_id_sirvoy', '')) or str(row.get('reference_sirvoy', '')) or "S_REF"
                
                found_corr = False
                if key in correcciones:
                    for i, corr in enumerate(correcciones[key]):
                        if abs(abs(corr['monto_eur']) - amount) < 1.0:
                            correcciones[key].pop(i)
                            found_corr = True
                            break
                
                if found_corr: continue
                
                method = row['payment_method_sirvoy_clean']
                income_type_val = 'Efectivo' if 'efectivo' in method else 'Transferencia'
                
                unified_records.append({
                    'transaction_id': str(row.get('sirvoy_transaction_id', '')),
                    'date': row.get('fecha'),
                    'amount_gross': amount,
                    'amount_net': amount * 0.95,
                    'currency': 'PEN',
                    'status': 'Completado',
                    'processor': income_type_val,
                    'source': 'Sirvoy',
                    'category': 'Pago Directo',
                    'income_type': income_type_val,
                    'is_verified': True,
                    'commission_processor': 0,
                    'commission_chamba': amount * 0.05,
                    'customer_name': str(row.get('description_sirvoy', '')),
                    'payment_method': row.get('payment_method_sirvoy', income_type_val)
                })

        # 4. Procesar Gastos (Facebook y Sirvoy Software)
        # -----------------------------------------------
        if self.facebook_data is not None and not self.facebook_data.empty:
            for _, row in self.facebook_data.iterrows():
                amount_reported = row.get('amount', 0)
                amount_real = abs(amount_reported) * 1.1197
                unified_records.append({
                    'transaction_id': row.get('transaction_id', ''),
                    'date': row.get('date'),
                    'amount_gross': -amount_real,
                    'amount_net': -amount_real,
                    'currency': 'PEN',
                    'status': 'Completado',
                    'processor': 'Facebook',
                    'source': 'Facebook Ads',
                    'category': 'Gasto Publicitario',
                    'income_type': 'Gasto',
                    'is_verified': True,
                    'commission_processor': 0,
                    'commission_chamba': 0,
                    'customer_name': 'Facebook Ads',
                    'payment_method': 'Ads'
                })

        if hasattr(self, 'sirvoy_expenses') and self.sirvoy_expenses is not None and not self.sirvoy_expenses.empty:
            for _, row in self.sirvoy_expenses.iterrows():
                unified_records.append({
                    'transaction_id': f"FEE_{row['date'].strftime('%Y%m%d')}",
                    'date': row['date'],
                    'amount_gross': row['amount_gross'],
                    'amount_net': row['amount_gross'],
                    'currency': row['currency'],
                    'status': 'Completado',
                    'processor': 'Sirvoy',
                    'source': 'Sirvoy Software',
                    'category': 'Gasto Operativo',
                    'income_type': 'Gasto',
                    'is_verified': True,
                    'commission_processor': 0,
                    'commission_chamba': 0,
                    'customer_name': 'Sirvoy Software',
                    'payment_method': 'Suscripción'
                })

        if not unified_records: return pd.DataFrame()
        df_unified = pd.DataFrame(unified_records)
        df_unified['date'] = pd.to_datetime(df_unified['date'], errors='coerce')
        df_unified = df_unified.dropna(subset=['date']).sort_values('date')
        
        # Campos de compatibilidad
        df_unified['amount'] = df_unified['amount_gross']
        df_unified['commission'] = df_unified['commission_processor']
        df_unified['commission_total'] = df_unified['commission_processor'] + df_unified['commission_chamba']
        # Asegurar amount_reported para stats
        if 'amount_reported' not in df_unified.columns:
             df_unified['amount_reported'] = df_unified['amount_gross']
        if 'tax_adjustment' not in df_unified.columns:
             df_unified['tax_adjustment'] = 0

        self.unified_data = df_unified
        return self.unified_data

    def get_income_breakdown(self) -> Dict:
        """Genera un desglose detallado de ingresos por tipo de pago"""
        if self.unified_data is None or self.unified_data.empty:
            return {
                'total_ingresos': 0,
                'desglose_por_tipo': {},
                'desglose_por_metodo': {},
                'detalle_transacciones': {},
                'resumen_ejecutivo': {}
            }

        # Filtrar solo ingresos (montos positivos)
        income_data = self.unified_data[self.unified_data['amount_gross'] > 0].copy()

        if income_data.empty:
            return {
                'total_ingresos': 0,
                'desglose_por_tipo': {},
                'desglose_por_metodo': {},
                'detalle_transacciones': {},
                'resumen_ejecutivo': {}
            }

        # 1. Desglose por tipo de ingreso (Tarjeta, Transferencia, Efectivo, Otros)
        desglose_tipo = {}
        tipos_principales = ['Tarjeta', 'Transferencia', 'Efectivo', 'Otros']

        # Debug: verificar qué tipos de ingresos tenemos
        tipos_unicos = income_data['income_type'].unique()
        logger.info(f"Tipos de ingresos encontrados: {tipos_unicos}")

        for tipo in tipos_principales:
            tipo_data = income_data[income_data['income_type'] == tipo]
            if not tipo_data.empty:
                monto_bruto = tipo_data['amount_gross'].sum()
                cantidad_transacciones = len(tipo_data)
                promedio_transaccion = monto_bruto / cantidad_transacciones if cantidad_transacciones > 0 else 0
                comisiones_totales = tipo_data['commission_total'].sum()
                porcentaje_ingreso = (monto_bruto / income_data['amount_gross'].sum()) * 100 if income_data['amount_gross'].sum() > 0 else 0

                logger.info(f"Tipo {tipo}: {cantidad_transacciones} transacciones, monto: {monto_bruto}")

                desglose_tipo[tipo] = {
                    'monto_total': round(monto_bruto, 2),
                    'cantidad_transacciones': cantidad_transacciones,
                    'promedio_transaccion': round(promedio_transaccion, 2),
                    'comisiones': round(comisiones_totales, 2),
                    'porcentaje_del_total': round(porcentaje_ingreso, 1)
                }

        # 2. Desglose por método de pago específico
        metodos_pago = income_data['payment_method'].value_counts()
        desglose_metodo = {}
        for metodo, count in metodos_pago.items():
            metodo_data = income_data[income_data['payment_method'] == metodo]
            desglose_metodo[metodo] = {
                'cantidad_transacciones': count,
                'monto_total': round(metodo_data['amount_gross'].sum(), 2),
                'comisiones': round(metodo_data['commission_total'].sum(), 2)
            }

        # 3. Detalle de transacciones principales por tipo
        detalle_transacciones = {}
        for tipo in tipos_principales:
            tipo_data = income_data[income_data['income_type'] == tipo]
            if not tipo_data.empty:
                # Ordenar por monto descendente y tomar top 5
                top_transacciones = tipo_data.nlargest(5, 'amount_gross')[
                    ['date', 'amount_gross', 'customer_name', 'transaction_id']
                ].to_dict('records')

                detalle_transacciones[tipo] = {
                    'top_5_transacciones': top_transacciones,
                    'rango_fechas': {
                        'fecha_min': tipo_data['date'].min().strftime('%Y-%m-%d') if pd.notna(tipo_data['date'].min()) else None,
                        'fecha_max': tipo_data['date'].max().strftime('%Y-%m-%d') if pd.notna(tipo_data['date'].max()) else None
                    }
                }

        # 4. Resumen ejecutivo
        total_ingresos = income_data['amount_gross'].sum()
        total_comisiones = income_data['commission_total'].sum()
        ingreso_neto = total_ingresos - total_comisiones

        # Encontrar el tipo más rentable (mayor porcentaje de contribución neta)
        tipos_por_rentabilidad = {}
        for tipo in desglose_tipo:
            tipo_data = income_data[income_data['income_type'] == tipo]
            neto_tipo = tipo_data['amount_gross'].sum() - tipo_data['commission_total'].sum()
            tipos_por_rentabilidad[tipo] = neto_tipo

        tipo_mas_rentable = max(tipos_por_rentabilidad, key=tipos_por_rentabilidad.get) if tipos_por_rentabilidad else None

        resumen_ejecutivo = {
            'total_ingresos_brutos': round(total_ingresos, 2),
            'total_comisiones': round(total_comisiones, 2),
            'ingreso_neto_total': round(ingreso_neto, 2),
            'margen_promedio': round((ingreso_neto / total_ingresos * 100), 1) if total_ingresos > 0 else 0,
            'tipo_ingreso_principal': max(desglose_tipo, key=lambda x: desglose_tipo[x]['monto_total']) if desglose_tipo else None,
            'tipo_mas_rentable': tipo_mas_rentable,
            'periodo_analizado': {
                'fecha_desde': income_data['date'].min().strftime('%Y-%m-%d') if pd.notna(income_data['date'].min()) else None,
                'fecha_hasta': income_data['date'].max().strftime('%Y-%m-%d') if pd.notna(income_data['date'].max()) else None
            }
        }

        return {
            'total_ingresos': round(total_ingresos, 2),
            'desglose_por_tipo': desglose_tipo,
            'desglose_por_metodo': desglose_metodo,
            'detalle_transacciones': detalle_transacciones,
            'resumen_ejecutivo': resumen_ejecutivo
        }

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

        # Agregar desglose detallado de ingresos
        income_breakdown = self.get_income_breakdown()
        stats['income_breakdown_detailed'] = income_breakdown

        # Desglose simple de ingresos por tipo (mantener compatibilidad)
        income_data = self.unified_data[self.unified_data['amount_gross'] > 0]
        if not income_data.empty:
            income_breakdown_simple = income_data.groupby('income_type')['amount_gross'].sum().to_dict()
            stats['income_breakdown'] = income_breakdown_simple
            stats['total_income'] = income_data['amount_gross'].sum()
        else:
            stats['income_breakdown'] = {}
            stats['total_income'] = 0

        # Desglose de gastos por tipo
        expense_data = self.unified_data[self.unified_data['amount_gross'] < 0]
        if not expense_data.empty:
            expense_breakdown = expense_data.groupby('income_type')['amount_gross'].sum().to_dict()
            stats['expense_breakdown'] = expense_breakdown
            stats['total_expenses'] = expense_data['amount_gross'].sum()
        else:
            stats['expense_breakdown'] = {}
            stats['total_expenses'] = 0

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

