"""Task manager routes."""
from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.core import get_db
from app.core.auth import current_user_id, login_required
from app.models.task import TaskManager, PRIORITY_LABELS

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
@login_required
def index():
    mgr = TaskManager(get_db(), current_user_id())
    return render_template(
        "tasks.html",
        board=mgr.board(),
        stats=mgr.stats(),
        priority_labels=PRIORITY_LABELS,
    )


@tasks_bp.route("/create", methods=["POST"])
@login_required
def create():
    mgr = TaskManager(get_db(), current_user_id())
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Task title can't be empty.", "error")
        return redirect(url_for("tasks.index"))
    mgr.create(
        title=title,
        description=request.form.get("description", ""),
        priority=int(request.form.get("priority", 2)),
        due_date=request.form.get("due_date") or None,
    )
    flash("Task added to your board.", "success")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def set_status(task_id: int):
    mgr = TaskManager(get_db(), current_user_id())
    status = (request.json or {}).get("status") if request.is_json else request.form.get("status")
    try:
        mgr.set_status(task_id, status)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if request.is_json:
        return jsonify({"ok": True, "stats": mgr.stats()})
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id: int):
    TaskManager(get_db(), current_user_id()).delete(task_id)
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/edit", methods=["POST"])
@login_required
def edit(task_id: int):
    mgr = TaskManager(get_db(), current_user_id())
    fields = {}
    for k in ("title", "description"):
        v = request.form.get(k)
        if v is not None:
            fields[k] = v.strip()
    if request.form.get("priority"):
        fields["priority"] = int(request.form["priority"])
    if request.form.get("due_date") is not None:
        fields["due_date"] = request.form["due_date"] or None
    mgr.update(task_id, **fields)
    return redirect(url_for("tasks.index"))
