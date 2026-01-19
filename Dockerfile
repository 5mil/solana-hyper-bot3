# Solana Hyper-Accumulation Bot v3.0 Dockerfile
# Production-grade Python 3.11 image

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY tools/ ./tools/

# Create data directory for metrics
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app

# Default entrypoint runs the live bot
# Can be overridden in CI/workflows with different commands
ENTRYPOINT ["python", "-m", "src.live_bot"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python tools/health_check.py || exit 1
