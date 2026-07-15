import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta, date
from app_v2.components import df_to_csv, df_to_excel, generate_weekly_pdf, export_buttons


def render(df, k, fi, ff, sv, sv_date_filtered):
    st.markdown("## 📤 Exportar Reportes")
    st.write("Genera y descarga informes consolidados listos para imprimir o compartir.")

    # ─── 3 columnas: PDF / HTML / CSV ───
    rep1, rep2, rep3 = st.columns(3)

    # --- PDF ---
    with rep1:
        st.markdown('<div class="shad-card"><h4>📄 Reporte PDF</h4>', unsafe_allow_html=True)
        st.write("Documento PDF formateado con el desglose del periodo filtrado.")
        if st.button("Construir PDF", use_container_width=True, key="exp_pdf"):
            with st.spinner("Generando PDF..."):
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import cm
                from reportlab.lib import colors as rc
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4,
                                        topMargin=1.5*cm, bottomMargin=1.5*cm,
                                        leftMargin=2*cm, rightMargin=2*cm)
                styles = getSampleStyleSheet()
                try:
                    styles.add(ParagraphStyle('T', parent=styles['Title'], fontSize=20, textColor=rc.HexColor('#1B365D'), spaceAfter=4))
                except Exception:
                    pass
                try:
                    styles.add(ParagraphStyle('S', parent=styles['Normal'], fontSize=11, textColor=rc.HexColor('#666'), spaceAfter=15, alignment=TA_CENTER))
                except Exception:
                    pass
                try:
                    styles.add(ParagraphStyle('C', fontSize=9, alignment=TA_CENTER))
                except Exception:
                    pass

                def at(d, cw=None):
                    t = Table(d, colWidths=cw, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('TEXTCOLOR', (0, 0), (-1, 0), rc.white),
                        ('BACKGROUND', (0, 0), (-1, 0), rc.HexColor('#1B365D')),
                        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                        ('GRID', (0, 0), (-1, -1), 0.3, rc.HexColor('#DDD')),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rc.white, rc.HexColor('#F5F8FC')]),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    elems.append(t)

                # === Cálculo desde MongoDB (deuda desde 03/03, coherente con HTML H1 y calculadora v3) ===
                from pymongo import MongoClient as _MC
                _cli = _MC(os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda"), serverSelectionTimeoutMS=5000)
                _db = _cli["pena_linda"]
                _DEBT = datetime(2026, 3, 3)
                _sv = list(_db["pagos"].find({"fuente": "Sirvoy", "fecha": {"$gte": _DEBT}}))
                _bruto = sum(d["monto"] for d in _sv if d["monto"] > 0)
                _revers = sum(d["monto"] for d in _sv if d["monto"] < 0)
                _neto = _bruto + _revers
                _comision = _neto * 0.05
                _costos = list(_db["pagos"].find({"fuente": {"$in": ["Costo FB Ads", "Costo Sirvoy", "Costo Asistente", "Costo Extra"]}, "fecha": {"$gte": _DEBT}}))
                _cfb = sum(d["monto"] for d in _costos if d["fuente"] == "Costo FB Ads")
                _csv = sum(d["monto"] for d in _costos if d["fuente"] == "Costo Sirvoy")
                _cas = sum(d["monto"] for d in _costos if d["fuente"] == "Costo Asistente")
                _cex = sum(d["monto"] for d in _costos if d["fuente"] == "Costo Extra")
                _total_costos = _cfb + _csv + _cas + _cex
                _saldo_base = sum(d["monto"] for d in _db["pagos"].find({"fuente": "Saldo Base"}))
                _abonos = sum(d["monto"] for d in _db["cobros"].find({"tipo": "abono"}))
                _adeudado = _saldo_base + _comision + _total_costos
                _pendiente = max(0.0, _adeudado - _abonos)
                _cli.close()

                elems = []
                elems.append(Spacer(1, 10))
                elems.append(Paragraph("Peña Linda Bungalows — Reporte de Conciliación", styles.get('T', styles['Title'])))
                elems.append(Paragraph("Deuda gestionada desde 03/03/2026 · Generado " + datetime.now().strftime('%d/%m/%Y'), styles.get('S', styles['Normal'])))
                elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
                elems.append(Spacer(1, 6))

                at([
                    ['Indicador', 'Valor'],
                    ['Ventas Sirvoy Bruto (desde 03/03)', f'S/ {_bruto:,.2f}'],
                    ['Reversiones (negativas)', f'S/ {_revers:,.2f}'],
                    ['Ventas Sirvoy Neto', f'S/ {_neto:,.2f}'],
                    ['Comisión 5% (sobre neto)', f'S/ {_comision:,.2f}'],
                    ['Costos Operativos', f'S/ {_total_costos:,.2f}'],
                    ['Saldo Base heredado (03/03)', f'S/ {_saldo_base:,.2f}'],
                    ['Abonos recibidos', f'S/ {_abonos:,.2f}'],
                    ['Deuda Pendiente', f'S/ {_pendiente:,.2f}'],
                ], [230, 130])

                elems.append(Spacer(1, 15))
                elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
                elems.append(Paragraph("Chamba Digital — Gestión e Ingeniería", styles.get('C', styles['Normal'])))
                doc.build(elems)

                st.download_button("⬇️ Descargar Reporte PDF", buffer.getvalue(),
                                   f"Reporte_{ff.strftime('%Y%m%d')}.pdf", "application/pdf",
                                   use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- HTML ---
    with rep2:
        st.markdown('<div class="shad-card"><h4>🌐 Reporte HTML H1 2026</h4>', unsafe_allow_html=True)
        st.write("Visualización interactiva y descarga del reporte ejecutivo dinámico H1 2026.")
        
        # Botón para reconstruir reporte H1 2026 con últimos datos al vuelo
        if st.button("🔄 Actualizar y Ver HTML H1", use_container_width=True, key="update_view_html"):
            with st.spinner("Compilando datos desde MongoDB..."):
                import subprocess
                # Ejecutar cálculo y actualización
                try:
                    subprocess.run(["python", "importar_costos_fb_nuevos.py"], capture_output=True)
                    subprocess.run(["python", "scratch/calculate_financials.py"], capture_output=True)
                    subprocess.run(["python", "scratch/robust_update_html.py"], capture_output=True)
                    st.success("✅ Informe Financiero H1 2026 actualizado con éxito.")
                except Exception as ex:
                    st.error(f"Error actualizando reporte: {ex}")
                    
        # Ofrecer descarga directa del archivo generado
        try:
            with open("Informe Financiero Peña Linda H1 2026.html", "r", encoding="utf-8") as fh:
                html_code = fh.read()
            st.download_button("⬇️ Descargar Reporte H1 2026 HTML", html_code.encode("utf-8"),
                               "Informe_Financiero_Pena_Linda_H1_2026.html", "text/html",
                               use_container_width=True)
            
            # Renderizar vista previa integrada con IFrame en Streamlit
            st.markdown("##### 👁️ Vista Previa Sincronizada")
            st.components.v1.html(html_code, height=450, scrolling=True)
        except Exception as e:
            st.warning("El informe estático H1 aún no ha sido generado o se encuentra inaccesible.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- CSV ---
    with rep3:
        st.markdown('<div class="shad-card"><h4>📊 Datos CSV</h4>', unsafe_allow_html=True)
        st.write("Descarga los datos crudos filtrados del período.")
        if not sv_date_filtered.empty:
            sv_exp = sv_date_filtered.copy()
            if "date_pe" in sv_exp.columns:
                sv_exp = sv_exp.sort_values("date_pe", ascending=False)
                sv_exp["Fecha"] = sv_exp["date_pe"].dt.strftime("%d/%m/%Y %H:%M")
            csv_data = df_to_csv(sv_exp)
            st.download_button("📥 Descargar CSV", csv_data,
                               f"Datos_Filtrados_{ff.strftime('%Y%m%d')}.csv", "text/csv",
                               use_container_width=True)
            st.download_button("📥 Descargar Excel", df_to_excel(sv_exp),
                               f"Datos_Filtrados_{ff.strftime('%Y%m%d')}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        else:
            st.button("Sin datos para exportar", disabled=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ─── RESUMEN DE DEUDA ACUMULADA ───
    st.markdown("---")
    st.markdown("### 🧮 Resumen de Deuda Acumulada")
    st.write("Descarga el resumen completo de la deuda acumulada desde el 03/03/2026.")

    if st.button("📄 Generar Resumen de Deuda PDF", use_container_width=True, key="exp_deuda_pdf"):
        with st.spinner("Generando Resumen de Deuda..."):
            from pymongo import MongoClient as MCli
            import os

            MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")
            cli_d = MCli(MONGO_URL, serverSelectionTimeoutMS=5000)
            db_d = cli_d["pena_linda"]

            DEBT_START = datetime(2026, 3, 3)

            sirvoy_docs = list(db_d["pagos"].find({
                "fuente": "Sirvoy",
                "fecha": {"$gte": DEBT_START}
            }))
            costos_docs = list(db_d["pagos"].find({
                "fuente": {"$in": ["Costo FB Ads", "Costo Sirvoy", "Costo Asistente", "Costo Extra"]},
                "fecha": {"$gte": DEBT_START}
            }))
            saldo_docs = list(db_d["pagos"].find({"fuente": "Saldo Base"}))
            cobros_docs = list(db_d["cobros"].find({"tipo": "abono"}))
            cli_d.close()

            montos_sv = [d["monto"] for d in sirvoy_docs]
            bruto = sum(m for m in montos_sv if m > 0)
            reversiones = sum(m for m in montos_sv if m < 0)
            neto = bruto + reversiones
            comision_d = neto * 0.05

            costo_fb = sum(d["monto"] for d in costos_docs if d["fuente"] == "Costo FB Ads")
            costo_sv = sum(d["monto"] for d in costos_docs if d["fuente"] == "Costo Sirvoy")
            costo_as = sum(d["monto"] for d in costos_docs if d["fuente"] == "Costo Asistente")
            costo_ex = sum(d["monto"] for d in costos_docs if d["fuente"] == "Costo Extra")
            total_costos_d = costo_fb + costo_sv + costo_as + costo_ex

            saldo_base_d = sum(d["monto"] for d in saldo_docs)
            abonos_total = sum(d["monto"] for d in cobros_docs)
            abonos_count = len(cobros_docs)

            adeudado = saldo_base_d + comision_d + total_costos_d
            pendiente = adeudado - abonos_total

            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.lib import colors as rc
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm,
                                    leftMargin=2*cm, rightMargin=2*cm)
            styles = getSampleStyleSheet()

            try:
                styles.add(ParagraphStyle('TitleD', parent=styles['Title'], fontSize=18,
                                         textColor=rc.HexColor('#1B365D'), spaceAfter=2, alignment=TA_CENTER))
            except:
                pass
            try:
                styles.add(ParagraphStyle('SubD', parent=styles['Normal'], fontSize=10,
                                         textColor=rc.HexColor('#666'), spaceAfter=12, alignment=TA_CENTER))
            except:
                pass
            try:
                styles.add(ParagraphStyle('SectionD', parent=styles['Normal'], fontSize=11,
                                         textColor=rc.HexColor('#1B365D'), spaceBefore=10, spaceAfter=4))
            except:
                pass

            def make_table(data, col_widths=None):
                t = Table(data, colWidths=col_widths, repeatRows=1)
                style_cmds = [
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (-1, 0), rc.white),
                    ('BACKGROUND', (0, 0), (-1, 0), rc.HexColor('#1B365D')),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.3, rc.HexColor('#DDD')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rc.white, rc.HexColor('#F5F8FC')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]
                t.setStyle(TableStyle(style_cmds))
                return t

            elems = []
            elems.append(Spacer(1, 10))
            elems.append(Paragraph("Resumen de Deuda Acumulada", styles.get('TitleD', styles['Title'])))
            elems.append(Paragraph("Peña Linda Bungalows — Chamba Digital SAC", styles.get('SubD', styles['Normal'])))
            elems.append(Paragraph(f"Periodo: 03/03/2026 al {datetime.now().strftime('%d/%m/%Y')}", styles.get('SubD', styles['Normal'])))
            elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
            elems.append(Spacer(1, 6))

            # 1. Ventas Sirvoy
            elems.append(Paragraph("1. Ventas Sirvoy", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Concepto', 'Monto (S/)'],
                ['Bruto (solo positivos)', f'{bruto:,.2f}'],
                ['Reversiones (negativos)', f'{-abs(reversiones):,.2f}'],
                ['Neto Real', f'{neto:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 8))

            # 2. Comisión
            elems.append(Paragraph("2. Comisión Chamba Digital (5%)", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Concepto', 'Monto (S/)'],
                [f'5% × {neto:,.2f} (neto Sirvoy)', f'{comision_d:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 8))

            # 3. Costos
            elems.append(Paragraph("3. Costos Operativos", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Concepto', 'Monto (S/)'],
                ['Facebook Ads', f'{costo_fb:,.2f}'],
                ['Plataforma Sirvoy', f'{costo_sv:,.2f}'],
                ['Asistente Virtual', f'{costo_as:,.2f}'],
                ['Costos Extra', f'{costo_ex:,.2f}'],
                ['Total Costos', f'{total_costos_d:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 8))

            # 4. Saldo Base
            elems.append(Paragraph("4. Saldo Heredado", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Concepto', 'Monto (S/)'],
                ['Saldo Base QuickBooks (03/03/2026)', f'{saldo_base_d:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 8))

            # 5. Total Adeudado
            elems.append(Paragraph("5. Total Adeudado", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Componente', 'Monto (S/)'],
                ['Saldo Base', f'{saldo_base_d:,.2f}'],
                ['Comisión 5%', f'{comision_d:,.2f}'],
                ['Costos Operativos', f'{total_costos_d:,.2f}'],
                ['Total Adeudado', f'{adeudado:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 8))

            # 6. Abonos
            elems.append(Paragraph("6. Abonos de Peña Linda", styles.get('SectionD', styles['Normal'])))
            elems.append(make_table([
                ['Concepto', 'Monto (S/)'],
                [f'Total Abonado ({abonos_count} registros)', f'{abonos_total:,.2f}'],
            ], [200, 160]))
            elems.append(Spacer(1, 12))

            # Resultado
            elems.append(HRFlowable(width="100%", thickness=1, color=rc.HexColor('#1B365D')))
            elems.append(Spacer(1, 6))
            color_pend = '#DC2626' if pendiente > 0 else '#16A34A'
            elems.append(make_table([
                ['Formula', 'Monto (S/)'],
                ['Adeudado (Saldo Base + Comisión + Costos)', f'{adeudado:,.2f}'],
                ['- Abonos de Peña Linda', f'{-abonos_total:,.2f}'],
                ['DEUDA PENDIENTE', f'{pendiente:,.2f}'],
            ], [260, 120]))

            elems.append(Spacer(1, 20))
            elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC')))
            elems.append(Paragraph(f"Chamba Digital — Gestión e Ingeniería | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                                   ParagraphStyle('FooterD', fontSize=8, textColor=rc.HexColor('#999'), alignment=TA_CENTER)))

            doc.build(elems)

            st.download_button(
                "⬇️ Descargar Resumen de Deuda PDF",
                data=buffer.getvalue(),
                file_name=f"Resumen_Deuda_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_resumen_deuda",
            )

    # ─── RESUMEN POR PESTAÑA ───
    st.markdown("---")
    st.markdown("### 📋 Exportar por Pestaña")
    st.write("Descarga solo los datos de una sección específica.")

    tab_names = ["Ventas", "Costos", "Conciliación"]
    tab_data = [
        k["sv_sirvoy"],
        k["costos_sin_base"],
        k.get("pendientes_link", pd.DataFrame()),
    ]

    for name, tab_df in zip(tab_names, tab_data):
        with st.expander(f"📥 {name}"):
            if tab_df is not None and not tab_df.empty:
                display_df = tab_df.copy()
                if "date_pe" in display_df.columns:
                    display_df = display_df.sort_values("date_pe", ascending=False)
                export_buttons(f"exp_tab_{name}", display_df, fi, ff, label=name)
            else:
                st.caption("Sin datos en este período.")

    # ─── REPORTE PARA CONTADOR ───
    st.markdown("---")
    st.markdown("### 📊 Reporte para Contador")
    st.write("Exportaciones detalladas para que el contador pueda validar la información.")

    from pymongo import MongoClient as MCli_cont
    import os
    MONGO_URL_C = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")

    r_c1, r_c2, r_c3, r_c4 = st.columns(4)

    # --- 1. Ventas Sirvoy desglosadas ---
    with r_c1:
        st.markdown('<div class="shad-card"><h4>📋 Ventas Sirvoy</h4>', unsafe_allow_html=True)
        st.caption("Todas las transacciones Sirvoy del período")
        if st.button("📥 CSV Ventas", use_container_width=True, key="exp_cont_sv"):
            cli_c = MCli_cont(MONGO_URL_C, serverSelectionTimeoutMS=5000)
            db_c = cli_c["pena_linda"]
            docs = list(db_c["pagos"].find({
                "fuente": "Sirvoy",
                "fecha": {"$gte": datetime.combine(fi, datetime.min.time()),
                          "$lte": datetime.combine(ff, datetime.max.time())}
            }))
            cli_c.close()

            rows = []
            for d in docs:
                rows.append({
                    "Payment ID": d.get("metadata", "{}").replace('{\"PaymentId\": \"', '').replace('\"}', '') if "metadata" in d else "",
                    "Fecha": d["fecha"].strftime("%d/%m/%Y %H:%M") if d.get("fecha") else "",
                    "Método": d.get("metodo", ""),
                    "Tipo": d.get("tipo_pago", ""),
                    "Monto": d.get("monto", 0),
                    "Reserva": d.get("reserva", ""),
                    "Comentario": d.get("comentario", ""),
                })
            exp_df = pd.DataFrame(rows)
            exp_df = exp_df.sort_values("Fecha", ascending=False)

            csv_bytes = exp_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv_bytes,
                               f"Ventas_Sirvoy_{fi.strftime('%Y%m%d')}_{ff.strftime('%Y%m%d')}.csv",
                               "text/csv", use_container_width=True, key="dl_cont_sv")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. Plataformas (Izipay, Culqi, Openpay) ---
    with r_c2:
        st.markdown('<div class="shad-card"><h4>💳 Plataformas</h4>', unsafe_allow_html=True)
        st.caption("Pagos con tarjeta por plataforma")
        if st.button("📥 CSV Plataformas", use_container_width=True, key="exp_cont_plat"):
            cli_c = MCli_cont(MONGO_URL_C, serverSelectionTimeoutMS=5000)
            db_c = cli_c["pena_linda"]
            docs = list(db_c["pagos"].find({
                "fuente": {"$in": ["Izipay", "Culqi", "Openpay"]},
                "fecha": {"$gte": datetime.combine(fi, datetime.min.time()),
                          "$lte": datetime.combine(ff, datetime.max.time())}
            }))
            cli_c.close()

            rows = []
            for d in docs:
                rows.append({
                    "Fecha": d["fecha"].strftime("%d/%m/%Y %H:%M") if d.get("fecha") else "",
                    "Plataforma": d.get("fuente", ""),
                    "Monto": d.get("monto", 0),
                    "Método": d.get("metodo", ""),
                    "Tipo": d.get("tipo_pago", ""),
                })
            exp_df = pd.DataFrame(rows)
            exp_df = exp_df.sort_values("Fecha", ascending=False)

            csv_bytes = exp_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv_bytes,
                               f"Plataformas_{fi.strftime('%Y%m%d')}_{ff.strftime('%Y%m%d')}.csv",
                               "text/csv", use_container_width=True, key="dl_cont_plat")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Costos operativos ---
    with r_c3:
        st.markdown('<div class="shad-card"><h4>💸 Costos</h4>', unsafe_allow_html=True)
        st.caption("Todos los costos operativos")
        if st.button("📥 CSV Costos", use_container_width=True, key="exp_cont_cost"):
            cli_c = MCli_cont(MONGO_URL_C, serverSelectionTimeoutMS=5000)
            db_c = cli_c["pena_linda"]
            docs = list(db_c["pagos"].find({
                "tipo_pago": "Costo",
                "fuente": {"$ne": "Saldo Base"},
                "fecha": {"$gte": datetime.combine(fi, datetime.min.time()),
                          "$lte": datetime.combine(ff, datetime.max.time())}
            }))
            cli_c.close()

            rows = []
            for d in docs:
                rows.append({
                    "Fecha": d["fecha"].strftime("%d/%m/%Y") if d.get("fecha") else "",
                    "Categoría": d.get("fuente", "").replace("Costo ", ""),
                    "Monto": d.get("monto", 0),
                    "Concepto": d.get("metodo", ""),
                })
            exp_df = pd.DataFrame(rows)
            exp_df = exp_df.sort_values("Fecha", ascending=False)

            csv_bytes = exp_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv_bytes,
                               f"Costos_{fi.strftime('%Y%m%d')}_{ff.strftime('%Y%m%d')}.csv",
                               "text/csv", use_container_width=True, key="dl_cont_cost")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. Pagos recibidos (abonos) ---
    with r_c4:
        st.markdown('<div class="shad-card"><h4>💰 Abonos</h4>', unsafe_allow_html=True)
        st.caption("Pagos recibidos de Peña Linda")
        if st.button("📥 CSV Abonos", use_container_width=True, key="exp_cont_abon"):
            cli_c = MCli_cont(MONGO_URL_C, serverSelectionTimeoutMS=5000)
            db_c = cli_c["pena_linda"]
            docs = list(db_c["cobros"].find({
                "tipo": "abono",
                "fecha": {"$gte": datetime.combine(fi, datetime.min.time()),
                          "$lte": datetime.combine(ff, datetime.max.time())}
            }))
            cli_c.close()

            rows = []
            for d in docs:
                rows.append({
                    "Fecha": d["fecha"].strftime("%d/%m/%Y") if d.get("fecha") else "",
                    "Monto": d.get("monto", 0),
                    "Origen": d.get("origen", ""),
                    "Descripción": d.get("descripcion", d.get("concepto", "")),
                    "Estado": d.get("estado", ""),
                })
            exp_df = pd.DataFrame(rows)
            exp_df = exp_df.sort_values("Fecha", ascending=False)

            csv_bytes = exp_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv_bytes,
                               f"Abonos_{fi.strftime('%Y%m%d')}_{ff.strftime('%Y%m%d')}.csv",
                               "text/csv", use_container_width=True, key="dl_cont_abon")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Reporte Consolidado Contador ---
    st.markdown("---")
    st.markdown("### 📑 Reporte Consolidado Contador (Excel)")
    st.write("Un solo archivo Excel con todas las hojas: Ventas, Plataformas, Costos, Abonos, Resumen.")

    if st.button("📑 Generar Excel Contador", use_container_width=True, key="exp_cont_all"):
        cli_c = MCli_cont(MONGO_URL_C, serverSelectionTimeoutMS=5000)
        db_c = cli_c["pena_linda"]

        fi_dt = datetime.combine(fi, datetime.min.time())
        ff_dt = datetime.combine(ff, datetime.max.time())

        # Ventas Sirvoy
        sv_docs = list(db_c["pagos"].find({
            "fuente": "Sirvoy",
            "fecha": {"$gte": fi_dt, "$lte": ff_dt}
        }))
        sv_rows = []
        for d in sv_docs:
            meta = d.get("metadata", "{}")
            pid = meta.replace('{"PaymentId": "', '').replace('"}', '') if "PaymentId" in meta else ""
            sv_rows.append({
                "Payment ID": pid,
                "Fecha": d["fecha"].strftime("%d/%m/%Y %H:%M") if d.get("fecha") else "",
                "Método": d.get("metodo", ""),
                "Tipo": d.get("tipo_pago", ""),
                "Monto": d.get("monto", 0),
                "Reserva": d.get("reserva", ""),
                "Comentario": d.get("comentario", ""),
            })
        df_sv = pd.DataFrame(sv_rows).sort_values("Fecha", ascending=False) if sv_rows else pd.DataFrame()

        # Plataformas
        plat_docs = list(db_c["pagos"].find({
            "fuente": {"$in": ["Izipay", "Culqi", "Openpay"]},
            "fecha": {"$gte": fi_dt, "$lte": ff_dt}
        }))
        plat_rows = []
        for d in plat_docs:
            plat_rows.append({
                "Fecha": d["fecha"].strftime("%d/%m/%Y %H:%M") if d.get("fecha") else "",
                "Plataforma": d.get("fuente", ""),
                "Monto": d.get("monto", 0),
                "Método": d.get("metodo", ""),
            })
        df_plat = pd.DataFrame(plat_rows).sort_values("Fecha", ascending=False) if plat_rows else pd.DataFrame()

        # Costos
        cost_docs = list(db_c["pagos"].find({
            "tipo_pago": "Costo",
            "fuente": {"$ne": "Saldo Base"},
            "fecha": {"$gte": fi_dt, "$lte": ff_dt}
        }))
        cost_rows = []
        for d in cost_docs:
            cost_rows.append({
                "Fecha": d["fecha"].strftime("%d/%m/%Y") if d.get("fecha") else "",
                "Categoría": d.get("fuente", "").replace("Costo ", ""),
                "Monto": d.get("monto", 0),
                "Concepto": d.get("metodo", ""),
            })
        df_cost = pd.DataFrame(cost_rows).sort_values("Fecha", ascending=False) if cost_rows else pd.DataFrame()

        # Abonos
        abon_docs = list(db_c["cobros"].find({
            "tipo": "abono",
            "fecha": {"$gte": fi_dt, "$lte": ff_dt}
        }))
        abon_rows = []
        for d in abon_docs:
            abon_rows.append({
                "Fecha": d["fecha"].strftime("%d/%m/%Y") if d.get("fecha") else "",
                "Monto": d.get("monto", 0),
                "Origen": d.get("origen", ""),
                "Descripción": d.get("descripcion", d.get("concepto", "")),
                "Estado": d.get("estado", ""),
            })
        df_abon = pd.DataFrame(abon_rows).sort_values("Fecha", ascending=False) if abon_rows else pd.DataFrame()

        # Resumen
        total_sv = df_sv["Monto"].sum() if not df_sv.empty else 0
        total_plat = df_plat["Monto"].sum() if not df_plat.empty else 0
        total_cost = df_cost["Monto"].sum() if not df_cost.empty else 0
        total_abon = df_abon["Monto"].sum() if not df_abon.empty else 0
        comision = total_sv * 0.05

        resumen_rows = [
            {"Concepto": "Ventas Sirvoy (neto)", "Monto": total_sv},
            {"Concepto": "Comisión 5%", "Monto": comision},
            {"Concepto": "Plataformas (confirmación tarjeta)", "Monto": total_plat},
            {"Concepto": "Costos operativos", "Monto": total_cost},
            {"Concepto": "Abonos recibidos", "Monto": total_abon},
            {"Concepto": "Saldo pendiente", "Monto": comision + total_cost - total_abon},
        ]
        df_res = pd.DataFrame(resumen_rows)

        cli_c.close()

        # Exportar a Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_res.to_excel(writer, sheet_name="Resumen", index=False)
            if not df_sv.empty:
                df_sv.to_excel(writer, sheet_name="Ventas Sirvoy", index=False)
            if not df_plat.empty:
                df_plat.to_excel(writer, sheet_name="Plataformas", index=False)
            if not df_cost.empty:
                df_cost.to_excel(writer, sheet_name="Costos", index=False)
            if not df_abon.empty:
                df_abon.to_excel(writer, sheet_name="Abonos", index=False)

        st.download_button(
            "⬇️ Descargar Excel Contador",
            data=buffer.getvalue(),
            file_name=f"Reporte_Contador_{fi.strftime('%Y%m%d')}_{ff.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_cont_excel",
        )

    # ─── REPORTES SEMANALES ───
    st.markdown("---")
    st.markdown("### 📅 Reportes Semanales Consolidados (Martes a Lunes)")
    st.write("Genera y descarga el reporte consolidado semanal con factura incluida.")

    start_date_w = date(2026, 3, 3)
    end_date_w = datetime.now().date()

    current_w = start_date_w
    weeks_list = []
    while current_w <= end_date_w:
        w_start = current_w
        w_end = current_w + timedelta(days=6)
        label = f"Semana: {w_start.strftime('%d/%m/%Y')} al {w_end.strftime('%d/%m/%Y')}"
        weeks_list.append((w_start, w_end, label))
        current_w += timedelta(days=7)

    weeks_list.reverse()

    selected_week_opt = st.selectbox(
        "Seleccionar período semanal:",
        options=range(len(weeks_list)),
        format_func=lambda idx: weeks_list[idx][2],
        key="weekly_export_select",
    )

    if selected_week_opt is not None:
        w_start, w_end, w_label = weeks_list[selected_week_opt]

        df_week = df[(df["date"].dt.date >= w_start) & (df["date"].dt.date <= w_end)]

        is_sale_w = (df_week["fuente"] == "Sirvoy") & (~df_week["tipo_pago"].isin(["Costo", "Abono"])) & (~df_week["fuente"].isin(["Abono Chamba", "Saldo Base"]))
        sales_sirvoy_w = df_week[is_sale_w]
        v_sirvoy_monto = float(sales_sirvoy_w["amount"].sum())
        v_sirvoy_tx = len(sales_sirvoy_w)
        comision_w = v_sirvoy_monto * 0.05
        costos_w = df_week[(df_week["tipo_pago"] == "Costo") & (df_week["fuente"] != "Saldo Base")]
        v_costos_monto = float(costos_w["amount"].sum())
        abonos_w = df_week[df_week["fuente"] == "Abono Chamba"]
        v_abonos_monto = float(abonos_w["amount"].sum())
        v_devoluciones = float(sales_sirvoy_w[sales_sirvoy_w["amount"] < 0]["amount"].sum())
        v_neto_sirvoy = v_sirvoy_monto

        saldo_base_doc = df[df["fuente"] == "Saldo Base"]
        v_saldo_base = float(saldo_base_doc["amount"].sum()) if not saldo_base_doc.empty else 0

        col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns(5)
        with col_w1:
            st.metric("Ventas Sirvoy Bruto", f"S/ {v_sirvoy_monto:,.2f}", f"{v_sirvoy_tx} tx")
        with col_w2:
            st.metric("Comisión Chamba (5%)", f"S/ {comision_w:,.2f}")
        with col_w3:
            st.metric("Gastos / Costos", f"S/ {v_costos_monto:,.2f}")
        with col_w4:
            st.metric("Abonos Registrados", f"S/ {v_abonos_monto:,.2f}")
        with col_w5:
            label_dev = f"{v_devoluciones:,.2f}" if v_devoluciones != 0 else "—"
            st.metric("💰 Neto Sirvoy", f"S/ {v_neto_sirvoy:,.2f}", label_dev if v_devoluciones != 0 else None)

        if v_saldo_base > 0:
            st.info(f"📋 **Deuda Inicial al 03/03/2026:** S/ {v_saldo_base:,.2f} (Saldo Base — pendiente Chamba Digital → Peña Linda)")

        dec_col1, dec_col2 = st.columns(2)
        with dec_col1:
            st.markdown("##### 💸 Gastos de la Semana")
            if not costos_w.empty:
                c_disp = costos_w.sort_values("date_pe").copy()
                c_disp["Fecha"] = c_disp["date_pe"].dt.strftime("%d/%m/%Y")
                c_disp["Monto"] = c_disp["amount"].apply(lambda x: f"S/ {x:,.2f}")
                c_disp["Concepto"] = c_disp["fuente"]
                c_disp["Referencia"] = c_disp["metodo"]
                st.dataframe(c_disp[["Fecha", "Concepto", "Referencia", "Monto"]], hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron gastos en esta semana.")

        with dec_col2:
            st.markdown("##### 💳 Abonos de la Semana")
            if not abonos_w.empty:
                a_disp = abonos_w.sort_values("date_pe").copy()
                a_disp["Fecha"] = a_disp["date_pe"].dt.strftime("%d/%m/%Y")
                a_disp["Monto"] = a_disp["amount"].apply(lambda x: f"S/ {x:,.2f}")
                a_disp["Referencia / Canal"] = a_disp["metodo"]
                st.dataframe(a_disp[["Fecha", "Referencia / Canal", "Monto"]], hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron abonos en esta semana.")

        costs_list = []
        if v_saldo_base > 0:
            costs_list.append({
                "fuente": "Saldo Base",
                "monto": v_saldo_base,
                "fecha": datetime(2026, 3, 3),
                "detalle": "Deuda inicial pendiente al 03/03/2026",
            })
        for _, r in costos_w.iterrows():
            costs_list.append({
                "fuente": r.get("fuente", ""),
                "monto": float(r.get("amount", 0)),
                "fecha": r.get("date_pe"),
                "detalle": r.get("metodo", ""),
            })

        abonos_list = []
        for _, r in abonos_w.iterrows():
            abonos_list.append({
                "concepto": r.get("metodo", ""),
                "detalle": r.get("metodo", ""),
                "monto": float(r.get("amount", 0)),
                "fecha": r.get("date_pe"),
            })

        devoluciones_df = sales_sirvoy_w[sales_sirvoy_w["amount"] < 0].copy()
        devoluciones_list = []
        if not devoluciones_df.empty:
            for _, r in devoluciones_df.iterrows():
                comment = str(r.get("comment", ""))
                motivo = comment if comment and comment != "nan" else str(r.get("method", ""))
                devoluciones_list.append({
                    "monto": float(r["amount"]),
                    "fecha": r.get("date_pe"),
                    "metodo": motivo,
                    "detalle": motivo,
                    "referencia": str(r.get("referencia", "")),
                    "transaction_id": str(r.get("transaction_id", "")),
                })

        if not devoluciones_df.empty:
            total_dev = float(devoluciones_df["amount"].sum())
            st.warning(f"⚠️ **{len(devoluciones_list)} transacciones negativas** detectadas (S/ {total_dev:,.2f}): devoluciones, correcciones o errores de tipeo.")
            dev_disp = devoluciones_df.sort_values("date_pe").copy()
            dev_disp["Fecha"] = dev_disp["date_pe"].dt.strftime("%d/%m/%Y")
            dev_disp["Monto"] = dev_disp["amount"].apply(lambda x: f"S/ {x:,.2f}")
            dev_disp["Método"] = dev_disp["method"]
            dev_disp["Motivo"] = dev_disp["comment"].fillna(dev_disp["metodo"]).fillna("") if "comment" in dev_disp.columns else dev_disp["method"].fillna("")
            dev_disp["ID"] = dev_disp["transaction_id"]
            show_cols = ["Fecha", "Método", "Motivo", "ID", "Monto"]
            show_cols = [c for c in show_cols if c in dev_disp.columns]
            st.dataframe(dev_disp[show_cols], hide_index=True, use_container_width=True)

        pdf_bytes = generate_weekly_pdf(
            ws=w_start,
            we=w_end,
            ventas_bruto=v_sirvoy_monto,
            reversiones=0,
            costs_list=costs_list,
            abonos_list=abonos_list,
            devoluciones_list=devoluciones_list,
        )

        st.download_button(
            "⬇️ Descargar Reporte PDF Semanal",
            data=pdf_bytes,
            file_name=f"Reporte_Semanal_{w_start.strftime('%Y%m%d')}_{w_end.strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="weekly_pdf_dl",
        )
