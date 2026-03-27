"""Gunicorn configuration file for ASGI/FastAPI."""

import multiprocessing

bind = "0.0.0.0:5000"

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

timeout = 120

accesslog = "-"
errorlog = "-"
loglevel = "info"
