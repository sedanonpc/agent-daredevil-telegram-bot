# ===========================================
# Agent Daredevil - Production Dockerfile for Railway
# ===========================================
# Optimized multi-stage build for production deployment

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PORT=8000

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    # For ChromaDB and vector operations
    libgomp1 \
    libgcc-s1 \
    # For voice processing
    ffmpeg \
    # For web scraping and HTTP requests
    curl \
    wget \
    ca-certificates \
    # For file operations and system utilities
    file \
    procps \
    # For audio processing
    libasound2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 daredevil && \
    mkdir -p /app /app/data /app/logs /app/temp_voice_files && \
    chown -R daredevil:daredevil /app

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=daredevil:daredevil . .

# Create necessary directories and set permissions
RUN mkdir -p /app/chroma_db /app/temp_voice_files /app/logs /app/data && \
    chown -R daredevil:daredevil /app && \
    chmod -R 755 /app

# Switch to non-root user
USER daredevil

# Health check for Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/health', timeout=5)" || exit 1

# Expose port for Railway
EXPOSE $PORT

# Default command - can be overridden by Railway
CMD ["python", "launch_web_messenger.py"]
