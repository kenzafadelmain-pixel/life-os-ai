"""Productivity routes — daily logs, heatmap, AI predictions."""
from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.core import get_db
from app.core.analyzer import ProductivityAnalyzer
from app.core.auth import current_user_id, login_required
from app.core.predictor import PredictionEngine
from app.models.data import ProductivityLogRepository

productivity_bp = Blueprint("productivity", __name__)


@productivity_bp.route("/")
@login_required
def index():
    db = get_db()
    uid = current_user_id()
    analyzer = ProductivityAnalyzer(db, uid)
    predictor = PredictionEngine(db, uid)
    repo = ProductivityLogRepository(db, uid)
    return render_template(
        "productivity.html",
        score=analyzer.overall_score(),
        trend=analyzer.weekly_trend(),
        recommendations=analyzer.recommendations(),
        prediction=predictor.summary_card(),
        logs=repo.latest(30),
        heatmap=repo.heatmap(),
        weekly_avg=repo.weekly_avg(),
    )


@productivity_bp.route("/log", methods=["POST"])
@login_required
def log():
    repo = ProductivityLogRepository(get_db(), current_user_id())
    try:
        repo.upsert_today(
            focus_minutes=int(request.form.get("focus_minutes", 0) or 0),
            deep_work_min=int(request.form.get("deep_work_min", 0) or 0),
            breaks_min=int(request.form.get("breaks_min", 0) or 0),
            sleep_hours=float(request.form.get("sleep_hours", 7) or 7),
            productivity=max(0, min(100, int(request.form.get("productivity", 50) or 50))),
        )
        flash("Today's productivity log saved.", "success")
    except (ValueError, TypeError):
        flash("Couldn't parse those numbers — try again.", "error")
    return redirect(url_for("productivity.index"))


@productivity_bp.route("/api/predict")
@login_required
def api_predict():
    engine = PredictionEngine(get_db(), current_user_id())
    return jsonify(engine.summary_card())
