#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaz Web para el Sistema de Procesamiento de Pagos - Peña Linda Bungalows
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import logging
import os
from data_processor import PaymentDataProcessor
from pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(
    page_title="Peña Linda Bungalows - Análisis de Pagos",
    page_icon="🏨",
    layout="wide"
)

# Inicializar el procesador
@st.cache_resource
def get_processor(cache_buster=None): # Añadir un argumento dummy para forzar la recarga de la caché
    return PaymentDataProcessor()

def main():
    st.title("🏨 Peña Linda Bungalows - Sistema de Análisis de Pagos")
    st.markdown("---")

    processor = get_processor(cache_buster=datetime.now()) # Pasar un valor dinámico para invalidar la caché
    
    # Sidebar para carga de archivos
    st.sidebar.header("📁 Cargar Archivos de Datos")
    
    # Upload de archivos
    izipay_file = st.sidebar.file_uploader(
        "Archivo Izipay (.csv)",
        type=['csv'],
        help="Archivo de transacciones de Izipay (separado por punto y coma)"
    )
    
    culqi_file = st.sidebar.file_uploader(
        "Archivo Culqi (.csv)",
        type=['csv'],
        help="Archivo de transacciones de Culqi (separado por coma)"
    )
    
    secured_file = st.sidebar.file_uploader(
        "Ingresos Sirvoy / Transferencias Directas (.csv)",
        type=['csv'],
        help="Archivo de ingresos de Sirvoy (payments_export) o transferencias bancarias directas"
    )
    
    facebook_file = st.sidebar.file_uploader(
        "Archivo Facebook Ads (.csv)",
        type=['csv'],
        help="Archivo de facturación de Facebook Ads"
    )
    
    gastos_sirvoy_excel = 0
    
    # Cargar datos de Sirvoy
    sirvoy_file = st.sidebar.file_uploader(
        "Gastos Sirvoy (.csv)",
        type=['csv'],
        help="Archivo de gastos/cobros de Sirvoy (historial de recargas y gastos del servicio). Puedes cargar múltiples archivos."
    )

    # Rastrear archivos de Sirvoy cargados anteriormente
    if 'sirvoy_files_loaded' not in st.session_state:
        st.session_state.sirvoy_files_loaded = {
            'sirvoy_file': False,
            'secured_file': False
        }
    
    # Rastrear IDs de archivos procesados para evitar duplicados y acumulacion
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = {
            'sirvoy_file': None,
            'secured_file': None
        }
    
    # Verificar si los archivos fueron eliminados
    sirvoy_files_present = (sirvoy_file is not None) or (secured_file is not None)
    
    # Si un archivo específico fue eliminado, limpiar solo esa parte de los datos
    if sirvoy_file is None and st.session_state.sirvoy_files_loaded['sirvoy_file']:
        # Archivo de gastos eliminado, remover solo gastos de los datos combinados
        if 'sirvoy_data_combined' in st.session_state and st.session_state.sirvoy_data_combined is not None:
            if 'es_facturacion' in st.session_state.sirvoy_data_combined.columns:
                # Filtrar solo ingresos (mantener solo los que NO son facturación)
                st.session_state.sirvoy_data_combined = st.session_state.sirvoy_data_combined[
                    st.session_state.sirvoy_data_combined['es_facturacion'] == False
                ].copy()
                if st.session_state.sirvoy_data_combined.empty:
                    st.session_state.sirvoy_data_combined = None
                    processor.sirvoy_data = pd.DataFrame()
                else:
                    processor.sirvoy_data = st.session_state.sirvoy_data_combined
        else:
            processor.sirvoy_data = pd.DataFrame()
        st.session_state.sirvoy_files_loaded['sirvoy_file'] = False
        st.session_state.processed_files['sirvoy_file'] = None
    
    if secured_file is None and st.session_state.sirvoy_files_loaded['secured_file']:
        # Archivo de ingresos eliminado, remover solo ingresos de los datos combinados
        if 'sirvoy_data_combined' in st.session_state and st.session_state.sirvoy_data_combined is not None:
            if 'es_facturacion' in st.session_state.sirvoy_data_combined.columns:
                # Filtrar solo gastos (mantener solo los que SÍ son facturación)
                st.session_state.sirvoy_data_combined = st.session_state.sirvoy_data_combined[
                    st.session_state.sirvoy_data_combined['es_facturacion'] == True
                ].copy()
                if st.session_state.sirvoy_data_combined.empty:
                    st.session_state.sirvoy_data_combined = None
                    processor.sirvoy_data = pd.DataFrame()
                else:
                    processor.sirvoy_data = st.session_state.sirvoy_data_combined
        else:
            processor.sirvoy_data = pd.DataFrame()
        st.session_state.sirvoy_files_loaded['secured_file'] = False
        st.session_state.processed_files['secured_file'] = None
    
    # Si ambos archivos fueron eliminados, limpiar completamente
    if not sirvoy_files_present:
        if st.session_state.sirvoy_files_loaded['sirvoy_file'] or st.session_state.sirvoy_files_loaded['secured_file']:
            # Ambos archivos fueron eliminados, limpiar todos los datos de Sirvoy
            if 'sirvoy_data_combined' in st.session_state:
                st.session_state.sirvoy_data_combined = None
            processor.sirvoy_data = pd.DataFrame()
            st.session_state.sirvoy_files_loaded['sirvoy_file'] = False
            st.session_state.sirvoy_files_loaded['secured_file'] = False
            st.session_state.processed_files['sirvoy_file'] = None
            st.session_state.processed_files['secured_file'] = None
    
    # Botón para limpiar datos de Sirvoy (solo afecta a Sirvoy, no a otros datos)
    if 'sirvoy_data_combined' in st.session_state and st.session_state.sirvoy_data_combined is not None:
        if st.sidebar.button("🗑️ Limpiar datos de Sirvoy", help="Elimina todos los datos de Sirvoy (ingresos y gastos) cargados. No afecta a Izipay, Culqi, Openpay u otros datos."):
            # Solo limpiar datos de Sirvoy, preservar todos los demás datos
            st.session_state.sirvoy_data_combined = None
            processor.sirvoy_data = pd.DataFrame()  # DataFrame vacío en lugar de None para evitar errores
            st.sidebar.success("✅ Datos de Sirvoy limpiados (ingresos y gastos)")
            st.rerun()

    openpay_file = st.sidebar.file_uploader(
        "Archivo Openpay (.csv)",
        type=['csv'],
        help="Archivo de transacciones de Openpay"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("💸 Gastos Adicionales")
    
    # Inicializar gastos adicionales en session_state
    if 'gastos_adicionales' not in st.session_state:
        st.session_state.gastos_adicionales = []
    
    # Formulario para agregar gastos
    with st.sidebar.expander("➕ Agregar Gasto", expanded=False):
        with st.form("agregar_gasto"):
            nombre_gasto = st.text_input("Nombre del gasto", placeholder="Ej: Mantenimiento, Servicios, etc.")
            monto_gasto = st.number_input("Monto (S/)", min_value=0.0, step=0.01, format="%.2f")
            fecha_gasto = st.date_input("Fecha del gasto")
            
            submitted = st.form_submit_button("Agregar Gasto")
            
            if submitted and nombre_gasto and monto_gasto > 0:
                nuevo_gasto = {
                    'nombre': nombre_gasto,
                    'monto': monto_gasto,
                    'fecha': fecha_gasto,
                    'id': len(st.session_state.gastos_adicionales)
                }
                st.session_state.gastos_adicionales.append(nuevo_gasto)
                st.success(f"Gasto agregado: {nombre_gasto} - S/ {monto_gasto:,.2f}")
                st.rerun()
    
    # Mostrar gastos existentes
    if st.session_state.gastos_adicionales:
        st.sidebar.subheader("📋 Gastos Registrados")
        total_gastos_adicionales = 0
        
        for i, gasto in enumerate(st.session_state.gastos_adicionales):
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                st.write(f"**{gasto['nombre']}**")
                st.write(f"S/ {gasto['monto']:,.2f} - {gasto['fecha']}")
            with col2:
                if st.button("🗑️", key=f"delete_{i}", help="Eliminar gasto"):
                    st.session_state.gastos_adicionales.pop(i)
                    st.rerun()
            
            total_gastos_adicionales += gasto['monto']
            st.sidebar.markdown("---")
        
        st.sidebar.metric("Total Gastos Adicionales", f"S/ {total_gastos_adicionales:,.2f}")
    else:
        st.sidebar.info("No hay gastos adicionales registrados")
    
    # LIMPIAR datos del procesador si no hay archivos cargados
    # Esto evita que los datos se acumulen cuando el usuario elimina archivos
    # IMPORTANTE: Solo limpiar si realmente no hay archivo cargado (no si es None por primera vez)
    # Usar una bandera para detectar si es la primera carga o si el usuario eliminó el archivo
    if 'files_loaded' not in st.session_state:
        st.session_state.files_loaded = {
            'izipay': False,
            'culqi': False,
            'openpay': False,
            'secured': False,
            'facebook': False
        }
    
    # Si no hay archivo cargado Y anteriormente había uno, limpiar los datos
    if izipay_file is None and st.session_state.files_loaded['izipay']:
        processor.izipay_data = pd.DataFrame()
        st.session_state.files_loaded['izipay'] = False
    if culqi_file is None and st.session_state.files_loaded['culqi']:
        processor.culqi_data = pd.DataFrame()
        st.session_state.files_loaded['culqi'] = False
    if openpay_file is None and st.session_state.files_loaded['openpay']:
        processor.openpay_data = pd.DataFrame()
        st.session_state.files_loaded['openpay'] = False
    if secured_file is None and st.session_state.files_loaded['secured']:
        processor.secured_data = pd.DataFrame()
        st.session_state.files_loaded['secured'] = False
    if facebook_file is None and st.session_state.files_loaded['facebook']:
        processor.facebook_data = pd.DataFrame()
        st.session_state.files_loaded['facebook'] = False
    # Nota: sirvoy_data se maneja con session_state, no se limpia aquí
    
    # Procesar archivos cargados
    data_loaded = False

    if izipay_file is not None:
        try:
            df_izipay = processor.load_izipay_data(izipay_file)
            if not df_izipay.empty:
                st.sidebar.success(f"✅ Izipay: {len(df_izipay)} registros cargados")
                st.session_state.files_loaded['izipay'] = True
                data_loaded = True
            else:
                st.sidebar.warning("⚠️ Izipay: No se cargaron registros válidos.")
        except Exception as e:
            st.sidebar.error(f"Error procesando Izipay: {e}")

    if culqi_file is not None:
        try:
            df_culqi = processor.load_culqi_data(culqi_file)
            if not df_culqi.empty:
                st.sidebar.success(f"✅ Culqi: {len(df_culqi)} registros cargados")
                st.session_state.files_loaded['culqi'] = True
                data_loaded = True
            else:
                st.sidebar.warning("⚠️ Culqi: No se cargaron registros válidos.")
        except Exception as e:
            st.sidebar.error(f"Error procesando Culqi: {e}")

    if secured_file is not None:
        try:
            # Verificar si es formato de Sirvoy antes de cargar
            content = secured_file.getvalue()
            df_check = pd.read_csv(io.BytesIO(content), encoding='utf-8', header=0, nrows=1)
            df_check.columns = df_check.columns.str.strip().str.replace('"', '')
            es_sirvoy = 'Payment Id' in df_check.columns or 'Date' in df_check.columns or 'Amount' in df_check.columns
            
            if es_sirvoy:
                # Generar ID único del archivo
                file_id = f"{secured_file.name}_{secured_file.size}"
                
                # Verificar si ya fue procesado para evitar duplicados
                if st.session_state.processed_files['secured_file'] != file_id:
                    # Es formato de Sirvoy, procesar como Sirvoy y guardar en session_state
                    if 'sirvoy_data_combined' not in st.session_state:
                        st.session_state.sirvoy_data_combined = None
                    
                    # Resetear el archivo para que load_sirvoy_data pueda leerlo
                    # Crear una copia del contenido para evitar problemas con el seek
                    secured_file.seek(0)
                    file_content = secured_file.read()
                    secured_file.seek(0)
                    
                    # Crear un objeto BytesIO con el contenido para load_sirvoy_data
                    file_copy = io.BytesIO(file_content)
                    df_sirvoy_new = processor.load_sirvoy_data(file_copy)
                    
                    if not df_sirvoy_new.empty:
                        # Marcar que se cargó un archivo desde secured_file
                        st.session_state.sirvoy_files_loaded['secured_file'] = True
                        st.session_state.processed_files['secured_file'] = file_id
                        
                        # LIMPIEZA: Eliminar datos anteriores de este tipo (Ingresos)
                        # secured_file trae Ingresos (es_facturacion=False)
                        if st.session_state.sirvoy_data_combined is not None and not st.session_state.sirvoy_data_combined.empty:
                            if 'es_facturacion' in st.session_state.sirvoy_data_combined.columns:
                                # Mantener solo gastos (es_facturacion=True)
                                st.session_state.sirvoy_data_combined = st.session_state.sirvoy_data_combined[
                                    st.session_state.sirvoy_data_combined['es_facturacion'] == True
                                ].copy()
                        
                        # Combinar con datos existentes si los hay
                        if st.session_state.sirvoy_data_combined is not None and not st.session_state.sirvoy_data_combined.empty:
                            # Verificar que ambas columnas es_facturacion existan y sean compatibles
                            if 'es_facturacion' not in df_sirvoy_new.columns:
                                # Si el nuevo no tiene es_facturacion, agregarlo (False para payments_export)
                                df_sirvoy_new['es_facturacion'] = False
                            if 'es_facturacion' not in st.session_state.sirvoy_data_combined.columns:
                                # Si el existente no tiene es_facturacion, agregarlo según sus columnas
                                if 'url_sirvoy' in st.session_state.sirvoy_data_combined.columns or 'tipo_sirvoy' in st.session_state.sirvoy_data_combined.columns:
                                    st.session_state.sirvoy_data_combined['es_facturacion'] = True
                                else:
                                    st.session_state.sirvoy_data_combined['es_facturacion'] = False
                            
                            df_sirvoy_combined = pd.concat([st.session_state.sirvoy_data_combined, df_sirvoy_new], ignore_index=True)
                            st.session_state.sirvoy_data_combined = df_sirvoy_combined
                            st.sidebar.success(f"✅ Ingresos Sirvoy: {len(df_sirvoy_new)} nuevos registros. Total: {len(df_sirvoy_combined)} registros")
                        else:
                            # Primera carga - asegurar que tenga es_facturacion
                            if 'es_facturacion' not in df_sirvoy_new.columns:
                                df_sirvoy_new['es_facturacion'] = False  # payments_export es False
                            st.session_state.sirvoy_data_combined = df_sirvoy_new
                            st.sidebar.success(f"✅ Ingresos Sirvoy: {len(df_sirvoy_new)} registros cargados")
                        
                        # Actualizar el procesador con los datos combinados
                        processor.sirvoy_data = st.session_state.sirvoy_data_combined
                        data_loaded = True
                    else:
                        st.sidebar.warning("⚠️ Ingresos Sirvoy: No se cargaron registros válidos.")
                else:
                    # Ya fue procesado, solo asegurar que data_loaded es True si hay datos
                    data_loaded = True
            else:
                # Es formato de transferencias directas normal
                df_secured = processor.load_secured_data(secured_file)
                if not df_secured.empty:
                    st.sidebar.success(f"✅ Transferencias: {len(df_secured)} registros cargados")
                    st.session_state.files_loaded['secured'] = True
                    data_loaded = True
                else:
                    st.sidebar.warning("⚠️ Transferencias: No se cargaron registros válidos.")
        except Exception as e:
            st.sidebar.error(f"Error procesando Transferencias: {e}")
            import traceback
            st.sidebar.error(traceback.format_exc())

    if facebook_file is not None:
        try:
            # Generar ID único del archivo para evitar reprocesamiento
            file_id = f"{facebook_file.name}_{facebook_file.size}"
            
            # Verificar si ya fue procesado
            if 'processed_files' not in st.session_state:
                st.session_state.processed_files = {}
            
            if st.session_state.processed_files.get('facebook_file') != file_id:
                df_facebook = processor.load_facebook_data(facebook_file)
                if not df_facebook.empty:
                    # Asegurar que los datos se guardan en el procesador
                    processor.facebook_data = df_facebook
                    # Guardar backup en session_state para persistencia entre ejecuciones
                    st.session_state.facebook_data_backup = df_facebook.copy()
                    st.sidebar.success(f"✅ Facebook Ads: {len(df_facebook)} registros cargados")
                    st.session_state.files_loaded['facebook'] = True
                    st.session_state.processed_files['facebook_file'] = file_id
                    data_loaded = True
                else:
                    st.sidebar.warning("⚠️ Facebook Ads: No se cargaron registros válidos.")
            else:
                # Ya fue procesado, restaurar desde session_state si es necesario
                if 'facebook_data_backup' in st.session_state and not st.session_state.facebook_data_backup.empty:
                    processor.facebook_data = st.session_state.facebook_data_backup.copy()
                if processor.facebook_data is not None and not processor.facebook_data.empty:
                    data_loaded = True
        except Exception as e:
            st.sidebar.error(f"Error procesando Facebook: {e}")
            import traceback
            st.sidebar.error(traceback.format_exc())

    if sirvoy_file is not None:
        try:
            # Generar ID único del archivo
            file_id = f"{sirvoy_file.name}_{sirvoy_file.size}"
            
            # Verificar si ya fue procesado
            if st.session_state.processed_files['sirvoy_file'] != file_id:
                # Usar session_state para mantener los datos de Sirvoy entre cargas
                if 'sirvoy_data_combined' not in st.session_state:
                    st.session_state.sirvoy_data_combined = None
                
                # Cargar el nuevo archivo
                df_sirvoy_new = processor.load_sirvoy_data(sirvoy_file)
                
                if not df_sirvoy_new.empty:
                    # Marcar que se cargó un archivo desde sirvoy_file
                    st.session_state.sirvoy_files_loaded['sirvoy_file'] = True
                    st.session_state.processed_files['sirvoy_file'] = file_id
                    
                    # LIMPIEZA: Eliminar datos anteriores de este tipo (Gastos)
                    # sirvoy_file trae Gastos (es_facturacion=True)
                    if st.session_state.sirvoy_data_combined is not None and not st.session_state.sirvoy_data_combined.empty:
                        if 'es_facturacion' in st.session_state.sirvoy_data_combined.columns:
                            # Mantener solo ingresos (es_facturacion=False)
                            st.session_state.sirvoy_data_combined = st.session_state.sirvoy_data_combined[
                                st.session_state.sirvoy_data_combined['es_facturacion'] == False
                            ].copy()
                    
                    # Combinar con datos existentes si los hay
                    if st.session_state.sirvoy_data_combined is not None and not st.session_state.sirvoy_data_combined.empty:
                        # Verificar que ambas columnas es_facturacion existan y sean compatibles
                        if 'es_facturacion' not in df_sirvoy_new.columns:
                            # Si el nuevo no tiene es_facturacion, agregarlo según sus columnas
                            if 'url_sirvoy' in df_sirvoy_new.columns or 'tipo_sirvoy' in df_sirvoy_new.columns:
                                df_sirvoy_new['es_facturacion'] = True  # Es facturación
                            else:
                                df_sirvoy_new['es_facturacion'] = False  # Es payments_export
                        if 'es_facturacion' not in st.session_state.sirvoy_data_combined.columns:
                            # Si el existente no tiene es_facturacion, agregarlo según sus columnas
                            if 'url_sirvoy' in st.session_state.sirvoy_data_combined.columns or 'tipo_sirvoy' in st.session_state.sirvoy_data_combined.columns:
                                st.session_state.sirvoy_data_combined['es_facturacion'] = True
                            else:
                                st.session_state.sirvoy_data_combined['es_facturacion'] = False
                        
                        # Combinar los nuevos datos con los existentes
                        df_sirvoy_combined = pd.concat([st.session_state.sirvoy_data_combined, df_sirvoy_new], ignore_index=True)
                        st.session_state.sirvoy_data_combined = df_sirvoy_combined
                        # Determinar si son gastos o ingresos para el mensaje
                        if 'es_facturacion' in df_sirvoy_new.columns:
                            es_gasto = df_sirvoy_new['es_facturacion'].any()
                            tipo_mensaje = "Gastos Sirvoy" if es_gasto else "Ingresos Sirvoy"
                        else:
                            tipo_mensaje = "Sirvoy"
                        st.sidebar.success(f"✅ {tipo_mensaje}: {len(df_sirvoy_new)} nuevos registros cargados. Total: {len(df_sirvoy_combined)} registros")
                    else:
                        # Primera carga - asegurar que tenga es_facturacion
                        if 'es_facturacion' not in df_sirvoy_new.columns:
                            # Detectar si es facturación o payments_export
                            if 'url_sirvoy' in df_sirvoy_new.columns or 'tipo_sirvoy' in df_sirvoy_new.columns:
                                df_sirvoy_new['es_facturacion'] = True  # Es facturación
                            else:
                                df_sirvoy_new['es_facturacion'] = False  # Es payments_export
                        st.session_state.sirvoy_data_combined = df_sirvoy_new
                        # Determinar si son gastos o ingresos para el mensaje
                        if 'es_facturacion' in df_sirvoy_new.columns:
                            es_gasto = df_sirvoy_new['es_facturacion'].any()
                            tipo_mensaje = "Gastos Sirvoy" if es_gasto else "Ingresos Sirvoy"
                        else:
                            tipo_mensaje = "Sirvoy"
                        st.sidebar.success(f"✅ {tipo_mensaje}: {len(df_sirvoy_new)} registros cargados")
                    
                    # Actualizar el procesador con los datos combinados
                    processor.sirvoy_data = st.session_state.sirvoy_data_combined
                    data_loaded = True
                else:
                    st.sidebar.warning("⚠️ Gastos Sirvoy: No se cargaron registros válidos.")
            else:
                # Ya fue procesado
                data_loaded = True
        except Exception as e:
            st.sidebar.error(f"Error procesando Sirvoy: {e}")
            import traceback
            st.sidebar.error(traceback.format_exc())
    
    # CRÍTICO: Sincronizar processor.sirvoy_data con session_state ANTES de unify_data()
    # Esto asegura que los datos estén actualizados y limpios
    if sirvoy_files_present:
        # Hay archivos cargados, usar datos de session_state
        if 'sirvoy_data_combined' in st.session_state and st.session_state.sirvoy_data_combined is not None:
            processor.sirvoy_data = st.session_state.sirvoy_data_combined.copy()  # Copia explícita
            # Mostrar estadísticas de los datos combinados
            if 'es_facturacion' in st.session_state.sirvoy_data_combined.columns:
                facturacion_count = len(st.session_state.sirvoy_data_combined[st.session_state.sirvoy_data_combined['es_facturacion'] == True])
                payments_count = len(st.session_state.sirvoy_data_combined[st.session_state.sirvoy_data_combined['es_facturacion'] == False])
                st.sidebar.info(f"📊 Sirvoy: {len(st.session_state.sirvoy_data_combined)} registros totales ({facturacion_count} gastos, {payments_count} ingresos)")
            else:
                st.sidebar.info(f"📊 Sirvoy: {len(st.session_state.sirvoy_data_combined)} registros combinados")
        else:
            # No hay datos en session_state pero hay archivos cargados (primera carga)
            processor.sirvoy_data = pd.DataFrame()
    else:
        # NO hay archivos cargados - LIMPIAR COMPLETAMENTE
        processor.sirvoy_data = pd.DataFrame()
        # También limpiar session_state si existe
        if 'sirvoy_data_combined' in st.session_state:
            st.session_state.sirvoy_data_combined = None
    
    if openpay_file is not None:
        try:
            df_openpay = processor.load_openpay_data(openpay_file)
            if not df_openpay.empty:
                st.sidebar.success(f"✅ Openpay: {len(df_openpay)} registros cargados")
                st.session_state.files_loaded['openpay'] = True
                data_loaded = True
            else:
                st.sidebar.warning("⚠️ Openpay: No se cargaron registros válidos.")
        except Exception as e:
            st.sidebar.error(f"Error procesando Openpay: {e}")

    if not data_loaded:
        st.info("👆 Por favor, carga al menos un archivo de datos en la barra lateral para comenzar.")
        st.markdown("""
        ### 📋 Formatos de Archivo Soportados:
        
        **Izipay**: Archivo CSV con separador punto y coma (;)
        - Contiene transacciones de tarjetas de crédito/débito
        - Incluye información de comisiones y estados de transacción
        
        **Culqi**: Archivo CSV con separador coma (,)
        - Transacciones de POS terminal y pagos digitales
        - Incluye información detallada de comisiones
        
        **Transferencias Directas**: Archivo CSV con transferencias bancarias
        - Pagos directos y transferencias
        - Formato simplificado
        
        **Facebook Ads**: Archivo CSV de facturación de Facebook
        - Gastos en publicidad de Facebook/Meta
        - Información de transacciones publicitarias
        
        **Openpay**: Archivo CSV con transacciones de Openpay
        - Pagos con tarjeta
        - Incluye información de fecha, tarjeta y monto (columnas 'odd'/'even')
        """)
        return
    
    # VALIDACIÓN FINAL: Asegurar que processor.sirvoy_data esté sincronizado
    # Esto es crítico para evitar que datos antiguos se procesen
    if not sirvoy_files_present:
        # No hay archivos, forzar limpieza completa
        processor.sirvoy_data = pd.DataFrame()
        if 'sirvoy_data_combined' in st.session_state:
            st.session_state.sirvoy_data_combined = None
    
    # IMPORTANTE: Asegurar que los datos de Facebook estén en el procesador antes de unificar
    # Verificar si hay datos de Facebook en session_state que no estén en el procesador
    if 'facebook_data_backup' in st.session_state and not st.session_state.facebook_data_backup.empty:
        if processor.facebook_data is None or processor.facebook_data.empty:
            processor.facebook_data = st.session_state.facebook_data_backup
            logger.info(f"Restaurados {len(processor.facebook_data)} registros de Facebook desde session_state")
    
    # Unificar datos
    unified_data = processor.unify_data()
    
    # Guardar backup de datos de Facebook en session_state para persistencia
    if processor.facebook_data is not None and not processor.facebook_data.empty:
        st.session_state.facebook_data_backup = processor.facebook_data.copy()
        logger.info("VALIDACIÓN: No hay archivos Sirvoy cargados - datos limpiados antes de unify_data()")
    elif sirvoy_files_present:
        # Hay archivos, sincronizar con session_state
        if 'sirvoy_data_combined' in st.session_state and st.session_state.sirvoy_data_combined is not None:
            processor.sirvoy_data = st.session_state.sirvoy_data_combined.copy()
            logger.info(f"VALIDACIÓN: Sincronizado processor.sirvoy_data con session_state ({len(processor.sirvoy_data)} registros)")
        else:
            processor.sirvoy_data = pd.DataFrame()
            logger.info("VALIDACIÓN: Hay archivos pero no hay datos en session_state - limpiando processor")
    
    # Unificar datos
    unified_data = processor.unify_data()
    
    if unified_data.empty:
        st.error("❌ No se pudieron procesar los datos. Verifica el formato de los archivos.")
        return
    
    # Filtros en la sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por fechas
    if not unified_data['date'].isna().all():
        min_date = unified_data['date'].min().date()
        max_date = unified_data['date'].max().date()
        
        date_range = st.sidebar.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (unified_data['date'].dt.date >= start_date) & (unified_data['date'].dt.date <= end_date)
            filtered_data = unified_data[mask]
        else:
            filtered_data = unified_data
    else:
        filtered_data = unified_data
    
    # Filtro por procesador
    processors = ['Todos'] + list(filtered_data['processor'].unique())
    selected_processor = st.sidebar.selectbox("Procesador de Pago", processors)
    
    if selected_processor != 'Todos':
        filtered_data = filtered_data[filtered_data['processor'] == selected_processor]
    
    # Filtro por método de pago
    payment_methods = ['Todos'] + list(filtered_data['payment_method'].unique())
    selected_method = st.sidebar.selectbox("Método de Pago", payment_methods)
    
    if selected_method != 'Todos':
        filtered_data = filtered_data[filtered_data['payment_method'] == selected_method]
    
    # Filtro por rango de montos
    if not filtered_data.empty:
        min_amount = float(filtered_data['amount'].min())
        max_amount = float(filtered_data['amount'].max())
        
        # Verificar que min y max sean diferentes para evitar error del slider
        if min_amount < max_amount:
            amount_range = st.sidebar.slider(
                "Rango de Montos (S/)",
                min_value=min_amount,
                max_value=max_amount,
                value=(min_amount, max_amount),
                step=10.0
            )
            
            filtered_data = filtered_data[
                (filtered_data['amount'] >= amount_range[0]) & 
                (filtered_data['amount'] <= amount_range[1])
            ]
        else:
            # Si todos los valores son iguales, mostrar información
            st.sidebar.info(f"Todos los montos son: S/ {min_amount:,.2f}")
    
    # Filtro adicional: Separar ingresos y gastos
    transaction_type = st.sidebar.selectbox(
        "Tipo de Transacción",
        ["Todos", "Solo Ingresos", "Solo Gastos"]
    )
    
    if transaction_type == "Solo Ingresos":
        filtered_data = filtered_data[filtered_data['amount_gross'] > 0]
    elif transaction_type == "Solo Gastos":
        filtered_data = filtered_data[filtered_data['amount_gross'] < 0]
    
    # Dashboard principal
    if not filtered_data.empty:
        # --- MÉTRICAS PRINCIPALES (SOLO TRANSFERENCIAS Y EFECTIVO) ---
        # Crear un dataframe específico para el resumen que solo incluya Transferencias, Efectivo y sus Ajustes
        summary_data = filtered_data[
            filtered_data['income_type'].isin(['Transferencia', 'Efectivo', 'Ajuste'])
        ].copy()

        # Recalcular las métricas solo con los datos de transferencias/efectivo
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Transacciones",
                f"{len(filtered_data):,}"
            )

        with col2:
            # Separar ingresos y gastos
            # IMPORTANTE: Excluir explícitamente los gastos de Sirvoy (income_type == 'Gasto')
            # Los ajustes negativos se manejan por separado para transparencia
            ingresos_data_filtered = filtered_data[
                (filtered_data['amount_gross'] > 0) & 
                (filtered_data['income_type'] != 'Gasto')  # Excluir gastos de Sirvoy
            ]
            
            # IMPORTANTE: Los "Ingresos Brutos" deben ser la BASE sobre la cual se calculó la comisión
            # La comisión se calcula sobre cada transacción positiva ANTES de ajustes
            # Por lo tanto, Ingresos Brutos = suma de amount_gross de transacciones positivas
            ingresos_brutos_base = ingresos_data_filtered['amount_gross'].sum()
            
            # Ajustes negativos de Sirvoy (devoluciones/correcciones) se muestran por separado
            ajustes_negativos = filtered_data[
                (filtered_data['source'] == 'Sirvoy') & 
                (filtered_data['income_type'] == 'Ajuste') &
                (filtered_data['amount_gross'] < 0)
            ]
            total_ajustes_negativos = ajustes_negativos['amount_gross'].sum()
            
            # Ingresos netos después de ajustes (para cálculos internos)
            ingresos = ingresos_brutos_base + total_ajustes_negativos  # Suma porque ajustes son negativos
            
            # Calcular gastos de Facebook específicamente
            gastos_facebook = abs(filtered_data[(filtered_data['processor'] == 'Facebook') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
            
            # Calcular gastos de Sirvoy (costos de plataforma - recargas y consumos)
            gastos_sirvoy = abs(filtered_data[(filtered_data['source'] == 'Sirvoy') & (filtered_data['income_type'] == 'Gasto') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
            
            # Agregar gastos adicionales
            gastos_adicionales_total = sum([g['monto'] for g in st.session_state.gastos_adicionales])
            
            # Total gastos (Facebook, Sirvoy y gastos adicionales)
            gastos_totales = gastos_facebook + gastos_sirvoy + gastos_adicionales_total
            
            # Mostrar Ingresos Brutos (base de comisión) con ajustes en el delta
            delta_text = f"Gastos: -S/ {gastos_totales:,.2f}"
            if total_ajustes_negativos < 0:
                delta_text += f" | Ajustes: S/ {total_ajustes_negativos:,.2f}"
            
            st.metric(
                "Ingresos Brutos",
                f"S/ {ingresos_brutos_base:,.2f}",
                delta=delta_text
            )
        
        with col3:
            total_commission = filtered_data['commission_total'].sum()
            commission_chamba = filtered_data['commission_chamba'].sum()
            
            st.metric(
                "Comisiones Totales",
                f"S/ {total_commission:,.2f}",
                delta=f"Chamba: S/ {commission_chamba:,.2f}"
            )

        with col4:
            # Ingreso neto final
            # Ingresos (netos de ajustes) - Gastos Totales - Comisiones
            neto_final = ingresos - gastos_totales - total_commission
            
            st.metric(
                "Ingresos Netos Finales",
                f"S/ {neto_final:,.2f}",
                delta=f"Margen: {(neto_final/ingresos_brutos_base*100) if ingresos_brutos_base > 0 else 0:.1f}%"
            )
            
        # Métricas secundarias
        col5, col6, col7 = st.columns(3)
        with col5:
            avg_ticket = ingresos_brutos_base / len(ingresos_data_filtered) if len(ingresos_data_filtered) > 0 else 0
            st.metric("Ticket Promedio", f"S/ {avg_ticket:,.2f}")
            
        with col6:
            # Mostrar porcentaje real de comisión Chamba sobre el bruto base
            pct_chamba = (commission_chamba / ingresos_brutos_base * 100) if ingresos_brutos_base > 0 else 0
            st.metric("Comisión Chamba (5%)", f"S/ {commission_chamba:,.2f}", f"{pct_chamba:.2f}% del bruto")
            
        with col7:
            commission_processor = filtered_data['commission_processor'].sum()
            pct_processor = (commission_processor / ingresos_brutos_base * 100) if ingresos_brutos_base > 0 else 0
            st.metric("Comisión Procesadores", f"S/ {commission_processor:,.2f}", f"{pct_processor:.2f}% del bruto")
        
        # --- RESUMEN FINANCIERO DETALLADO (Movido para mejor visibilidad) ---
        st.markdown("---")
        st.subheader("📋 Resumen Financiero Detallado")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric("Ingresos Brutos", f"S/ {ingresos_brutos_base:,.2f}")
            
            # Calcular detalles de Facebook
            fb_data_gastos = filtered_data[(filtered_data['source'] == 'Facebook Ads') & (filtered_data['amount_gross'] < 0)]
            monto_reportado_fb = abs(fb_data_gastos['amount_reported'].sum())
            ajuste_fb = fb_data_gastos['tax_adjustment'].sum()
            
            st.metric(
                "Gasto Real Facebook", 
                f"S/ {gastos_facebook:,.2f}",
                delta=f"Reportado: S/ {monto_reportado_fb:,.2f} | Ajuste: S/ {ajuste_fb:,.2f}"
            )
            
            # Calcular detalles de Sirvoy
            sirvoy_data_gastos = filtered_data[(filtered_data['source'] == 'Sirvoy') & (filtered_data['income_type'] == 'Gasto') & (filtered_data['amount_gross'] < 0)]
            monto_reportado_sirvoy = abs(sirvoy_data_gastos['amount_reported'].sum())
            ajuste_sirvoy = sirvoy_data_gastos['tax_adjustment'].sum()
            
            st.metric(
                "Gastos Sirvoy", 
                f"S/ {gastos_sirvoy:,.2f}",
                delta=f"Reportado: S/ {monto_reportado_sirvoy:,.2f} | Ajuste: S/ {ajuste_sirvoy:,.2f}"
            )
            
            st.metric("Gastos Adicionales", f"S/ {gastos_adicionales_total:,.2f}")
            st.metric("Gastos Totales", f"S/ {gastos_totales:,.2f}")
            st.metric("Comisiones Totales", f"S/ {total_commission:,.2f}")
            
        with col_res2:
            st.metric("Ingresos Netos Finales", f"S/ {neto_final:,.2f}")

            # Agregar ayuda contextual
            with st.expander("💡 ¿Cómo se calculan los Ingresos Netos Finales?", expanded=True):
                st.write("""
                **Fórmula:** Ingresos Brutos - Gastos Totales - Comisiones Totales

                **Detalles:**
                - **Ingresos Brutos**: Suma de todas las transacciones positivas (antes de comisiones).
                - **Gastos Totales**: Gasto Real Facebook + Gastos Sirvoy + Gastos Adicionales.
                - **Comisiones Totales**: Comisión Procesadores + Comisión Chamba Digital (5%).
                - **Ajustes**: Los ajustes por impuestos/diferencias se incluyen en los costos reales.
                """)
        
        # Nueva sección: Ingresos por Plataforma de Tarjeta
        st.markdown("---")
        st.subheader("💳 Ingresos por Plataforma de Pagos con Tarjeta")
        
        # Filtrar solo ingresos por tarjeta
        ingresos_tarjeta = filtered_data[
            (filtered_data['amount_gross'] > 0) & 
            (filtered_data['income_type'] == 'Tarjeta')
        ]
        
        if not ingresos_tarjeta.empty:
            # Calcular ingresos por cada plataforma
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                izipay_tarjeta = ingresos_tarjeta[ingresos_tarjeta['processor'] == 'Izipay']
                izipay_total = izipay_tarjeta['amount_gross'].sum()
                izipay_neto = izipay_tarjeta['amount_net'].sum()
                izipay_count = len(izipay_tarjeta)
                st.metric(
                    "💳 Izipay",
                    f"S/ {izipay_total:,.2f}",
                    delta=f"{izipay_count} transacciones | Neto: S/ {izipay_neto:,.2f}"
                )
            
            with col2:
                culqi_tarjeta = ingresos_tarjeta[ingresos_tarjeta['processor'] == 'Culqi']
                culqi_total = culqi_tarjeta['amount_gross'].sum()
                culqi_neto = culqi_tarjeta['amount_net'].sum()
                culqi_count = len(culqi_tarjeta)
                st.metric(
                    "💳 Culqi",
                    f"S/ {culqi_total:,.2f}",
                    delta=f"{culqi_count} transacciones | Neto: S/ {culqi_neto:,.2f}"
                )
            
            with col3:
                openpay_tarjeta = ingresos_tarjeta[ingresos_tarjeta['processor'] == 'Openpay']
                openpay_total = openpay_tarjeta['amount_gross'].sum()
                openpay_neto = openpay_tarjeta['amount_net'].sum()
                openpay_count = len(openpay_tarjeta)
                st.metric(
                    "💳 Openpay",
                    f"S/ {openpay_total:,.2f}",
                    delta=f"{openpay_count} transacciones | Neto: S/ {openpay_neto:,.2f}"
                )
            
            with col4:
                total_tarjeta = izipay_total + culqi_total + openpay_total
                total_tarjeta_neto = izipay_neto + culqi_neto + openpay_neto
                total_tarjeta_count = izipay_count + culqi_count + openpay_count
                st.metric(
                    "💰 Total Tarjetas",
                    f"S/ {total_tarjeta:,.2f}",
                    delta=f"{total_tarjeta_count} transacciones | Neto: S/ {total_tarjeta_neto:,.2f}"
                )
            
            # Gráfico de barras comparativo
            st.markdown("### 📊 Comparativa de Ingresos por Plataforma")
            plataformas_data = pd.DataFrame({
                'Plataforma': ['Izipay', 'Culqi', 'Openpay'],
                'Ingresos Brutos': [izipay_total, culqi_total, openpay_total],
                'Ingresos Netos': [izipay_neto, culqi_neto, openpay_neto],
                'Transacciones': [izipay_count, culqi_count, openpay_count]
            })
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_barras = px.bar(
                    plataformas_data,
                    x='Plataforma',
                    y='Ingresos Brutos',
                    title="Ingresos Brutos por Plataforma",
                    labels={'Ingresos Brutos': 'Monto (S/)', 'Plataforma': 'Plataforma'},
                    color='Plataforma',
                    color_discrete_map={
                        'Izipay': '#1f77b4',
                        'Culqi': '#ff7f0e',
                        'Openpay': '#2ca02c'
                    }
                )
                fig_barras.update_layout(showlegend=False)
                st.plotly_chart(fig_barras, use_container_width=True)
            
            with col2:
                fig_barras_neto = px.bar(
                    plataformas_data,
                    x='Plataforma',
                    y='Ingresos Netos',
                    title="Ingresos Netos por Plataforma",
                    labels={'Ingresos Netos': 'Monto (S/)', 'Plataforma': 'Plataforma'},
                    color='Plataforma',
                    color_discrete_map={
                        'Izipay': '#1f77b4',
                        'Culqi': '#ff7f0e',
                        'Openpay': '#2ca02c'
                    }
                )
                fig_barras_neto.update_layout(showlegend=False)
                st.plotly_chart(fig_barras_neto, use_container_width=True)
            
            # Tabla detallada
            st.markdown("### 📋 Detalle por Plataforma")
            detalle_plataformas = pd.DataFrame({
                'Plataforma': ['Izipay', 'Culqi', 'Openpay', '**TOTAL**'],
                'Transacciones': [
                    f"{izipay_count:,}",
                    f"{culqi_count:,}",
                    f"{openpay_count:,}",
                    f"**{total_tarjeta_count:,}**"
                ],
                'Ingresos Brutos (S/)': [
                    f"{izipay_total:,.2f}",
                    f"{culqi_total:,.2f}",
                    f"{openpay_total:,.2f}",
                    f"**{total_tarjeta:,.2f}**"
                ],
                'Comisiones Procesador (S/)': [
                    f"{izipay_tarjeta['commission_processor'].sum():,.2f}",
                    f"{culqi_tarjeta['commission_processor'].sum():,.2f}",
                    f"{openpay_tarjeta['commission_processor'].sum():,.2f}",
                    f"**{ingresos_tarjeta['commission_processor'].sum():,.2f}**"
                ],
                'Comisión Chamba (S/)': [
                    f"{izipay_tarjeta['commission_chamba'].sum():,.2f}",
                    f"{culqi_tarjeta['commission_chamba'].sum():,.2f}",
                    f"{openpay_tarjeta['commission_chamba'].sum():,.2f}",
                    f"**{ingresos_tarjeta['commission_chamba'].sum():,.2f}**"
                ],
                'Ingresos Netos (S/)': [
                    f"{izipay_neto:,.2f}",
                    f"{culqi_neto:,.2f}",
                    f"{openpay_neto:,.2f}",
                    f"**{total_tarjeta_neto:,.2f}**"
                ]
            })
            st.dataframe(detalle_plataformas, use_container_width=True, hide_index=True)
        else:
            st.info("No hay ingresos por tarjeta registrados en el período seleccionado.")
        
        # Crea DataFrames para cada tipo de gasto
        gastos_fb = filtered_data[(filtered_data['processor'] == 'Facebook') & (filtered_data['amount_gross'] < 0)].copy()
        # NOTA: Sirvoy ahora son INGRESOS, no gastos - se muestran en la sección de ingresos

        # Análisis de Facebook Ads
        if not gastos_fb.empty:
            st.markdown("---")
            st.subheader("📱 Análisis de Facebook Ads")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                monto_reportado_fb = abs(gastos_fb['amount_reported'].sum())
                st.metric("Monto Reportado", f"S/ {monto_reportado_fb:,.2f}", delta="Según reporte Facebook")
            with col2:
                ajuste_impuestos_fb = abs(gastos_fb['tax_adjustment'].sum())
                st.metric("Ajuste por Impuestos", f"S/ {ajuste_impuestos_fb:,.2f}", delta="11.11% + redondeo")
            with col3:
                gasto_real_fb = abs(gastos_fb['amount_gross'].sum())
                st.metric("Gasto Real", f"S/ {gasto_real_fb:,.2f}", delta="Cobrado en tarjeta")
            with col4:
                num_transacciones_fb = len(gastos_fb)
                promedio_gasto_fb = gasto_real_fb / num_transacciones_fb if num_transacciones_fb > 0 else 0
                st.metric("Gasto Promedio", f"S/ {promedio_gasto_fb:,.2f}", delta=f"{num_transacciones_fb} transacciones")
        
        # NOTA: Los datos de Sirvoy ahora son INGRESOS (pagos recibidos), no gastos
        # Se muestran en la sección "DETALLE DE INGRESOS POR TIPO DE PAGO" más abajo
                

        st.markdown("---")

        # Nueva sección: DETALLE DE INGRESOS POR TIPO DE PAGO
        st.subheader("📊 DETALLE DE INGRESOS POR TIPO DE PAGO")

        # Filtrar ingresos positivos Y ajustes negativos de Sirvoy (devoluciones/correcciones)
        # Los ajustes negativos deben incluirse para reflejar el ingreso real neto
        ingresos_data = filtered_data[
            ((filtered_data['amount_gross'] > 0) & (filtered_data['income_type'] != 'Gasto')) |
            ((filtered_data['income_type'] == 'Ajuste') & (filtered_data['source'] == 'Sirvoy'))
        ].copy()

        if not ingresos_data.empty:
            # Crear estructura de datos para la tabla detallada
            detalle_tipos = {
                'Pago con tarjeta': {'soles': 0, 'dolares': 0, 'recibido': 0, 'niubiz': 0, 'amex': 0, 'culqi': 0},
                'Transferencia o depósito': {'soles': 0, 'dolares': 0, 'recibido': 0, 'pendientes': 0, 'diners': 0, 'izipay_link': 0},
                'Efectivo': {'soles': 0, 'dolares': 0, 'recibido': 0, 'niubiz': 0, 'amex': 0, 'culqi': 0},
                'Otros': {'soles': 0, 'dolares': 0, 'recibido': 0, 'niubiz': 0, 'amex': 0, 'culqi': 0}
            }

            # Procesar cada tipo de pago
            for tipo_pago in detalle_tipos.keys():
                if tipo_pago == 'Pago con tarjeta':
                    # Total Vendido: Calcular desde Sirvoy (pagos con tarjeta reportados para CONTRASTE)
                    # NOTA: Los pagos con tarjeta de Sirvoy NO se cuentan como ingresos (ya están en Izipay/Culqi/Openpay)
                    # Se usan solo para comparar/verificar que coinciden con los pagos recibidos
                    sirvoy_raw_data = processor.sirvoy_data if processor.sirvoy_data is not None else pd.DataFrame()
                    if not sirvoy_raw_data.empty:
                        # Filtrar pagos con tarjeta de Sirvoy (datos originales, no procesados como ingresos)
                        sirvoy_card_raw = sirvoy_raw_data[
                            (sirvoy_raw_data['monto_eur'] > 0) & 
                            (sirvoy_raw_data['payment_method_sirvoy'].str.contains('tarjeta', case=False, na=False))
                        ]
                        # Aplicar filtros de fecha si existen (usar las mismas fechas del filtro principal)
                        if 'fecha' in sirvoy_card_raw.columns and not filtered_data.empty:
                            # Obtener fechas del filtro aplicado
                            min_date_filtered = filtered_data['date'].min()
                            max_date_filtered = filtered_data['date'].max()
                            sirvoy_card_raw = sirvoy_card_raw[
                                (sirvoy_card_raw['fecha'] >= min_date_filtered) & 
                                (sirvoy_card_raw['fecha'] <= max_date_filtered)
                            ]
                        monto_total_soles = sirvoy_card_raw['monto_eur'].sum() if not sirvoy_card_raw.empty else 0
                        monto_total_dolares = 0  # Asumir que todos están en PEN
                    else:
                        monto_total_soles = 0
                        monto_total_dolares = 0

                    # Total Recibido: Sumatoria de Izipay + Culqi + Openpay (TOTAL BRUTO sin descuentos)
                    # ESTOS son los ingresos reales por tarjeta - usar amount_gross (bruto) no amount_net
                    izipay_card_data = ingresos_data[(ingresos_data['processor'] == 'Izipay') & (ingresos_data['income_type'] == 'Tarjeta')]
                    culqi_card_data = ingresos_data[(ingresos_data['processor'] == 'Culqi') & (ingresos_data['income_type'] == 'Tarjeta')]
                    openpay_card_data = ingresos_data[(ingresos_data['processor'] == 'Openpay') & (ingresos_data['income_type'] == 'Tarjeta')]
                    monto_recibido = izipay_card_data['amount_gross'].sum() + culqi_card_data['amount_gross'].sum() + openpay_card_data['amount_gross'].sum()

                elif tipo_pago == 'Transferencia o depósito':
                    tipo_data = ingresos_data[ingresos_data['income_type'] == 'Transferencia']
                    # Total Vendido y Total Recibido deben ser BRUTOS (sin descuentos)
                    monto_total_soles = tipo_data[tipo_data['currency'] == 'PEN']['amount_gross'].sum()
                    monto_total_dolares = tipo_data[tipo_data['currency'] == 'USD']['amount_gross'].sum()
                    monto_recibido = tipo_data['amount_gross'].sum()
                    
                    logger.info(f"DEBUG TRANSFERENCIAS: Total bruto inicial: S/ {monto_recibido:,.2f} ({len(tipo_data)} transacciones)")
                    
                    # IMPORTANTE: Incluir ajustes negativos de Sirvoy (devoluciones/correcciones no canceladas)
                    # Estos afectan a las transferencias y deben restarse del total vendido Y recibido
                    ajustes_sirvoy = ingresos_data[
                        (ingresos_data['source'] == 'Sirvoy') & 
                        (ingresos_data['income_type'] == 'Ajuste')
                    ]
                    if not ajustes_sirvoy.empty:
                        monto_ajuste = ajustes_sirvoy['amount_gross'].sum()  # Ya es negativo
                        # Aplicar el ajuste tanto al total vendido como al recibido
                        monto_total_soles += monto_ajuste  # Sumar (restar porque es negativo)
                        monto_recibido += monto_ajuste  # Sumar (restar porque es negativo)
                        logger.info(f"Ajuste negativo de Sirvoy incluido en Transferencia: S/ {monto_ajuste:,.2f}")
                        logger.info(f"  Total Vendido después de ajuste: S/ {monto_total_soles:,.2f}")
                        logger.info(f"  Total Recibido después de ajuste: S/ {monto_recibido:,.2f}")
                    else:
                        logger.info("DEBUG TRANSFERENCIAS: No se encontraron ajustes negativos de Sirvoy")

                elif tipo_pago == 'Efectivo':
                    tipo_data = ingresos_data[ingresos_data['income_type'] == 'Efectivo']
                    # Total Vendido y Total Recibido deben ser BRUTOS (sin descuentos)
                    monto_total_soles = tipo_data[tipo_data['currency'] == 'PEN']['amount_gross'].sum()
                    monto_total_dolares = tipo_data[tipo_data['currency'] == 'USD']['amount_gross'].sum()
                    monto_recibido = tipo_data['amount_gross'].sum()

                else:  # Otros
                    tipo_data = ingresos_data[ingresos_data['income_type'] == 'Otros']
                    # Total Vendido y Total Recibido deben ser BRUTOS (sin descuentos)
                    monto_total_soles = tipo_data[tipo_data['currency'] == 'PEN']['amount_gross'].sum()
                    monto_total_dolares = tipo_data[tipo_data['currency'] == 'USD']['amount_gross'].sum()
                    monto_recibido = tipo_data['amount_gross'].sum()

                detalle_tipos[tipo_pago]['soles'] = monto_total_soles
                detalle_tipos[tipo_pago]['dolares'] = monto_total_dolares
                detalle_tipos[tipo_pago]['recibido'] = monto_recibido

                    # Nota: Los campos específicos de depósito necesitarían más lógica según los datos reales
                    # Por ahora usaré placeholders que se pueden ajustar según la estructura de datos

            # Crear tabla con el formato solicitado
            tabla_headers = [
                'Tipo de Pago',
                'Total Vendido (S/.)',
                'Total vendido ($)',
                'Total Recibido',
                'Depósitos de niubiz',
                'Depósitos American Express',
                'Depósitos Culqi'
            ]

            tabla_rows = []

            for tipo_pago, datos in detalle_tipos.items():
                if tipo_pago == 'Transferencia o depósito':
                    row = [
                        tipo_pago,
                        f"S/. {datos['soles']:,.2f}",
                        f"${datos['dolares']:,.2f}",
                        f"S/. {datos['recibido']:,.2f}",
                        "Depósitos pendientes",
                        "Depósitos Diners Club",
                        "Depósitos Izipay Link"
                    ]
                else:
                    row = [
                        tipo_pago,
                        f"S/. {datos['soles']:,.2f}",
                        f"${datos['dolares']:,.2f}",
                        f"S/. {datos['recibido']:,.2f}",
                        f"S/. {datos.get('niubiz', 0):,.2f}",
                        f"S/. {datos.get('amex', 0):,.2f}",
                        f"S/. {datos.get('culqi', 0):,.2f}"
                    ]
                tabla_rows.append(row)

            # Agregar fila de totales
            total_soles = sum(datos['soles'] for datos in detalle_tipos.values())
            total_dolares = sum(datos['dolares'] for datos in detalle_tipos.values())
            total_recibido = sum(datos['recibido'] for datos in detalle_tipos.values())

            tabla_rows.append([
                "Total",
                f"S/. {total_soles:,.2f}",
                f"${total_dolares:,.2f}",
                f"S/. {total_recibido:,.2f}",
                "",
                "",
                "Depósitos Izipay POS"
            ])

            # Crear DataFrame para la tabla
            df_detalle = pd.DataFrame(tabla_rows, columns=tabla_headers)

            # Mostrar tabla con formato mejorado
            st.dataframe(
                df_detalle,
                width='stretch',
                hide_index=True
            )

            # Agregar información adicional debajo de la tabla
            st.markdown("#### 💡 Información Adicional")

            # Crear columnas para métricas adicionales
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.metric(
                    "💱 Tasa de Cambio Promedio",
                    "S/ 3.55 por USD",
                    help="Tasa de cambio utilizada para conversiones"
                )

            with col_b:
                # Calcular porcentaje de ventas en dólares
                porc_dolares = (total_dolares / (total_soles + total_dolares * 3.55)) * 100 if (total_soles + total_dolares * 3.55) > 0 else 0
                st.metric(
                    "🇺🇸 Ventas en USD",
                    f"{porc_dolares:.1f}%",
                    help="Porcentaje de ventas realizadas en dólares"
                )

            with col_c:
                # Calcular eficiencia de cobro (recibido vs vendido)
                eficiencia = (total_recibido / (total_soles + total_dolares * 3.55)) * 100 if (total_soles + total_dolares * 3.55) > 0 else 0
                st.metric(
                    "✅ Eficiencia de Cobro",
                    f"{eficiencia:.1f}%",
                    help="Porcentaje efectivamente recibido vs total vendido"
                )

        else:
            st.info("ℹ️ No hay datos de ingresos para mostrar el detalle por tipo de pago")

        st.markdown("---")

        # Nueva sección: Análisis de Ingresos
        st.markdown("---")
        st.subheader("📈 Análisis de Ingresos")
        
        # Filtrar solo ingresos positivos para el análisis
        # Incluir también ajustes negativos de Sirvoy (devoluciones/correcciones no canceladas)
        ingresos_data = filtered_data[
            ((filtered_data['amount_gross'] > 0) & (filtered_data['income_type'] != 'Gasto')) |
            ((filtered_data['income_type'] == 'Ajuste') & (filtered_data['source'] == 'Sirvoy'))
        ].copy()
        
        if not ingresos_data.empty:
            # Resumen General
            ingresos_totales = ingresos_data['amount_gross'].sum()
            total_transacciones = len(ingresos_data)
            monto_promedio = ingresos_totales / total_transacciones if total_transacciones > 0 else 0
            
            # Obtener rango de fechas
            fecha_min = ingresos_data['date'].min()
            fecha_max = ingresos_data['date'].max()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Ingresos Totales", f"S/ {ingresos_totales:,.2f}")
            with col2:
                st.metric("Total Transacciones", f"{total_transacciones:,}")
            with col3:
                st.metric("Monto Promedio por Transacción", f"S/ {monto_promedio:,.2f}")
            
            if fecha_min and fecha_max:
                st.caption(f"📅 Período analizado: {fecha_min.strftime('%d/%m/%Y')} al {fecha_max.strftime('%d/%m/%Y')}")
            
            st.markdown("---")
            
            # Distribución de Ingresos por Método de Pago
            st.subheader("💳 Distribución de Ingresos por Método de Pago")
            
            # Obtener desglose por tipo de ingreso
            desglose_tipos = {}
            tipos_principales = ['Tarjeta', 'Transferencia', 'Efectivo', 'Otros']
            
            # Mapeo de nombres para mostrar
            nombres_tipos = {
                'Tarjeta': 'Pago con tarjeta',
                'Transferencia': 'Transferencia bancaria',
                'Efectivo': 'Efectivo',
                'Otros': 'Otros'
            }

            for tipo in tipos_principales:
                tipo_data = ingresos_data[ingresos_data['income_type'] == tipo]
                if not tipo_data.empty:
                    monto_total = tipo_data['amount_gross'].sum()
                    cantidad_transacciones = len(tipo_data)
                    promedio_transaccion = monto_total / cantidad_transacciones if cantidad_transacciones > 0 else 0
                    comisiones_tipo = tipo_data['commission_total'].sum()
                    porcentaje_del_total = (monto_total / ingresos_totales) * 100 if ingresos_totales > 0 else 0

                    desglose_tipos[tipo] = {
                        'monto_total': monto_total,
                        'cantidad_transacciones': cantidad_transacciones,
                        'promedio_transaccion': promedio_transaccion,
                        'comisiones': comisiones_tipo,
                        'porcentaje': porcentaje_del_total
                    }

            # Crear DataFrame para visualización
            df_desglose = pd.DataFrame([
                {
                    'Método de Pago': nombres_tipos.get(tipo, tipo),
                    'Monto Total (S/)': datos['monto_total'],
                    'Transacciones': datos['cantidad_transacciones'],
                    'Promedio (S/)': datos['promedio_transaccion'],
                    'Porcentaje': datos['porcentaje'],
                    'Comisiones (S/)': datos['comisiones']
                }
                for tipo, datos in desglose_tipos.items()
            ])
            
            if not df_desglose.empty:
                # Ordenar por monto total descendente
                df_desglose = df_desglose.sort_values('Monto Total (S/)', ascending=False)
                
                # Mostrar tabla
                st.dataframe(
                    df_desglose.style.format({
                        'Monto Total (S/)': '{:,.2f}',
                        'Promedio (S/)': '{:,.2f}',
                        'Porcentaje': '{:.2f}%',
                        'Comisiones (S/)': '{:,.2f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Gráfico de distribución
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de pastel
                    fig_pie = px.pie(
                        df_desglose,
                        values='Monto Total (S/)',
                        names='Método de Pago',
                        title="Distribución de Ingresos por Método de Pago",
                        hole=0.4
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Gráfico de barras
                    fig_bar = px.bar(
                        df_desglose,
                        x='Método de Pago',
                        y='Monto Total (S/)',
                        title="Ingresos por Método de Pago",
                        labels={'Monto Total (S/)': 'Monto (S/)', 'Método de Pago': 'Método'},
                        text='Monto Total (S/)'
                    )
                    fig_bar.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(yaxis_title='Monto (S/)')
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("---")
            
            # Tendencia Diaria de Ingresos
            st.subheader("📅 Tendencia Diaria de Ingresos")
            
            # Agrupar por fecha
            ingresos_diarios = ingresos_data.groupby(ingresos_data['date'].dt.date).agg({
                'amount_gross': 'sum',
                'transaction_id': 'count'
            }).reset_index()
            ingresos_diarios.columns = ['Fecha', 'Ingresos', 'Transacciones']
            ingresos_diarios = ingresos_diarios.sort_values('Fecha')
            
            if not ingresos_diarios.empty:
                # Encontrar pico y valle
                pico_idx = ingresos_diarios['Ingresos'].idxmax()
                valle_idx = ingresos_diarios['Ingresos'].idxmin()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    fecha_pico = pd.to_datetime(ingresos_diarios.loc[pico_idx, 'Fecha'])
                    st.metric(
                        "Día con Mayor Ingreso",
                        f"S/ {ingresos_diarios.loc[pico_idx, 'Ingresos']:,.2f}",
                        delta=fecha_pico.strftime('%d/%m/%Y')
                    )
                with col2:
                    fecha_valle = pd.to_datetime(ingresos_diarios.loc[valle_idx, 'Fecha'])
                    st.metric(
                        "Día con Menor Ingreso",
                        f"S/ {ingresos_diarios.loc[valle_idx, 'Ingresos']:,.2f}",
                        delta=fecha_valle.strftime('%d/%m/%Y')
                    )
                with col3:
                    promedio_diario = ingresos_diarios['Ingresos'].mean()
                    st.metric("Promedio Diario", f"S/ {promedio_diario:,.2f}")
                
                # Gráfico de línea
                fig_tendencia = px.line(
                    ingresos_diarios,
                    x='Fecha',
                    y='Ingresos',
                    title=f"Tendencia Diaria de Ingresos ({ingresos_diarios['Fecha'].min()} al {ingresos_diarios['Fecha'].max()})",
                    labels={'Ingresos': 'Ingresos (S/)', 'Fecha': 'Fecha'},
                    markers=True
                )
                fig_tendencia.update_traces(
                    line=dict(width=3),
                    marker=dict(size=8)
                )
                fig_tendencia.update_layout(
                    xaxis_title='Fecha',
                    yaxis_title='Ingresos (S/)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_tendencia, use_container_width=True)
                
                # Tabla de ingresos diarios
                with st.expander("📋 Ver Detalle Diario", expanded=False):
                    ingresos_diarios_display = ingresos_diarios.copy()
                    ingresos_diarios_display['Fecha'] = ingresos_diarios_display['Fecha'].astype(str)
                    ingresos_diarios_display = ingresos_diarios_display.rename(columns={
                        'Fecha': 'Fecha',
                        'Ingresos': 'Ingresos (S/)',
                        'Transacciones': 'Transacciones'
                    })
                    st.dataframe(
                        ingresos_diarios_display.style.format({
                            'Ingresos (S/)': '{:,.2f}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
            
            st.markdown("---")
            
            # Desglose Detallado por Medio de Pago (sección original)
            st.subheader("💳 Desglose Detallado por Medio de Pago")

            # Crear columnas para las métricas de cada tipo de pago
            col1, col2, col3, col4 = st.columns(4)

            # Mostrar métricas para cada tipo
            with col1:
                if 'Tarjeta' in desglose_tipos:
                    data = desglose_tipos['Tarjeta']
                    st.metric(
                        "💳 Tarjeta",
                        f"S/ {data['monto_total']:,.2f}",
                        delta=f"{data['cantidad_transacciones']} txns | {data['porcentaje']:.1f}%"
                    )
                    st.caption(f"Promedio: S/ {data['promedio_transaccion']:.2f}")
                    st.caption(f"Comisiones: S/ {data['comisiones']:.2f}")
                else:
                    st.metric("💳 Tarjeta", "Sin datos")

            with col2:
                if 'Transferencia' in desglose_tipos:
                    data = desglose_tipos['Transferencia']
                    st.metric(
                        "🏦 Transferencia",
                        f"S/ {data['monto_total']:,.2f}",
                        delta=f"{data['cantidad_transacciones']} txns | {data['porcentaje']:.1f}%"
                    )
                    st.caption(f"Promedio: S/ {data['promedio_transaccion']:.2f}")
                    st.caption(f"Comisiones: S/ {data['comisiones']:.2f}")
                else:
                    st.metric("🏦 Transferencia", "Sin datos")

            with col3:
                if 'Efectivo' in desglose_tipos:
                    data = desglose_tipos['Efectivo']
                    st.metric(
                        "💵 Efectivo",
                        f"S/ {data['monto_total']:,.2f}",
                        delta=f"{data['cantidad_transacciones']} txns | {data['porcentaje']:.1f}%"
                    )
                    st.caption(f"Promedio: S/ {data['promedio_transaccion']:.2f}")
                    st.caption(f"Comisiones: S/ {data['comisiones']:.2f}")
                else:
                    st.metric("💵 Efectivo", "Sin datos")

            with col4:
                if 'Otros' in desglose_tipos:
                    data = desglose_tipos['Otros']
                    st.metric(
                        "📋 Otros",
                        f"S/ {data['monto_total']:,.2f}",
                        delta=f"{data['cantidad_transacciones']} txns | {data['porcentaje']:.1f}%"
                    )
                    st.caption(f"Promedio: S/ {data['promedio_transaccion']:.2f}")
                    st.caption(f"Comisiones: S/ {data['comisiones']:.2f}")
                else:
                    st.metric("📋 Otros", "Sin datos")

            # Gráfico de barras para comparar tipos de pago
            if desglose_tipos:
                st.markdown("#### 📊 Comparación Visual")

                tipos_grafico = []
                montos_grafico = []
                colores_grafico = []

                colores_map = {
                    'Tarjeta': '#FF6B6B',
                    'Transferencia': '#4ECDC4',
                    'Efectivo': '#45B7D1',
                    'Otros': '#FFA07A'
                }

                for tipo in tipos_principales:
                    if tipo in desglose_tipos:
                        tipos_grafico.append(tipo)
                        montos_grafico.append(desglose_tipos[tipo]['monto_total'])
                        colores_grafico.append(colores_map.get(tipo, '#CCCCCC'))

                fig_tipos = go.Figure(data=[
                    go.Bar(
                        x=tipos_grafico,
                        y=montos_grafico,
                        marker_color=colores_grafico,
                        text=[f"S/ {monto:,.0f}" for monto in montos_grafico],
                        textposition='auto',
                    )
                ])

                fig_tipos.update_layout(
                    title="Montos por Tipo de Pago",
                    xaxis_title="Tipo de Pago",
                    yaxis_title="Monto Total (S/)",
                    showlegend=False
                )

                st.plotly_chart(fig_tipos, width='stretch')

                # Tabla detallada de desglose
                st.markdown("#### 📋 Tabla Detallada")

                tabla_data = []
                for tipo in tipos_principales:
                    if tipo in desglose_tipos:
                        data = desglose_tipos[tipo]
                        tabla_data.append({
                            'Tipo de Pago': tipo,
                            'Monto Total': f"S/ {data['monto_total']:,.2f}",
                            'Transacciones': data['cantidad_transacciones'],
                            'Promedio': f"S/ {data['promedio_transaccion']:,.2f}",
                            'Comisiones': f"S/ {data['comisiones']:,.2f}",
                            '% del Total': f"{data['porcentaje']:.1f}%"
                        })

                if tabla_data:
                    df_tabla = pd.DataFrame(tabla_data)
                    st.dataframe(df_tabla, width='stretch')
            else:
                st.info("ℹ️ No hay datos de ingresos para mostrar el desglose por tipo de pago")
        else:
            st.info("ℹ️ No hay datos de ingresos para mostrar el desglose por tipo de pago")

        st.markdown("---")

        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Ingresos por Procesador")
            # Solo mostrar ingresos positivos en el gráfico de pie
            ingresos_data = filtered_data[filtered_data['amount_gross'] > 0]
            if not ingresos_data.empty:
                processor_data = ingresos_data.groupby('processor')['amount_gross'].agg(['count', 'sum']).reset_index()
                
                fig_processor = px.pie(
                    processor_data, 
                    values='sum', 
                    names='processor',
                    title="Distribución de Ingresos por Procesador"
                )
                st.plotly_chart(fig_processor, width='stretch')
            else:
                st.info("No hay datos de ingresos para mostrar")
        
        with col2:
            st.subheader("💳 Métodos de Pago")
            # Separar ingresos y gastos para mejor visualización
            method_data = filtered_data.groupby('payment_method').agg({
                'amount_gross': 'sum',
                'transaction_id': 'count'
            }).reset_index()
            method_data.columns = ['payment_method', 'amount', 'count']
            
            # Crear colores diferentes para ingresos y gastos
            colors = ['green' if x > 0 else 'red' for x in method_data['amount']]
            
            fig_method = px.bar(
                method_data, 
                x='payment_method', 
                y='amount',
                title="Ingresos/Gastos por Método de Pago",
                labels={'payment_method': 'Método de Pago', 'amount': 'Monto (S/)'},
                color=colors,
                color_discrete_map={'green': '#2E8B57', 'red': '#DC143C'}
            )
            st.plotly_chart(fig_method, width='stretch')
        
        # Gráfico de comisiones
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Desglose de Comisiones")
            if not filtered_data.empty:
                comisiones_data = {
                    'Tipo': ['Procesadores', 'Chamba Digital (5%)', 'Total'],
                    'Monto': [
                        filtered_data['commission_processor'].sum(),
                        filtered_data['commission_chamba'].sum(),
                        filtered_data['commission_total'].sum()
                    ]
                }
                
                fig_comisiones = px.bar(
                    comisiones_data,
                    x='Tipo',
                    y='Monto',
                    title="Desglose de Comisiones",
                    labels={'Monto': 'Monto (S/)'},
                    color='Tipo',
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
                )
                st.plotly_chart(fig_comisiones, width='stretch')
        
        with col2:
            st.subheader("📈 Desglose de Gastos")
            if not filtered_data.empty or gastos_adicionales_total > 0:
                gastos_facebook = abs(filtered_data[(filtered_data['processor'] == 'Facebook') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
                
                # Calcular gastos de Sirvoy (costos de plataforma) - SOLO los que están marcados como 'Gasto'
                gastos_sirvoy = abs(filtered_data[(filtered_data['source'] == 'Sirvoy') & (filtered_data['income_type'] == 'Gasto') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
                
                # Mostrar métricas numéricas de gastos
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    if gastos_facebook > 0:
                        st.metric("Facebook Ads", f"S/ {gastos_facebook:,.2f}")
                    else:
                        st.metric("Facebook Ads", "S/ 0.00")
                
                with col_g2:
                    if gastos_sirvoy > 0:
                        st.metric("Gastos Sirvoy", f"S/ {gastos_sirvoy:,.2f}")
                    else:
                        st.metric("Gastos Sirvoy", "S/ 0.00")
                
                with col_g3:
                    if gastos_adicionales_total > 0:
                        st.metric("Gastos Adicionales", f"S/ {gastos_adicionales_total:,.2f}")
                    else:
                        st.metric("Gastos Adicionales", "S/ 0.00")
                
                gastos_data = {
                    'Tipo': [],
                    'Monto': [],
                    'Color': []
                }
                
                if gastos_facebook > 0:
                    gastos_data['Tipo'].append('Gasto Real Facebook')
                    gastos_data['Monto'].append(gastos_facebook)
                    gastos_data['Color'].append('Publicidad')

                if gastos_sirvoy > 0:
                    gastos_data['Tipo'].append('Gastos Sirvoy')
                    gastos_data['Monto'].append(gastos_sirvoy)
                    gastos_data['Color'].append('Plataforma')

                if gastos_adicionales_total > 0:
                    gastos_data['Tipo'].append('Gastos Adicionales')
                    gastos_data['Monto'].append(gastos_adicionales_total)
                    gastos_data['Color'].append('Operativos')
                
                if gastos_data['Tipo']:
                    fig_gastos = px.pie(
                        gastos_data,
                        values='Monto',
                        names='Tipo',
                        title="Distribución de Gastos",
                        color='Color',
                        color_discrete_map={'Publicidad': '#FF6B6B', 'Software': '#88B04B', 'Operativos': '#4ECDC4'}
                    )
                    st.plotly_chart(fig_gastos, width='stretch')
                else:
                    st.info("No hay gastos registrados para mostrar")
        
        # Gráfico de tendencia temporal
        if not filtered_data['date'].isna().all():
            st.subheader("📈 Tendencia Temporal")
            
            # Agrupar por día
            daily_data = filtered_data.groupby(filtered_data['date'].dt.date).agg({
                'amount': 'sum',
                'transaction_id': 'count'
            }).reset_index()
            daily_data.columns = ['date', 'total_amount', 'transaction_count']
            
            fig_trend = go.Figure()
            
            fig_trend.add_trace(go.Scatter(
                x=daily_data['date'],
                y=daily_data['total_amount'],
                mode='lines+markers',
                name='Monto Diario (S/)',
                yaxis='y'
            ))
            
            fig_trend.add_trace(go.Scatter(
                x=daily_data['date'],
                y=daily_data['transaction_count'],
                mode='lines+markers',
                name='Número de Transacciones',
                yaxis='y2'
            ))
            
            fig_trend.update_layout(
                title="Evolución Diaria de Transacciones",
                xaxis_title="Fecha",
                yaxis=dict(title="Monto (S/)", side="left"),
                yaxis2=dict(title="Número de Transacciones", side="right", overlaying="y"),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_trend, width='stretch')
        
        # Sección de gastos adicionales
        if st.session_state.gastos_adicionales:
            st.markdown("---")
            st.subheader("💸 Detalle de Gastos Adicionales")
            
            # Crear DataFrame con gastos adicionales
            gastos_df = pd.DataFrame(st.session_state.gastos_adicionales)
            gastos_df['Fecha'] = pd.to_datetime(gastos_df['fecha']).dt.strftime('%d/%m/%Y')
            gastos_df['Monto'] = gastos_df['monto'].apply(lambda x: f"S/ {x:,.2f}")
            
            # Mostrar tabla
            display_gastos = gastos_df[['Fecha', 'nombre', 'Monto']].copy()
            display_gastos.columns = ['Fecha', 'Concepto', 'Monto']
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(display_gastos, width='stretch')
            
            with col2:
                # Resumen de gastos adicionales
                total_gastos_adicionales_display = sum([g['monto'] for g in st.session_state.gastos_adicionales])
                promedio_gasto = total_gastos_adicionales_display / len(st.session_state.gastos_adicionales)
                
                st.metric("Total Gastos Adicionales", f"S/ {total_gastos_adicionales_display:,.2f}")
                st.metric("Promedio por Gasto", f"S/ {promedio_gasto:,.2f}")
                st.metric("Número de Conceptos", len(st.session_state.gastos_adicionales))
                
                # Botón para limpiar todos los gastos
                if st.button("🗑️ Limpiar Todos los Gastos", type="secondary"):
                    st.session_state.gastos_adicionales = []
                    st.rerun()
        
        # Tabla de datos
        st.subheader("📋 Detalle de Transacciones")
        
        # Preparar datos para mostrar
        display_data = filtered_data[[
            'date', 'transaction_id', 'amount_gross', 'amount_net', 'payment_method',
            'customer_name', 'processor', 'commission_chamba', 'commission_processor', 'category'
        ]].copy()

        # Convertir tipos de datos para evitar errores de Arrow
        # Solo aplicar strftime a valores datetime válidos
        display_data['date'] = display_data['date'].apply(
            lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
        )
        display_data['transaction_id'] = display_data['transaction_id'].astype(str)
        display_data['amount_gross'] = display_data['amount_gross'].apply(lambda x: f"S/ {float(x):,.2f}")
        display_data['amount_net'] = display_data['amount_net'].apply(lambda x: f"S/ {float(x):,.2f}")
        display_data['commission_chamba'] = display_data['commission_chamba'].apply(lambda x: f"S/ {float(x):,.2f}")
        display_data['commission_processor'] = display_data['commission_processor'].apply(lambda x: f"S/ {float(x):,.2f}")
        
        display_data.columns = [
            'Fecha', 'ID Transacción', 'Monto Bruto', 'Monto Neto', 'Método de Pago',
            'Cliente', 'Procesador', 'Comisión Chamba', 'Comisión Procesador', 'Categoría'
        ]
        
        st.dataframe(display_data, width='stretch')
        
        # Botón de descarga
        st.subheader("💾 Exportar Datos")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_data = filtered_data.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_data,
                file_name=f"transacciones_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Crear Excel en memoria
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                filtered_data.to_excel(writer, sheet_name='Transacciones', index=False)
                
                # Agregar hoja de resumen
                ingresos_excel = filtered_data[filtered_data['amount_gross'] > 0]['amount_gross'].sum()
                gastos_facebook_excel = abs(filtered_data[(filtered_data['source'] == 'Facebook Ads') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())

                # Calcular gastos de Sirvoy (costos de plataforma)
                gastos_sirvoy_excel = abs(filtered_data[(filtered_data['source'] == 'Sirvoy') & (filtered_data['income_type'] == 'Gasto') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())

                gastos_adicionales_excel = sum([g['monto'] for g in st.session_state.gastos_adicionales])
                gastos_totales_excel = gastos_facebook_excel + gastos_sirvoy_excel + gastos_adicionales_excel
                
                summary_data = pd.DataFrame({
                    'Métrica': [
                        'Total Transacciones', 
                        'Ingresos Brutos', 
                        'Gastos Facebook', 
                        'Gastos Sirvoy',
                        'Gastos Adicionales',
                        'Gastos Totales',
                        'Comisiones Totales', 
                        'Ingresos Netos Finales'
                    ],
                    'Valor': [
                        len(filtered_data),
                        f"S/ {ingresos_excel:,.2f}",
                        f"S/ {gastos_facebook_excel:,.2f}",
                        f"S/ {gastos_sirvoy_excel:,.2f}",
                        f"S/ {gastos_adicionales_excel:,.2f}",
                        f"S/ {gastos_totales_excel:,.2f}",
                        f"S/ {filtered_data['commission_total'].sum():,.2f}",
                        f"S/ {ingresos_excel - gastos_totales_excel - filtered_data['commission_total'].sum():,.2f}"
                    ]
                })
                summary_data.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Visualización del Resumen Financiero movida al inicio del dashboard
                pass

                
                # Agregar hoja de gastos adicionales si existen
                if st.session_state.gastos_adicionales:
                    gastos_adicionales_df = pd.DataFrame(st.session_state.gastos_adicionales)
                    gastos_adicionales_df['fecha'] = pd.to_datetime(gastos_adicionales_df['fecha'])
                    gastos_adicionales_df = gastos_adicionales_df[['fecha', 'nombre', 'monto']]
                    gastos_adicionales_df.columns = ['Fecha', 'Concepto', 'Monto']
                    gastos_adicionales_df.to_excel(writer, sheet_name='Gastos Adicionales', index=False)
            
            st.download_button(
                label="📊 Descargar Excel",
                data=excel_buffer.getvalue(),
                file_name=f"reporte_transacciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col3:
            # Generar PDF
            if st.button("📄 Generar PDF", use_container_width=True):
                try:
                    with st.spinner("Generando reporte PDF..."):
                        # Obtener estadísticas para el reporte
                        # Usar los datos filtrados para el reporte
                        ingresos_brutos = filtered_data[filtered_data['amount_gross'] > 0]['amount_gross'].sum()
                        
                        # Gastos Facebook
                        fb_data = filtered_data[filtered_data['processor'] == 'Facebook']
                        gastos_fb = abs(fb_data['amount_gross'].sum())
                        
                        # Comisiones
                        comision_chamba = filtered_data['commission_chamba'].sum()
                        comision_proc = filtered_data['commission_processor'].sum()
                        
                        # Neto
                        neto_final = ingresos_brutos - gastos_fb - comision_chamba - comision_proc
                        
                        # ROI
                        roi = 0
                        if gastos_fb > 0:
                            roi = ((ingresos_brutos - gastos_fb - comision_chamba - comision_proc) / gastos_fb) * 100
                        
                        # Consolidar stats
                        report_stats = {
                            'total_gross_income': ingresos_brutos,
                            'total_facebook_expenses': gastos_fb,
                            'total_net_income': neto_final,
                            'total_chamba_commission': comision_chamba,
                            'total_processor_commission': comision_proc,
                            'roi_facebook': roi,
                            'facebook_reported_raw': abs(fb_data['amount_reported'].sum()) if 'amount_reported' in fb_data.columns else 0,
                            'facebook_tax_adjustment': fb_data['tax_adjustment'].sum() if 'tax_adjustment' in fb_data.columns else 0
                        }

                        # Generar el PDF
                        pdf_gen = PDFGenerator()
                        pdf_filename = f"reporte_financiero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        pdf_path = pdf_gen.generate_report(filtered_data, report_stats, pdf_filename)
                        
                        # Leer el PDF generado
                        with open(pdf_path, 'rb') as pdf_file:
                            pdf_bytes = pdf_file.read()
                        
                        # Descargar el PDF
                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_bytes,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            key="download_pdf"
                        )
                        
                        # Eliminar archivo temporal
                        try:
                            os.remove(pdf_path)
                        except:
                            pass
                            
                        st.success("✅ PDF generado exitosamente")
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    import traceback
                    st.error(traceback.format_exc())
    
    else:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")

if __name__ == "__main__":
    main()
