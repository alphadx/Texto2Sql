"""Gunicorn configuration file.

Override any value via environment variables, e.g.
    GUNICORN_CMD_ARGS="--workers 8"
"""

import multiprocessing

bind = "0.0.0.0:5000"

# A safe default: 2 × CPU cores + 1
workers = multiprocessing.cpu_count() * 2 + 1

worker_class = "sync"

# Long timeout to allow LLM calls to complete
timeout = 120

# Log to stdout/stderr (captured by Docker / systemd)
accesslog = "-"
errorlog = "-"
loglevel = "info"
