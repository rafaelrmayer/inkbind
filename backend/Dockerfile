FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/storage \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
