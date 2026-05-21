"""Settings, profile, AI memory, automation engine."""
from __future__ import annotations

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template,
                   request, session, url_for)

from app.core import get_db
from app.core.auth import current_user_id, login_required
from app.core.services import build_default_automations
from app.models.data import MemoryRepository
from app.models.user import UserRepository

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
@login_required
def index():
    db = get_db()
    uid = current_user_id()
    user = UserRepository(db).get(uid)
    memory = MemoryRepository(db, uid).all()
    settings_row = db.query_one("SELECT * FROM settings WHERE user_id = ?", (uid,))
    automations = build_default_automations(current_app.config["UPLOAD_FOLDER"]).list()
    return render_template(
        "settings.html",
        user=user,
        memory=memory,
        settings=dict(settings_row) if settings_row else {},
        automations=automations,
    )


@settings_bp.route("/profile", methods=["POST"])
@login_required
def profile():
    uid = current_user_id()
    repo = UserRepository(get_db())
    name = (request.form.get("name") or "").strip()
    avatar = (request.form.get("avatar_seed") or "spark").strip() or "spark"
    if len(name) >= 2:
        repo.update_profile(uid, name, avatar)
        session["user_name"] = name
        flash("Profile updated.", "success")
    else:
        flash("Name must be at least 2 characters.", "error")
    return redirect(url_for("settings.index"))


@settings_bp.route("/password", methods=["POST"])
@login_required
def password():
    new = request.form.get("new_password") or ""
    confirm = request.form.get("confirm_password") or ""
    if len(new) < 8 or new != confirm:
        flash("Password must be 8+ characters and match the confirmation.", "error")
    else:
        UserRepository(get_db()).update_password(current_user_id(), new)
        flash("Password updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/preferences", methods=["POST"])
@login_required
def preferences():
    db = get_db()
    uid = current_user_id()
    db.execute(
        """UPDATE settings SET ai_provider = ?, theme = ?, notifications = ?, coach_tone = ?
           WHERE user_id = ?""",
        (
            request.form.get("ai_provider", "local"),
            request.form.get("theme", "aurora"),
            1 if request.form.get("notifications") == "on" else 0,
            request.form.get("coach_tone", "supportive"),
            uid,
        ),
    )
    flash("Preferences saved.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/memory", methods=["POST"])
@login_required
def memory_add():
    repo = MemoryRepository(get_db(), current_user_id())
    key = (request.form.get("key") or "").strip()
    value = (request.form.get("value") or "").strip()
    if key and value:
        repo.remember(key, value)
        flash("Memory saved — Aurora will use it in future chats.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/memory/forget", methods=["POST"])
@login_required
def memory_forget():
    key = request.form.get("key", "")
    if key:
        MemoryRepository(get_db(), current_user_id()).forget(key)
    return redirect(url_for("settings.index"))


@settings_bp.route("/automation/<key>", methods=["POST"])
@login_required
def run_automation(key: str):
    engine = build_default_automations(current_app.config["UPLOAD_FOLDER"])
    try:
        message = engine.run(key, current_user_id(), get_db())
        return jsonify({"ok": True, "message": message})
    except KeyError:
        return jsonify({"ok": False, "error": "Unknown automation"}), 404
