"""Study management routes."""
from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.core import get_db
from app.core.auth import current_user_id, login_required
from app.models.study import StudyPlanner

study_bp = Blueprint("study", __name__)


@study_bp.route("/")
@login_required
def index():
    planner = StudyPlanner(get_db(), current_user_id())
    return render_template(
        "study.html",
        subjects=planner.list_subjects(),
        progress=planner.progress_per_subject(),
        sessions=planner.recent_sessions(),
        plan=planner.generate_plan(7),
        weekly_minutes=planner.total_minutes_this_week(),
    )


@study_bp.route("/subject", methods=["POST"])
@login_required
def add_subject():
    planner = StudyPlanner(get_db(), current_user_id())
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Subject name is required.", "error")
        return redirect(url_for("study.index"))
    planner.add_subject(
        name=name,
        target_hours=float(request.form.get("target_hours", 10) or 10),
        exam_date=request.form.get("exam_date") or None,
    )
    flash(f"Subject \"{name}\" added.", "success")
    return redirect(url_for("study.index"))


@study_bp.route("/subject/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id: int):
    StudyPlanner(get_db(), current_user_id()).delete_subject(subject_id)
    return redirect(url_for("study.index"))


@study_bp.route("/session", methods=["POST"])
@login_required
def log_session():
    planner = StudyPlanner(get_db(), current_user_id())
    data = request.get_json(silent=True) or request.form
    duration = int(data.get("duration_min", 25))
    subject_id = data.get("subject_id")
    subject_id = int(subject_id) if subject_id else None
    focus = int(data.get("focus_score", 7))
    notes = (data.get("notes") or "").strip()
    planner.log_session(subject_id, duration, focus, notes)
    if request.is_json:
        return jsonify({"ok": True})
    flash("Study session logged.", "success")
    return redirect(url_for("study.index"))
