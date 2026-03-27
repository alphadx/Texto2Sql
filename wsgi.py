"""ASGI entry point consumed by Gunicorn/Uvicorn.

Usage:
    gunicorn --config gunicorn.conf.py wsgi:app
"""

from dotenv import load_dotenv

load_dotenv()

from app.api import app  # noqa: E402 (import after env load)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("wsgi:app", host="0.0.0.0", port=5000)
