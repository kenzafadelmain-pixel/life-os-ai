"""Dashboard — the command center of LIFE OS AI."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, render_template

from app.core import get_db
from app.core.analyzer import ProductivityAnalyzer
from app.core.auth import current_user_id, login_required
from app.core.predictor import PredictionEngine
from app.models.task import TaskManager
from app.models.data import MoodRepository, ProductivityLogRepository
from app.models.study import StudyPlanner
from app.models.user import UserRepository

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    db = get_db()
    uid = current_user_id()

    user = UserRepository(db).get(uid)
    tasks = TaskManager(db, uid)
    analyzer = ProductivityAnalyzer(db, uid)
    predictor = PredictionEngine(db, uid)
    mood = MoodRepository(db, uid)
    study = StudyPlanner(db, uid)
    prod_log = ProductivityLogRepository(db, uid)

    context = {
        "user": user,
        "score": analyzer.overall_score(),
        "task_stats": tasks.stats(),
        "next_tasks": tasks.next_up(5),
        "mood_summary": mood.weekly_average(),
        "weekly_trend": analyzer.weekly_trend(),
        "recommendations": analyzer.recommendations(),
        "activity": analyzer.activity_feed(),
        "prediction": predictor.summary_card(),
        "study_total_min": study.total_minutes_this_week(),
        "study_progress": study.progress_per_subject(),
        "heatmap": prod_log.heatmap(),
        "weekly_prod": prod_log.weekly_avg(),
    }
    return render_template("dashboard.html", **context)


@dashboard_bp.route("/api/snapshot")
@login_required
def api_snapshot():
    """JSON snapshot used to refresh the dashboard without a full reload."""
    db = get_db()
    uid = current_user_id()
    analyzer = ProductivityAnalyzer(db, uid)
    predictor = PredictionEngine(db, uid)
    return jsonify({
        "score": analyzer.overall_score(),
        "trend": analyzer.weekly_trend(),
        "recommendations": analyzer.recommendations(),
        "prediction": predictor.summary_card(),
    })
