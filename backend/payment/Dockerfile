FROM python:3.10.16-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install curl for container healthcheck execution
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy into /app/payment to match python package namespace
COPY . /app/payment/

EXPOSE 8001

CMD ["uvicorn", "payment.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
