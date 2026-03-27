"""Compatibility module for the ASGI application factory."""

from app.api import app, create_app

__all__ = ["app", "create_app"]
