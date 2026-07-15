# views/agente.py - Agente de consultas con OpenRouter (completo)
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pymongo import MongoClient


def get_system_prompt():
    return """Eres el asistente financiero de Peña Linda Bungalows (hotel en Peru, gestionado por Chamba Digital SAC).

CONTEXTO:
- Hotel registra ventas via Sirvoy (fuente maestra)
- Plataformas de cobro: Izipay, Culqui, Openpay (confirmacion de tarjeta)
- Comision Chamba Digital: 5% sobre ventas Sirvoy netas
- Gestion inicia 03/03/2026 con Saldo Base de S/ 9,654.83
- Costos: Facebook Ads, Asistente Comercial, Sirvoy plataforma

REGLAS:
- Responde en espanol, seconciso y claro
- Muestra montos formateados: S/ X,XXX.XX
- Si no tienes datos suficientes, pide especificar fechas o contexto
- Para comparativas, muestra diferencias porcentuales
- Si te preguntan por transacciones especificas, muestra tabla resumen"""

# ─── Consultas predefinidas ───
QUERIES = {
    "resumen_mes": {
        "label": "Resumen del mes actual",
        "prompt": "Dame el resumen financiero del mes actual: ventas, comision, costos y saldo.",
        "aggregation": lambda fi, ff: [
            {"$match": {"fecha": {"$gte": datetime(fi.year, fi.month, 1),
                                   "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": {"fuente": "$fuente", "tipo": "$tipo_pago"},
                        "total": {"$sum": "$monto"}, "count": {"$sum": 1}}}
        ]
    },
    "ventas_por_mes": {
        "label": "Ventas por mes",
        "prompt": "Muestra las ventas totales de Sirvoy por mes del ano en curso.",
        "aggregation": lambda fi, ff: [
            {"$match": {"fuente": "Sirvoy", "fecha": {"$gte": datetime(2026, 1, 1), "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}},
                        "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
    },
    "costos_categoria": {
        "label": "Costos por categoria",
        "prompt": "Desglosa los costos operativos por categoria (FB Ads, Sirvoy, Asistente, Extra).",
        "aggregation": lambda fi, ff: [
            {"$match": {"tipo_pago": "Costo", "fuente": {"$ne": "Saldo Base"},
                        "fecha": {"$gte": datetime(fi.year, fi.month, 1),
                                   "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": "$fuente", "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}}
        ]
    },
    "abonos_recibidos": {
        "label": "Abonos recibidos",
        "prompt": "Cuales son los abonos recibidos de Peña Linda y su estado de pagos?",
        "aggregation": lambda fi, ff: [
            {"$match": {"tipo": "abono", "fecha": {"$gte": datetime(2026, 3, 3),
                                                   "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}},
                        "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": -1}}
        ]
    },
    "top_reservas": {
        "label": "Top reservas",
        "prompt": "Cuales son las 10 reservas con mayor monto pagado en Sirvoy?",
        "aggregation": lambda fi, ff: [
            {"$match": {"fuente": "Sirvoy", "fecha": {"$gte": datetime(fi.year, fi.month, 1),
                                                       "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": "$reserva", "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}},
            {"$limit": 10}
        ]
    },
    "deuda_acumulada": {
        "label": "Deuda acumulada",
        "prompt": "Cual es el estado de la deuda acumulada desde 03/03/2026?",
        "aggregation": None  # Uses k dict directly
    },
    "comparativa_meses": {
        "label": "Comparativa meses",
        "prompt": "Compara las ventas del mes actual vs el mes anterior.",
        "aggregation": lambda fi, ff: [
            {"$match": {"fuente": "Sirvoy", "fecha": {"$gte": datetime(2026, 1, 1), "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}},
                        "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": -1}},
            {"$limit": 3}
        ]
    },
    "metodos_pago": {
        "label": "Metodos de pago",
        "prompt": "Cual es la distribucion de pagos por metodo (Tarjeta, Transferencia, Efectivo)?",
        "aggregation": lambda fi, ff: [
            {"$match": {"fuente": "Sirvoy", "tipo_pago": {"$in": ["Tarjeta", "Transferencia", "Efectivo"]},
                        "fecha": {"$gte": datetime(fi.year, fi.month, 1),
                                   "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": "$tipo_pago", "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}}
        ]
    },
    "plataformas": {
        "label": "Plataformas cobro",
        "prompt": "Cual es el desglose de pagos por plataforma (Izipay, Culqi, Openpay)?",
        "aggregation": lambda fi, ff: [
            {"$match": {"fuente": {"$in": ["Izipay", "Culqi", "Openpay"]}, "monto": {"$gt": 0},
                        "fecha": {"$gte": datetime(fi.year, fi.month, 1),
                                   "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}}},
            {"$group": {"_id": "$fuente", "total": {"$sum": "$monto"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}}
        ]
    },
}


def fetch_data(MONGO_URL, pipeline):
    """Ejecuta query MongoDB y retorna DataFrame."""
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = cli['pena_linda']
        result = list(db['pagos'].aggregate(pipeline))
        cli.close()
        if not result:
            return pd.DataFrame()
        return pd.DataFrame(result)
    except Exception as e:
        return pd.DataFrame([{"error": str(e)}])


def fetch_cobros(MONGO_URL, fi, ff):
    """Obtiene cobros del periodo."""
    try:
        cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = cli['pena_linda']
        result = list(db['cobros'].find({
            "fecha": {"$gte": datetime(fi.year, fi.month, 1),
                       "$lte": datetime(ff.year, ff.month, ff.day, 23, 59, 59)}
        }))
        cli.close()
        return pd.DataFrame(result) if result else pd.DataFrame()
    except:
        return pd.DataFrame()


def build_context(k, fi, ff, extra_data=None):
    """Construye contexto detallado para el LLM."""
    ctx = f"""DATOS DEL PERIODO {fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}:

VENTAS SIRVOY:
- Neto: S/ {k.get('tb_sirvoy', 0):,.2f}
- Transacciones: {k.get('tx', 0)}
- Ticket promedio: S/ {k.get('prom', 0):,.2f}

COMISION CHAMBA DIGITAL:
- 5% sobre neto: S/ {k.get('comision', 0):,.2f}

COSTOS OPERATIVOS:
- Facebook Ads: S/ {k.get('costo_fb', 0):,.2f}
- Sirvoy plataforma: S/ {k.get('costo_sv', 0):,.2f}
- Asistente: S/ {k.get('costo_as', 0):,.2f}
- Total: S/ {k.get('total_costos', 0):,.2f}

RECIBIDO:
- Plataformas (tarjeta): S/ {k.get('tb_plataformas', 0):,.2f}
- Transferencia+Efectivo: S/ {k.get('tb_recibido', 0) - k.get('tb_plataformas', 0):,.2f}
- Total recibido: S/ {k.get('tb_recibido', 0):,.2f}

HISTORICO (desde 03/03/2026):
- Ventas netas: S/ {k.get('neto_desde_mar', 0):,.2f}
- Comision acumulada: S/ {k.get('comision_desde_mar', 0):,.2f}
- Costos acumulados: S/ {k.get('total_costos_hist', 0):,.2f}
- Saldo base: S/ {k.get('saldo_base_hist', 0):,.2f}
- Total adeudado: S/ {k.get('adeudado', 0):,.2f}
- Abonos recibidos: S/ {k.get('total_abonos', 0):,.2f}
- Saldo pendiente: S/ {k.get('saldo_pendiente', 0):,.2f}
"""

    if extra_data is not None and not extra_data.empty:
        ctx += f"\nDATOS ADICIONALES CONSULTADOS:\n{extra_data.to_string(index=False)}\n"

    return ctx


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
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1500,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return f"Error API: {e.code}"
    except Exception as e:
        return f"Error: {str(e)}"


def render(df, k, t, fi, ff, MONGO_URL):
    st.markdown("## 🤖 Agente de Consultas")
    st.caption("Preguntale al agente sobre ventas, costos, comisiones, abonos o cualquier dato del hotel")

    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        st.warning("Se requiere `OPENROUTER_API_KEY` en variables de entorno.")
        st.code("OPENROUTER_API_KEY=tu_api_key_aqui", language="bash")
        return

    # Session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ─── Layout principal ───
    col_chat, col_data = st.columns([3, 2])

    with col_chat:
        st.markdown("### 💬 Chat")

        # Chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**Tú:** {msg['content']}")
                else:
                    st.markdown(f"**Agente:** {msg['content']}")
                    # Mostrar datos si existen
                    if "data" in msg and msg["data"] is not None and not msg["data"].empty:
                        st.dataframe(msg["data"], use_container_width=True, height=200)

        # Input
        user_input = st.text_input(
            "Escribi tu pregunta:",
            placeholder="Ej: Cuanto se vendio en junio 2026?",
            key="chat_input",
            label_visibility="collapsed",
        )

        btn_cols = st.columns([1, 1, 4])
        with btn_cols[0]:
            enviar = st.button("Enviar", type="primary", key="send_btn")
        with btn_cols[1]:
            if st.button("Limpiar", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

    with col_data:
        st.markdown("### 📊 Consultas Rapidas")

        for qkey, qinfo in QUERIES.items():
            if st.button(qinfo["label"], key=f"q_{qkey}", use_container_width=True):
                with st.spinner("Consultando..."):
                    extra_data = None
                    if qinfo["aggregation"]:
                        extra_data = fetch_data(MONGO_URL, qinfo["aggregation"](fi, ff))
                    elif qkey == "deuda_acumulada":
                        # Usar datos del k dict
                        pass

                    context = build_context(k, fi, ff, extra_data)
                    messages = [
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": f"{context}\n\nPregunta: {qinfo['prompt']}"},
                    ]

                    response = call_openrouter(messages, api_key)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "data": extra_data
                    })
                st.rerun()

        # Resumen rapido
        st.markdown("---")
        st.markdown("**Resumen actual:**")
        st.metric("Ventas Sirvoy", f"S/ {k.get('tb_sirvoy', 0):,.2f}")
        st.metric("Comision 5%", f"S/ {k.get('comision', 0):,.2f}")
        st.metric("Deuda pendiente", f"S/ {k.get('saldo_pendiente', 0):,.2f}")

    # ─── Procesar input del usuario ───
    if enviar and user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Consultando al agente..."):
            # Buscar datos relevantes segun la pregunta
            extra_data = None
            lower_q = user_input.lower()

            if any(w in lower_q for w in ["costo", "gasto", "fb", "facebook", "asistente"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["costos_categoria"]["aggregation"](fi, ff))
            elif any(w in lower_q for w in ["abono", "pago rec", "pagado"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["abonos_recibidos"]["aggregation"](fi, ff))
            elif any(w in lower_q for w in ["reserva", "habitacion", "top"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["top_reservas"]["aggregation"](fi, ff))
            elif any(w in lower_q for w in ["mes", "monthly", "compar"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["ventas_por_mes"]["aggregation"](fi, ff))
            elif any(w in lower_q for w in ["plataforma", "izipay", "culqi", "openpay"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["plataformas"]["aggregation"](fi, ff))
            elif any(w in lower_q for w in ["metodo", "tarjeta", "transfer", "efectivo"]):
                extra_data = fetch_data(MONGO_URL, QUERIES["metodos_pago"]["aggregation"](fi, ff))

            context = build_context(k, fi, ff, extra_data)
            messages = [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": f"{context}\n\nPregunta: {user_input}"},
            ]

            response = call_openrouter(messages, api_key)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "data": extra_data
            })

        st.rerun()
