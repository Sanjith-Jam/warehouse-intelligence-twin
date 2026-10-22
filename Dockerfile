# Production Dockerfile for Warehouse Intelligence Twin FastAPI Backend
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr and writing pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    UPLOAD_STORAGE_DIR=/app/backend/app/data/uploads

WORKDIR /app

# Install system dependencies (build-essential needed if wheels require compiling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application and contracts
COPY backend/ ./backend/
COPY contracts/ ./contracts/

# Ensure writable upload storage directory exists for dynamic datasets
RUN mkdir -p /app/backend/app/data/uploads && chmod 777 /app/backend/app/data/uploads

# Expose default HTTP port
EXPOSE 8000

# Health check using FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run Uvicorn ASGI server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
