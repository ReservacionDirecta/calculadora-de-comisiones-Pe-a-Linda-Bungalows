# components.py - Componentes reutilizables (optimizado)
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

# ─── Export helpers ───
def df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig") if not df.empty else "".encode()

def df_to_excel(df):
    output = io.BytesIO()
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            if df_clean[col].dt.tz is not None:
                df_clean[col] = df_clean[col].dt.tz_localize(None)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_clean.to_excel(writer, index=False, sheet_name="Reporte")
    return output.getvalue()


# ─── Bento KPI card ───
def bento_kpi(label, value, sub, color, fmt="S/ {:,.2f}"):
    if isinstance(value, (int, float)):
        val_str = fmt.format(value)
    else:
        val_str = str(value)
    st.markdown(f"""
    <div class="bento-item" style="border-top:3px solid {color};">
        <div class="bento-label">{label}</div>
        <div class="bento-value" style="color:{color};">{val_str}</div>
        <div class="bento-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Alerta ───
def alert_box(title, body, action_html=""):
    st.markdown(f"""
    <div class="alert-box">
        <div class="alert-title">{title}</div>
        <div class="alert-body">{body}</div>
        {f'<div class="alert-action">{action_html}</div>' if action_html else ""}
    </div>
    """, unsafe_allow_html=True)


# ─── Export buttons row ───
def export_buttons(key_prefix, df, fi, ff, label="", container_width=True):
    """Dos botones: CSV y Excel."""
    if df is None or df.empty:
        st.caption("Sin datos para exportar")
        return
    col1, col2 = st.columns(2)
    slug = label.lower().replace(" ", "_")
    with col1:
        st.download_button(
            f"📥 CSV {label}" if label else "📥 CSV",
            data=df_to_csv(df),
            file_name=f"{slug}_{fi}_{ff}.csv",
            mime="text/csv",
            use_container_width=container_width,
            key=f"{key_prefix}_csv",
        )
    with col2:
        st.download_button(
            f"📥 Excel {label}" if label else "📥 Excel",
            data=df_to_excel(df),
            file_name=f"{slug}_{fi}_{ff}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=container_width,
            key=f"{key_prefix}_xlsx",
        )


# ─── Scales ───
def get_yscale(escala_log):
    return dict(type="log") if escala_log else {}


# ─── Weekly PDF Report (like v1) ───
def generate_weekly_pdf(ws, we, ventas_bruto, reversiones, costs_list, abonos_list, devoluciones_list=None, comision_pct=0.05):
    """Genera un PDF invoice-style con reportlab (lazy import)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors as rc
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    comision = ventas_bruto * comision_pct
    total_costos = sum(d.get('monto', 0) for d in costs_list)
    total_abonos = sum(d.get('monto', 0) for d in abonos_list)
    subtotal = comision + total_costos
    saldo_pend = subtotal - total_abonos

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
    cell_left = ParagraphStyle('CellL', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT)

    elems = []

    # 1. Header
    info = """<b>Chamba Digital SAC</b><br/>
Alameda del Premio Real Mz. K, Lt. 34C, La Encantada de Villa, Chorrillos<br/>
Lima, Lima 15067 PE<br/>
hola@chambadigital.la<br/>
chambadigital.la<br/>
N.° de registro de IGV: 20604661476"""
    p_info = Paragraph(info, ParagraphStyle('CI', fontSize=7, leading=9, textColor=rc.HexColor('#333')))
    p_title = Paragraph("<b>Factura De<br/>Servicios</b>",
                        ParagraphStyle('CT', fontSize=15, leading=17, textColor=rc.HexColor('#111'), alignment=TA_CENTER))
    logo_data = [[Paragraph("<font color='white'><b>CHA</b></font>",
                             ParagraphStyle('L1', fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER))],
                 [Paragraph("<font color='white'><b>MBA</b></font>",
                             ParagraphStyle('L2', fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER))],
                 [Paragraph("<font color='#D6D6FF'><b>• DIGITAL</b></font>",
                             ParagraphStyle('L3', fontName='Helvetica-Bold', fontSize=6, alignment=TA_CENTER))]]
    t_logo = Table(logo_data, colWidths=[70])
    t_logo.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), rc.HexColor('#0000FF')),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ('TOPPADDING', (0,0), (-1,-1), 4),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    t_header = Table([[p_info, p_title, t_logo]], colWidths=[200, 180, 100])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    elems.append(t_header)
    elems.append(Spacer(1, 5))

    # 2. Facturar a
    fa_data = [[Paragraph("<b>FACTURAR A</b>", ParagraphStyle('FH', fontSize=7, textColor=rc.HexColor('#1B365D')))],
               [Paragraph("Peña Linda Bungalows Sac", ParagraphStyle('FB', fontSize=9, textColor=rc.HexColor('#333')))]]
    t_fa = Table(fa_data, colWidths=[200])
    t_fa.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                              ('BOX', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                              ('TOPPADDING', (0,0), (-1,-1), 3),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                              ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    elems.append(t_fa)
    elems.append(Spacer(1, 8))

    # 3. Metadata
    invoice_num = f"INV{int(ws.strftime('%y%m%d')) % 1000:03d}"
    total_p_str = f"S/. {subtotal:,.2f}"
    mh = [Paragraph(f"<b>{c}</b>", ParagraphStyle('MH', fontSize=7, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER))
          for c in ["FACTURA N.º", "FECHA", "TOTAL A PAGAR", "FECHA DE VENCIMIENTO", "CONDICIONES"]]
    mv = [Paragraph(v, ParagraphStyle('MV', fontSize=8, alignment=TA_CENTER))
          for v in [invoice_num, we.strftime('%d/%m/%Y'), total_p_str,
                    (we + timedelta(days=7)).strftime('%d/%m/%Y'), "7 Días"]]
    t_meta = Table([mh, mv], colWidths=[80, 80, 100, 100, 80])
    t_meta.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                                ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ('TOPPADDING', (0,0), (-1,-1), 4),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elems.append(t_meta)
    elems.append(HRFlowable(width="100%", thickness=0.5, color=rc.HexColor('#CCC'), spaceBefore=8, spaceAfter=2, dash=(2,2)))
    elems.append(Paragraph("<font color='#666' size='6'>SEPARE LA PARTE SUPERIOR Y REGRÉSELA JUNTO CON EL PAGO.</font>",
                           ParagraphStyle('Sep', alignment=TA_CENTER)))
    elems.append(Spacer(1, 10))

    # 4. Main concepts table
    items = [[Paragraph(f"<b>{c}</b>", ParagraphStyle('MTH', fontSize=7, textColor=rc.HexColor('#1B365D'),
                        alignment=TA_LEFT if i == 1 else TA_CENTER))
              for i, c in enumerate(["FECHA", "DESCRIPCIÓN", "CANT.", "TASA", "IMPORTE"])]]
    items.append([Paragraph(we.strftime('%d/%m/%Y'), cell_style),
                  Paragraph(f"<b>Comisión del 5% por ventas generadas</b><br/>"
                            f"Ventas generadas del {ws.strftime('%d-%m')} al {we.strftime('%d-%m')}<br/>"
                            f"S/. {ventas_bruto:,.2f}", cell_left),
                  Paragraph("1", cell_style),
                  Paragraph(f"{comision:,.2f}", cell_style),
                  Paragraph(f"{comision:,.2f}", cell_style)])
    for c in costs_list:
        f = c.get('fecha', '')
        if isinstance(f, datetime):
            f_str = f.strftime('%d/%m/%Y')
        else:
            f_str = str(f)[:10]
        items.append([Paragraph(f_str, cell_style),
                      Paragraph(f"<b>{c.get('fuente', 'Costo')}</b><br/>{c.get('detalle', '')}", cell_left),
                      Paragraph("1", cell_style),
                      Paragraph(f"{c.get('monto', 0):,.2f}", cell_style),
                      Paragraph(f"{c.get('monto', 0):,.2f}", cell_style)])

    total_cell = ParagraphStyle('TotCell', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    items.append([Paragraph("", cell_style),
                  Paragraph("<b>TOTAL CONCEPTOS</b>", ParagraphStyle('TotLbl', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
                  Paragraph("", cell_style),
                  Paragraph("", cell_style),
                  Paragraph(f"<b>{subtotal:,.2f}</b>", total_cell)])

    col_widths = [70, 240, 30, 70, 70]
    t_main = Table(items, colWidths=col_widths)
    t_main.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                                ('BACKGROUND', (0,-1), (-1,-1), rc.HexColor('#EDF2F7')),
                                ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                                ('LINEABOVE', (0,-1), (-1,-1), 1, rc.HexColor('#1B365D')),
                                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                ('TOPPADDING', (0,0), (-1,-1), 5),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
    elems.append(t_main)
    elems.append(Paragraph(
        f"<i>La comisión se calcula sobre ventas generadas: S/. {ventas_bruto:,.2f}</i>",
        ParagraphStyle('Nota', fontSize=7, textColor=rc.HexColor('#888'), spaceBefore=3, spaceAfter=5)))

    # 5. Totals
    tdata = [
        [Paragraph("SUBTOTAL", cell_left), Paragraph(f"{subtotal:,.2f}", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
        [Paragraph("IMPUESTO", cell_left), Paragraph("0,00", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
        [Paragraph("TOTAL", cell_left), Paragraph(f"{subtotal:,.2f}", ParagraphStyle('TR', alignment=TA_RIGHT, fontSize=8))],
        [Paragraph("<b>SALDO PENDIENTE</b>", cell_left),
         Paragraph(f"<b>S/. {saldo_pend:,.2f}</b>", ParagraphStyle('TRB', alignment=TA_RIGHT, fontSize=11, fontName='Helvetica-Bold'))],
    ]
    t_tot = Table(tdata, colWidths=[110, 110])
    t_tot.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-2), 0.3, rc.HexColor('#EEE')),
                               ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
                               ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                               ('TOPPADDING', (0,0), (-1,-1), 3),
                               ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    sl = [[Paragraph("Gracias por elegirnos como tus aliados tecnológicos.",
                     ParagraphStyle('Thx', fontSize=9, textColor=rc.HexColor('#555'))), t_tot]]
    t_sum = Table(sl, colWidths=[260, 220])
    t_sum.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 5)]))
    elems.append(t_sum)
    elems.append(Spacer(1, 10))

    # 6. Tax summary
    ih = [Paragraph(f"<b>{c}</b>", ParagraphStyle('IH', fontSize=7, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER))
          for c in ["TASA", "IMPUESTOS DE", "BASE IMPONIBLE"]]
    iv = [Paragraph(v, ParagraphStyle('IV', fontSize=8, alignment=TA_CENTER))
          for v in ["IGV de 0%", "0,00", f"{subtotal:,.2f}"]]
    t_tax = Table([ih, iv], colWidths=[120, 180, 180])
    t_tax.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                               ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                               ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                               ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                               ('TOPPADDING', (0,0), (-1,-1), 4),
                               ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elems.append(Paragraph("<b>RESUMEN DE IMPUESTOS</b>",
                           ParagraphStyle('RIT', fontSize=8, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=3)))
    elems.append(t_tax)
    elems.append(Spacer(1, 10))

    # 7. Abonos
    if abonos_list:
        elems.append(HRFlowable(width="100%", thickness=1, color=rc.HexColor('#E4E4E7'), spaceBefore=5, spaceAfter=3))
        elems.append(Paragraph("<b>ABONOS RECIBIDOS EN LA SEMANA</b>",
                               ParagraphStyle('ABT', fontSize=9, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=3,
                                              textColor=rc.HexColor('#1B365D'))))
        ah = [Paragraph(f"<b>{c}</b>", ParagraphStyle('AH', fontSize=7, textColor=rc.HexColor('#1B365D'), alignment=TA_CENTER))
              for c in ["FECHA", "REFERENCIA / CANAL", "IMPORTE"]]
        arows = [ah]
        for a in sorted(abonos_list, key=lambda x: x.get('fecha', datetime.min)):
            f = a.get('fecha', '')
            f_str = f.strftime('%d/%m/%Y') if isinstance(f, datetime) else str(f)[:10]
            arows.append([
                Paragraph(f_str, cell_style),
                Paragraph(str(a.get('detalle', a.get('concepto', '')))[:30], cell_left),
                Paragraph(f"S/. {a.get('monto', 0):,.2f}", cell_style),
            ])
        arows.append([
            Paragraph("", cell_style),
            Paragraph("<b>TOTAL ABONOS</b>", ParagraphStyle('ABTot', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            Paragraph(f"<b>S/. {total_abonos:,.2f}</b>", ParagraphStyle('ABTotV', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        ])
        t_ab = Table(arows, colWidths=[100, 260, 120])
        t_ab.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), rc.HexColor('#D6D6FF')),
                                  ('BACKGROUND', (0,-1), (-1,-1), rc.HexColor('#EDF2F7')),
                                  ('GRID', (0,0), (-1,-1), 0.5, rc.HexColor('#CCCCFF')),
                                  ('LINEABOVE', (0,-1), (-1,-1), 1, rc.HexColor('#1B365D')),
                                  ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                  ('TOPPADDING', (0,0), (-1,-1), 4),
                                  ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
        elems.append(t_ab)
        elems.append(Spacer(1, 15))
    else:
        elems.append(Spacer(1, 10))

    # 8. Devoluciones / Correcciones / Errores de tipeo
    if devoluciones_list:
        total_dev = sum(d.get('monto', 0) for d in devoluciones_list)
        elems.append(HRFlowable(width="100%", thickness=1, color=rc.HexColor('#FFCCCC'), spaceBefore=5, spaceAfter=3))
        elems.append(Paragraph("<b>ANOMALIAS: DEVOLUCIONES / CORRECCIONES / ERRORES</b>",
                               ParagraphStyle('DVT', fontSize=9, fontName='Helvetica-Bold',
                                              spaceBefore=5, spaceAfter=3, textColor=rc.HexColor('#CC0000'))))
        elems.append(Paragraph(
            f"Se detectaron {len(devoluciones_list)} transacciones con montos negativos "
            f"(total S/. {total_dev:,.2f}). Estas reducen el bruto del periodo.",
            ParagraphStyle('DVS', fontSize=7, textColor=rc.HexColor('#666'), spaceAfter=5)))
        dh = [Paragraph(f"<b>{c}</b>", ParagraphStyle('DH', fontSize=7, textColor=rc.HexColor('#CC0000'), alignment=TA_CENTER))
              for c in ["FECHA", "REFERENCIA", "MOTIVO", "IMPORTE"]]
        drows = [dh]
        for d in devoluciones_list:
            f = d.get('fecha', '')
            f_str = f.strftime('%d/%m/%Y') if isinstance(f, datetime) else str(f)[:10]
            motivo = d.get('metodo', d.get('detalle', ''))
            ref = str(d.get('referencia', d.get('transaction_id', '')))[:20]
            drows.append([
                Paragraph(f_str, cell_style),
                Paragraph(ref, cell_left),
                Paragraph(motivo, cell_left),
                Paragraph(f"<font color='#CC0000'>S/. {d.get('monto', 0):,.2f}</font>", cell_style),
            ])
        drows.append([
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph("<b>TOTAL ANOMALIAS</b>", ParagraphStyle('DVTot', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=rc.HexColor('#CC0000'))),
            Paragraph(f"<b><font color='#CC0000'>S/. {total_dev:,.2f}</font></b>", ParagraphStyle('DVTotV', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        ])
        t_dev = Table(drows, colWidths=[80, 100, 160, 100])
        t_dev.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), rc.HexColor('#FFF0F0')),
                                   ('BACKGROUND', (0, -1), (-1, -1), rc.HexColor('#FFF0F0')),
                                   ('GRID', (0, 0), (-1, -1), 0.5, rc.HexColor('#FFCCCC')),
                                   ('LINEABOVE', (0, -1), (-1, -1), 1, rc.HexColor('#CC0000')),
                                   ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                   ('TOPPADDING', (0, 0), (-1, -1), 4),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        elems.append(t_dev)
        elems.append(Spacer(1, 10))

    # Footer
    elems.append(Paragraph("Enviar comprobante de pago a hola@chambadigital.la",
                           ParagraphStyle('FI', fontSize=9, alignment=TA_CENTER, textColor=rc.HexColor('#555'))))
    doc.build(elems)
    return buffer.getvalue()
