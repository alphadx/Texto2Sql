"""Gunicorn configuration for FastAPI (ASGI via Uvicorn workers)."""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")

# Concurrency
cpu_count = multiprocessing.cpu_count()
default_workers = max(2, cpu_count)
workers = int(os.getenv("WEB_CONCURRENCY", str(default_workers)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("WORKER_CONNECTIONS", "1000"))

# Timeouts / lifecycle
keepalive = int(os.getenv("KEEPALIVE", "900"))
timeout = int(os.getenv("TIMEOUT", "900"))
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "900"))

# Reinicio preventivo para evitar crecimiento de memoria en cargas largas
max_requests = int(os.getenv("MAX_REQUESTS", "2000"))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", "200"))

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# FastAPI behind reverse proxy
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
