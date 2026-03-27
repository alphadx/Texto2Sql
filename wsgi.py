"""WSGI entry point consumed by Gunicorn.

Usage:
    gunicorn --config gunicorn.conf.py wsgi:application
"""

from dotenv import load_dotenv

load_dotenv()

from app.main import create_app  # noqa: E402 (import after env load)

application = create_app()

if __name__ == "__main__":
    application.run()
