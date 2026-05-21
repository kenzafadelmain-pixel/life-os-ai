"""Public routes: landing page, marketing pages, healthcheck."""
from flask import Blueprint, redirect, render_template, session, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    """The marketing / landing page. Logged-in users go straight to dashboard."""
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    return render_template("landing.html")


@main_bp.route("/health")
def health():
    return {"status": "ok"}
