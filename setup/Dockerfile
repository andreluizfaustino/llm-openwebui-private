FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition first for layer caching
COPY pyproject.toml .

# Upgrade pip and setuptools, then install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Copy application source and static assets
COPY src/ ./src/
COPY data/ ./data/
RUN mkdir -p ./static

# Ensure /data volume directory exists at runtime (mounted volume may be empty)
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
