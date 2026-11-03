# ==============================================================================
# InsurTech AI Microservice - Production Multi-Stage Dockerfile
# Optimized for Ethiopian Ge'ez NLP, Whisper Speech & Hybrid RAG Retrieval
# Port: 5000 | Non-root User: appuser (UID 10001)
# ==============================================================================

# Stage 1: Build Dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Production Runtime
FROM python:3.11-slim AS runtime

LABEL maintainer="InsurTech Engineering <engineering@insurtech.et>"
LABEL description="Ethiopian InsurTech AI Microservice (Amharic/English RAG, Claims & Voice)"

# Install runtime dependencies:
# - ffmpeg: audio normalization & transcoding
# - libgomp1: OpenMP runtime for vector embeddings
# - tesseract-ocr + tesseract-ocr-amh: Amharic Ge'ez OCR fallback for policy scans
# - curl: container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-amh \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser .env.example /app/.env.example

# Set environment variables
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    HOST=0.0.0.0

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--proxy-headers"]
