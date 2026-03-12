# Multi-stage Dockerfile for Emy AI Chief of Staff
# Base: python:3.11-slim for compatibility and minimal size

# ============================================================================
# Stage 1: Build
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv --always-copy /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EMY_API_URL="http://localhost:8000" \
    EMY_LOG_LEVEL="INFO"

# Create non-root user
RUN useradd -m -u 1000 emy && \
    mkdir -p /app /data && \
    chown -R emy:emy /app /data /opt/venv

# Copy application code
COPY --chown=emy:emy . .

# Switch to non-root user
USER emy

# Create data directory for database
RUN mkdir -p emy/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()"

# Default command: run API gateway server
# Can be overridden to run CLI: docker run emy python emy.py ask "query"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "gateway.api:app", "--host", "0.0.0.0", "--port", "8000"]
