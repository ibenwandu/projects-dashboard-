# Multi-stage Dockerfile for Emy AI Chief of Staff
# Build context: emy/ directory (Render setting)
# When build context is emy/:
#   COPY . . copies contents of emy/ to /app/
#   Result: /app/gateway/, /app/agents/, etc. (NOT /app/emy/gateway/)

# ============================================================================
# Stage 1: Build
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (build context is emy/, so this is emy/requirements.txt)
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
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
    PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EMY_API_URL="${EMY_API_URL:-http://localhost:8000}" \
    EMY_LOG_LEVEL="${EMY_LOG_LEVEL:-INFO}"

# Create non-root user
RUN useradd -m -u 1000 emy && \
    mkdir -p /app /data && \
    chown -R emy:emy /app /data /opt/venv

# Copy application code (from emy/ build context to /app/)
# Result: /app/gateway/, /app/agents/, etc.
COPY --chown=emy:emy . .

# Switch to non-root user
USER emy

# Expose port and run server
EXPOSE 8000
CMD ["python", "/app/entrypoint.py"]
