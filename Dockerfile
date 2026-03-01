# Multi-stage build para optimizar tamaño
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y compilar wheels
COPY pyproject.toml uv.lock* ./
SHELL ["/bin/bash", "-c"]
RUN pip install --upgrade pip uv && \
    uv pip install --system -r <(uv pip compile pyproject.toml 2>/dev/null || echo "")

# Stage final
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar wheels del builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copiar código fuente
COPY pyproject.toml uv.lock* ./
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY .env.example ./.env

# Health check para Ollama
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

# Crear usuario no-root
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app
USER trader

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LLM_PROVIDER=local \
    LLM_BASE_URL=http://ollama:11434 \
    DEBUG_MODE=true

# Exponer puerto para Streamlit
EXPOSE 8501

# CMD por defecto: Dashboard
CMD ["streamlit", "run", "app/ui/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]