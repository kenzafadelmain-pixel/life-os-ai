"""
Core package — domain logic + shared services.

The `get_db()` helper lazily attaches a DatabaseManager instance to the
current Flask app so route handlers and repository classes don't need to
construct one themselves.
"""
from __future__ import annotations

from flask import current_app, g

from .database import DatabaseManager


def get_db() -> DatabaseManager:
    """Return a per-request DatabaseManager bound to `g`."""
    if "db" not in g:
        g.db = DatabaseManager(current_app.config["DATABASE_PATH"])
    return g.db


__all__ = ["DatabaseManager", "get_db"]
