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
from data_processor import PaymentDataProcessor

# Configuración de la página
st.set_page_config(
    page_title="Peña Linda Bungalows - Análisis de Pagos",
    page_icon="🏨",
    layout="wide"
)

# Inicializar el procesador
@st.cache_resource
def get_processor():
    return PaymentDataProcessor()

def main():
    st.title("🏨 Peña Linda Bungalows - Sistema de Análisis de Pagos")
    st.markdown("---")
    
    processor = get_processor()
    
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
        "Archivo Transferencias Directas (.csv)", 
        type=['csv'],
        help="Archivo de transferencias bancarias directas"
    )
    
    facebook_file = st.sidebar.file_uploader(
        "Archivo Facebook Ads (.csv)", 
        type=['csv'],
        help="Archivo de facturación de Facebook Ads"
    )
    
    gastos_sirvoy_excel = 0

    # Cargar datos de Sirvoy
    sirvoy_file = st.sidebar.file_uploader(
        "Archivo Sirvoy (.csv)", 
        type=['csv'],
        help="Archivo de cobros de Sirvoy"
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
    
    # Procesar archivos cargados
    data_loaded = False
    
    if izipay_file is not None:
        # Guardar temporalmente y cargar
        with open("temp_izipay.csv", "wb") as f:
            f.write(izipay_file.getbuffer())
        processor.load_izipay_data("temp_izipay.csv")
        st.sidebar.success(f"✅ Izipay: {len(processor.izipay_data)} registros")
        data_loaded = True
    
    if culqi_file is not None:
        with open("temp_culqi.csv", "wb") as f:
            f.write(culqi_file.getbuffer())
        processor.load_culqi_data("temp_culqi.csv")
        st.sidebar.success(f"✅ Culqi: {len(processor.culqi_data)} registros")
        data_loaded = True
    
    if secured_file is not None:
        with open("temp_secured.csv", "wb") as f:
            f.write(secured_file.getbuffer())
        processor.load_secured_data("temp_secured.csv")
        st.sidebar.success(f"✅ Transferencias: {len(processor.secured_data)} registros")
        data_loaded = True
    
    if facebook_file is not None:
        with open("temp_facebook.csv", "wb") as f:
            f.write(facebook_file.getbuffer())
        processor.load_facebook_data("temp_facebook.csv")
        st.sidebar.success(f"✅ Facebook Ads: {len(processor.facebook_data)} registros")
        data_loaded = True
    
    if sirvoy_file is not None:
        with open("temp_sirvoy.csv", "wb") as f:
            f.write(sirvoy_file.getbuffer())
        processor.load_sirvoy_data("temp_sirvoy.csv")
        st.sidebar.success(f"✅ Sirvoy: {len(processor.sirvoy_data)} registros")
        data_loaded = True
    
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
        """)
        return
    
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
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Transacciones",
                f"{len(filtered_data):,}",
                delta=f"{len(filtered_data) - len(unified_data):,}" if len(filtered_data) != len(unified_data) else None
            )
        
        with col2:
            # Separar ingresos y gastos
            ingresos = filtered_data[filtered_data['amount_gross'] > 0]['amount_gross'].sum()
            
            # Calcular gastos de Facebook específicamente
            gastos_facebook = abs(filtered_data[(filtered_data['processor'] == 'Facebook') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
            
            # Calcular gasto real de Sirvoy
            sirvoy_data = filtered_data[filtered_data['processor'] == 'Sirvoy']
            monto_reportado_sirvoy = sirvoy_data['amount_reported'].sum() if 'amount_reported' in sirvoy_data.columns and len(sirvoy_data) > 0 else 0
            ajuste_porcentaje = 0.143
            ajuste_sirvoy = monto_reportado_sirvoy * ajuste_porcentaje
            gasto_real_sirvoy = monto_reportado_sirvoy + ajuste_sirvoy
            gastos_sirvoy = abs(gasto_real_sirvoy)  # Usar magnitud positiva para totales
            
            # Agregar gastos adicionales
            gastos_adicionales_total = sum([g['monto'] for g in st.session_state.gastos_adicionales])
            
            # Total gastos
            gastos_totales = gastos_facebook + gastos_sirvoy + gastos_adicionales_total
            
            st.metric(
                "Ingresos Brutos",
                f"S/ {ingresos:,.2f}",
                delta=f"Gastos totales: -S/ {gastos_totales:,.2f}"
            )
        
        with col3:
            # Comisiones totales (procesador + Chamba Digital)
            commission_processor = filtered_data['commission_processor'].sum()
            commission_chamba = filtered_data['commission_chamba'].sum()
            total_commission = commission_processor + commission_chamba
            
            st.metric(
                "Comisiones Totales",
                f"S/ {total_commission:,.2f}",
                delta=f"Chamba: S/ {commission_chamba:,.2f}"
            )
        
        with col4:
            # Ingresos netos después de comisiones y gastos
            ingresos_netos_base = filtered_data[filtered_data['amount_gross'] > 0]['amount_net'].sum()
            ingresos_netos_final = ingresos_netos_base - gastos_totales
            
            st.metric(
                "Ingresos Netos Finales",
                f"S/ {ingresos_netos_final:,.2f}",
                delta=f"Margen: {(ingresos_netos_final/ingresos*100) if ingresos > 0 else 0:.1f}%"
            )
        
        # Segunda fila de métricas
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            # Promedio por transacción (solo ingresos)
            ingresos_data = filtered_data[filtered_data['amount_gross'] > 0]
            avg_transaction = ingresos_data['amount_gross'].mean() if len(ingresos_data) > 0 else 0
            st.metric(
                "Ticket Promedio",
                f"S/ {avg_transaction:,.2f}"
            )
        
        with col6:
            # Comisión Chamba Digital (5%)
            st.metric(
                "Comisión Chamba (5%)",
                f"S/ {commission_chamba:,.2f}",
                delta=f"{(commission_chamba/ingresos*100) if ingresos > 0 else 0:.2f}% del bruto"
            )
        
        with col7:
            # Comisiones de procesadores
            st.metric(
                "Comisión Procesadores",
                f"S/ {commission_processor:,.2f}",
                delta=f"{(commission_processor/ingresos*100) if ingresos > 0 else 0:.2f}% del bruto"
            )
        
        with col8:
            # Gastos adicionales y ROI
            if gastos_adicionales_total > 0:
                st.metric(
                    "Gastos Adicionales",
                    f"S/ {gastos_adicionales_total:,.2f}",
                    delta=f"{len(st.session_state.gastos_adicionales)} conceptos"
                )
            else:
                # ROI de Facebook Ads (si hay datos y no hay gastos adicionales)
                facebook_data = filtered_data[filtered_data['processor'] == 'Facebook']
                if len(facebook_data) > 0:
                    gastos_facebook_solo = abs(facebook_data['amount_gross'].sum())
                    if gastos_facebook_solo > 0:
                        roi = ((ingresos - gastos_totales - total_commission) / gastos_totales) * 100 if gastos_totales > 0 else 0
                        st.metric(
                            "ROI Total",
                            f"{roi:.1f}%",
                            delta="Retorno sobre gastos totales"
                        )
                    else:
                        st.metric(
                            "Facebook Ads",
                            "Sin datos",
                            delta="No hay gastos publicitarios"
                        )
                else:
                    st.metric(
                        "Transacciones Directas",
                        f"{len(filtered_data[filtered_data['processor'] == 'Directo'])}"
                    )
        
        # Sección específica para Facebook Ads
        facebook_data = filtered_data[filtered_data['processor'] == 'Facebook']
        if len(facebook_data) > 0:
            st.markdown("---")
            st.subheader("📱 Análisis de Facebook Ads")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                monto_reportado = facebook_data['amount_reported'].sum() if 'amount_reported' in facebook_data.columns and len(facebook_data) > 0 else 0
                st.metric(
                    "Monto Reportado",
                    f"S/ {monto_reportado:,.2f}",
                    delta="Según reporte Facebook"
                )
            
            with col2:
                ajuste_impuestos = facebook_data['tax_adjustment'].sum() if 'tax_adjustment' in facebook_data.columns and len(facebook_data) > 0 else 0
                st.metric(
                    "Ajuste por Impuestos",
                    f"S/ {ajuste_impuestos:,.2f}",
                    delta="11.11% + redondeo"
                )
            
            with col3:
                gasto_real = abs(facebook_data['amount_gross'].sum()) if len(facebook_data) > 0 else 0
                st.metric(
                    "Gasto Real",
                    f"S/ {gasto_real:,.2f}",
                    delta="Cobrado en tarjeta"
                )
            
            with col4:
                num_transacciones = len(facebook_data)
                promedio_gasto = gasto_real / num_transacciones if num_transacciones > 0 else 0
                st.metric(
                    "Gasto Promedio",
                    f"S/ {promedio_gasto:,.2f}",
                    delta=f"{num_transacciones} transacciones"
                )
                

        
        # Sección específica para Sirvoy
        sirvoy_data = filtered_data[filtered_data['processor'] == 'Sirvoy']
        if len(sirvoy_data) > 0:
            st.markdown("---")
            st.subheader("🏨 Análisis de Sirvoy")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                monto_reportado_sirvoy = sirvoy_data['amount_reported'].sum() if 'amount_reported' in sirvoy_data.columns and len(sirvoy_data) > 0 else 0
                st.metric(
                    "Monto Reportado",
                    f"S/ {monto_reportado_sirvoy:,.2f}",
                    delta="Según reporte Sirvoy"
                )
            
            with col2:
                ajuste_porcentaje = 0.143  # Porcentaje promedio de ajuste calculado
                ajuste_sirvoy = monto_reportado_sirvoy * ajuste_porcentaje
                st.metric(
                    "Ajuste por Impuestos/Cargos",
                    f"S/ {ajuste_sirvoy:,.2f}",
                    delta=f"{ajuste_porcentaje:.1%} de ajuste"
                )
            
            with col3:
                gasto_real_sirvoy = monto_reportado_sirvoy + ajuste_sirvoy
                st.metric(
                    "Gasto Real Sirvoy",
                    f"S/ {gasto_real_sirvoy:,.2f}",
                    delta="Cobrado en tarjeta"
                )
            
            with col4:
                num_transacciones_sirvoy = len(sirvoy_data)
                promedio_gasto_sirvoy = gasto_real_sirvoy / num_transacciones_sirvoy if num_transacciones_sirvoy > 0 else 0
                st.metric(
                    "Gasto Promedio",
                    f"S/ {promedio_gasto_sirvoy:,.2f}",
                    delta=f"{num_transacciones_sirvoy} transacciones"
                )
                

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
            if not filtered_data.empty or gastos_adicionales_total > 0 or gastos_sirvoy_excel > 0:
                gastos_facebook = abs(filtered_data[filtered_data['amount_gross'] < 0]['amount_gross'].sum())
                
                # Obtener el gasto real de Sirvoy calculado en la sección de análisis
                sirvoy_data = filtered_data[filtered_data['processor'] == 'Sirvoy']
                monto_reportado_sirvoy = sirvoy_data['amount_reported'].sum() if 'amount_reported' in sirvoy_data.columns and len(sirvoy_data) > 0 else 0
                ajuste_porcentaje = 0.143
                ajuste_sirvoy = monto_reportado_sirvoy * ajuste_porcentaje
                gasto_real_sirvoy = monto_reportado_sirvoy + ajuste_sirvoy
                
                gastos_data = {
                    'Tipo': [],
                    'Monto': [],
                    'Color': []
                }
                
                if gastos_facebook > 0:
                    gastos_data['Tipo'].append('Gasto Real Facebook')
                    gastos_data['Monto'].append(gastos_facebook)
                    gastos_data['Color'].append('Publicidad')
                
                if gasto_real_sirvoy > 0:
                    gastos_data['Tipo'].append('Gasto Real Sirvoy')
                    gastos_data['Monto'].append(gasto_real_sirvoy)
                    gastos_data['Color'].append('Software')
                elif gastos_sirvoy_excel > 0:  # Usar gastos_sirvoy_excel como respaldo si no hay datos en sirvoy_data
                    gastos_data['Tipo'].append('Gastos Sirvoy')
                    gastos_data['Monto'].append(gastos_sirvoy_excel)
                    gastos_data['Color'].append('Software')

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
        display_data.loc[:, 'date'] = display_data['date'].dt.strftime('%d/%m/%Y %H:%M')
        display_data.loc[:, 'transaction_id'] = display_data['transaction_id'].astype(str)
        display_data.loc[:, 'amount_gross'] = display_data['amount_gross'].apply(lambda x: f"S/ {x:,.2f}")
        display_data.loc[:, 'amount_net'] = display_data['amount_net'].apply(lambda x: f"S/ {x:,.2f}")
        display_data.loc[:, 'commission_chamba'] = display_data['commission_chamba'].apply(lambda x: f"S/ {x:,.2f}")
        display_data.loc[:, 'commission_processor'] = display_data['commission_processor'].apply(lambda x: f"S/ {x:,.2f}")
        
        display_data.columns = [
            'Fecha', 'ID Transacción', 'Monto Bruto', 'Monto Neto', 'Método de Pago',
            'Cliente', 'Procesador', 'Comisión Chamba', 'Comisión Procesador', 'Categoría'
        ]
        
        st.dataframe(display_data, width='stretch')
        
        # Botón de descarga
        st.subheader("💾 Exportar Datos")
        
        col1, col2 = st.columns(2)
        
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
                gastos_sirvoy_excel = abs(filtered_data[(filtered_data['source'] == 'Sirvoy') & (filtered_data['amount_gross'] < 0)]['amount_gross'].sum())
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
                
                st.subheader("Resumen Financiero")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Ingresos Brutos", f"S/ {ingresos_excel:,.2f}")
                    st.metric("Gasto Real Facebook", f"S/ {gastos_facebook_excel:,.2f}")
                    st.metric("Gastos Sirvoy", f"S/ {gastos_sirvoy_excel:,.2f}")
                    st.metric("Gastos Totales", f"S/ {gastos_totales_excel:,.2f}")
                    st.metric("Comisiones Totales", f"S/ {filtered_data['commission_total'].sum():,.2f}")
                with col2:
                    st.metric("Ingresos Netos Finales", f"S/ {ingresos_excel - gastos_totales_excel - filtered_data['commission_total'].sum():,.2f}")
                    st.markdown(f"""
                    <style>
                    .tooltip {
                        position: relative;
                        display: inline-block;
                        cursor: help;
                    }

                    .tooltip .tooltiptext {
                        visibility: hidden;
                        width: 300px;
                        background-color: #555;
                        color: #fff;
                        text-align: center;
                        border-radius: 6px;
                        padding: 5px 0;
                        position: absolute;
                        z-index: 1;
                        bottom: 125%;
                        left: 50%;
                        margin-left: -150px;
                        opacity: 0;
                        transition: opacity 0.3s;
                    }

                    .tooltip .tooltiptext::after {
                        content: \"\";
                        position: absolute;
                        top: 100%;
                        left: 50%;
                        margin-left: -5px;
                        border-width: 5px;
                        border-style: solid;
                        border-color: #555 transparent transparent transparent;
                    }

                    .tooltip:hover .tooltiptext {
                        visibility: visible;
                        opacity: 1;
                    }
                    </style>
                    <div class="tooltip">
                        <span style="font-size: 1.2em; cursor: help;">❓</span>
                        <span class="tooltiptext">
                            <b>Ingresos Netos Finales</b> = Ingresos Brutos - Gastos Totales (Gasto Real Facebook + Sirvoy + Gastos Adicionales) - Comisiones Totales
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                
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
    
    else:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")

if __name__ == "__main__":
    main()