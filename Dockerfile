FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for chromadb and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Create persistent data directory
RUN mkdir -p /data/vector_wealth_db

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VECTOR_WEALTH_DB_PATH=/data/vector_wealth_db

# Expose port
EXPOSE 10000

# Run with gunicorn for production (Render uses port 10000 by default)
CMD ["gunicorn", "main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:10000", "--timeout", "120"]
