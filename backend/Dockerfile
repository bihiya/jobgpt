FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PLAYWRIGHT_NO_SANDBOX=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

RUN mkdir -p /tmp/jobpilot/uploads /tmp/jobpilot/screenshots /tmp/jobpilot/reports

EXPOSE 8000

# Production: Gunicorn + Uvicorn workers (override with uvicorn for local reload)
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
