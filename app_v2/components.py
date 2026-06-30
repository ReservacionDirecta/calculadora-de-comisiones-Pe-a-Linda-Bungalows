# components.py - Componentes reutilizables
import streamlit as st
import pandas as pd
import io

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
    """Renderiza una card del bento grid."""
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


# ─── Alerta / acción ───
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
