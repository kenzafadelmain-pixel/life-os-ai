"""Mood + journal routes."""
from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.core import get_db
from app.core.auth import current_user_id, login_required
from app.core.emotion import EmotionDetector
from app.models.data import MoodRepository

mood_bp = Blueprint("mood", __name__)


@mood_bp.route("/")
@login_required
def index():
    repo = MoodRepository(get_db(), current_user_id())
    return render_template(
        "mood.html",
        entries=repo.recent(30),
        weekly=repo.weekly_average(),
        trend=repo.trend(14),
    )


@mood_bp.route("/journal", methods=["POST"])
@login_required
def journal():
    repo = MoodRepository(get_db(), current_user_id())
    text = (request.form.get("journal") or "").strip()
    if not text:
        flash("Write a few words and I'll reflect them.", "info")
        return redirect(url_for("mood.index"))

    analysis = EmotionDetector().analyse(text)
    repo.add(
        journal=text,
        sentiment=analysis["sentiment"],
        emotion=analysis["emotion"],
        stress=analysis["stress"],
        motivation=analysis["motivation"],
    )
    flash(analysis["summary"], "success")
    return redirect(url_for("mood.index"))


@mood_bp.route("/analyse", methods=["POST"])
@login_required
def analyse_only():
    """Lightweight endpoint — returns analysis without persisting."""
    text = (request.json or {}).get("journal", "")
    return jsonify(EmotionDetector().analyse(text))
