"""Gunicorn + Uvicorn worker configuration for production."""

import multiprocessing
import os

bind = os.getenv("BIND", "0.0.0.0:8000")
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
threads = 1
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
keepalive = 5  # HTTP Keep-Alive
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
preload_app = True
