# Multi-stage Dockerfile for Emy AI Chief of Staff
# Base: python:3.11-slim for compatibility and minimal size
# NOTE: This Dockerfile is at emy/Dockerfile but uses repository root as build context
# (configured in Render service settings)

# ============================================================================
# Stage 1: Build
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from emy/ (build context is repository root)
COPY emy/requirements.txt .

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
# Note: ANTHROPIC_API_KEY and ANTHROPIC_MODEL are set via Render's Environment tab
# (not hardcoded here for security)
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

# Copy application code
# Build context is repository root, so this copies the entire repo
# Result: /app/emy/ directory exists with all modules
COPY --chown=emy:emy . .

# Switch to non-root user
USER emy

# Expose port and run server
EXPOSE 8000
CMD ["python", "/app/emy/entrypoint.py"]
