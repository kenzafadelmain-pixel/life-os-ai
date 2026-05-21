"""Small helpers shared by route blueprints."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import flash, redirect, session, url_for


def login_required(fn: Callable):
    """Redirect anonymous users to /auth/login."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper


def current_user_id() -> int:
    return int(session["user_id"])


ALLOWED_EXT = {"pdf", "txt", "md", "docx", "png", "jpg", "jpeg"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
