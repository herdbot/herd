# Herdbot Docker Image
# Multi-stage build for smaller final image

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /wheels -e .

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 herdbot && \
    chown -R herdbot:herdbot /app

USER herdbot

# Environment variables
ENV HERDBOT_API_HOST=0.0.0.0
ENV HERDBOT_API_PORT=8000
ENV HERDBOT_LOG_LEVEL=INFO

# Expose ports
EXPOSE 8000
EXPOSE 7447
EXPOSE 1883

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "-m", "uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
