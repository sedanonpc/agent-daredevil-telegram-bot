# ===========================================
# Agent Daredevil Telegram Bot - Production Dockerfile
# ===========================================
# Multi-stage build for optimized production image

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    # For ChromaDB and vector operations
    libgomp1 \
    # For voice processing
    ffmpeg \
    # For web scraping
    curl \
    wget \
    # For file operations
    file \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash daredevil && \
    mkdir -p /app && \
    chown -R daredevil:daredevil /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=daredevil:daredevil . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/chroma_db /app/temp_voice_files /app/logs && \
    chown -R daredevil:daredevil /app

# Switch to non-root user
USER daredevil

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import telethon; print('Health check passed')" || exit 1

# Expose port (if needed for web services)
EXPOSE 8000

# Health check endpoint for Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden by Railway)
CMD ["python", "telegram_bot_rag.py"]
