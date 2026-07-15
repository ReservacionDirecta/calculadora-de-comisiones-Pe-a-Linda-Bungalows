# views/agente.py - Agente de consultas con OpenAI/OpenRouter
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pymongo import MongoClient

def get_system_prompt():
    return """Eres un asistente financiero para Peña Linda Bungalows (hotel en Peru).
Tienes acceso a una base de datos MongoDB con estas colecciones:

1. pagos: Transacciones de Sirvoy (ventas) y costos operativos
   - fuente: 'Sirvoy', 'Izipay', 'Culqi', 'Openpay', 'Izipay POS', 'Costo FB Ads', 'Costo Sirvoy', 'Costo Asistente', 'Costo Extra', 'Saldo Base', 'Abono Chamba'
   - tipo_pago: 'Tarjeta', 'Transferencia', 'Efectivo', 'Reversion', 'Costo', 'Abono'
   - fecha: datetime, monto: float, metodo: string, comentario: string, reserva: string

2. cobros: Facturas y abonos
   - tipo: 'comision', 'costo', 'abono', 'saldo_inicial'
   - fecha: datetime, monto: float, descripcion: string, factura: string

Reglas de negocio:
- Comision Chamba Digital: 5% sobre ventas Sirvoy netas (positivos + negativos)
- Sirvoy es la fuente maestra de ventas
- Las plataformas (Izipay/Culqi/Openpay) son confirmacion de pagos con tarjeta
- La deuda se calcula desde 03/03/2026
- Saldo Base heredado: S/ 9,654.83

Responde en espanol, se conciso y muestra montos formateados (S/ X,XXX.XX).
Si la pregunta requiere datos especificos, genera el pipeline de MongoDB necesario."""


def query_mongodb(MONGO_URL, pipeline):
    """Ejecuta un pipeline de MongoDB."""
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = cli['pena_linda']
        result = list(db['pagos'].aggregate(pipeline))
        cli.close()
        return result
    except Exception as e:
        return [{"error": str(e)}]


def call_openrouter(messages, api_key):
    """Llama a OpenRouter API."""
    import urllib.request
    import urllib.error

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://penalinda.app",
    }
    data = json.dumps({
        "model": "google/gemma-4-31b-it:free",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return f"Error API: {e.code} - {error_body[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"


def render(df, k, t, fi, ff, MONGO_URL):
    st.markdown("## 🤖 Agente de Consultas")
    st.caption("Preguntale al agente sobre ventas, costos, comisiones, abonos o cualquier dato del hotel")

    # API Key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        st.warning("Se requiere la variable de entorno `OPENROUTER_API_KEY` para usar el agente.")
        st.code("OPENROUTER_API_KEY=tu_api_key_aqui", language="bash")
        return

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"**Tú:** {msg['content']}")
        else:
            st.markdown(f"**Agente:** {msg['content']}")

    # Quick queries
    st.markdown("**Consultas rapidas:**")
    q_cols = st.columns(3)
    quick_queries = [
        "Total ventas Sirvoy del mes",
        "Desglose de costos por categoria",
        "Abonos recibidos este mes",
        "Comision pendiente de cobro",
        "Top 5 reservas con mas pagos",
        "Comparativa ventas mes anterior vs actual",
    ]

    for i, q in enumerate(quick_queries):
        col_idx = i % 3
        with q_cols[col_idx]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state.user_input = q
                st.rerun()

    # User input
    user_input = st.text_input(
        "Escribi tu pregunta:",
        value=st.session_state.get("user_input", ""),
        placeholder="Ej: Cuanto se vendio en junio 2026?",
        key="chat_input",
    )

    if st.button("Enviar", type="primary", key="send_btn") and user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.user_input = ""

        with st.spinner("Consultando..."):
            # Contexto de datos para el agente
            context = f"""
Datos del periodo {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}:
- Ventas Sirvoy netas: S/ {k.get('tb_sirvoy', 0):,.2f}
- Comision 5%: S/ {k.get('comision', 0):,.2f}
- Costos operativos: S/ {k.get('total_costos', 0):,.2f}
- Abonos recibidos: S/ {k.get('total_abonos', 0):,.2f}
- Deuda pendiente: S/ {k.get('saldo_pendiente', 0):,.2f}

Historico desde 03/03/2026:
- Comision acumulada: S/ {k.get('comision_desde_mar', 0):,.2f}
- Costos acumulados: S/ {k.get('total_costos_hist', 0):,.2f}
- Adeudado: S/ {k.get('adeudado', 0):,.2f}

Pregunta del usuario: {user_input}
"""

            messages = [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": context},
            ]

            response = call_openrouter(messages, api_key)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

        st.rerun()

    # Clear chat
    if st.button("🗑️ Limpiar chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()
