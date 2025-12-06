"""Middleware package for FastAPI."""

from app.api.middleware.auth import verify_api_key

__all__ = ["verify_api_key"]
