"""Web layer: the FastAPI application and its static client."""

from .app import app, create_app

__all__ = ["app", "create_app"]
