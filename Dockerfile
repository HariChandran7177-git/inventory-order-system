# Reference Monorepo Python Container for Inventory Order System Backend Services
# Note: In production and Docker Compose orchestration, dedicated Dockerfiles are
# used per service (see backend/inventory/Dockerfile and backend/payment/Dockerfile).
FROM python:3.10.16-slim

WORKDIR /app

# Install curl for container healthcheck support
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Configure environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app

# Expose default API port
EXPOSE 8000

# Default command: Inventory API (can be overridden for payment or consumers)
CMD ["uvicorn", "inventory.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
