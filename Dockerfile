FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo
COPY *.py .
COPY *.csv /data/ 2>/dev/null || true

# Puerto Railway
ENV PORT=8501
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

CMD streamlit run panel_control.py --server.port ${PORT} --server.headless true --server.address 0.0.0.0
