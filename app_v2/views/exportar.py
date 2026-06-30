# views/exportar.py - Exportación PDF/HTML (simplificado)
import streamlit as st
import io

def render(df, k, fi, ff, sv, sv_date_filtered):
    st.markdown("## 📤 Exportar Reportes")
    st.info("Exportación de reportes disponible en la versión v1 (puerto 8501).")
    st.write("")
    
    # CSV directo
    if not sv_date_filtered.empty:
        csv_bytes = sv_date_filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Descargar CSV", csv_bytes,
                          file_name=f"ventas_{fi}_{ff}.csv", mime="text/csv",
                          use_container_width=True)
    else:
        st.caption("Sin datos para exportar.")
