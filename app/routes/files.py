"""Files & notes routes — upload, summarise, flashcards."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template,
                   request, send_from_directory, url_for)
from werkzeug.utils import secure_filename

from app.core import get_db
from app.core.auth import allowed_file, current_user_id, login_required
from app.core.services import FileSummariser
from app.models.data import FileRepository

files_bp = Blueprint("files", __name__)


@files_bp.route("/")
@login_required
def index():
    repo = FileRepository(get_db(), current_user_id())
    return render_template("files.html", files=repo.list())


@files_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Pick a file first.", "error")
        return redirect(url_for("files.index"))
    if not allowed_file(file.filename):
        flash("That file type isn't supported.", "error")
        return redirect(url_for("files.index"))

    safe_name = secure_filename(file.filename)
    unique_prefix = secrets.token_hex(4)
    stored_name = f"{unique_prefix}_{safe_name}"
    save_path = Path(current_app.config["UPLOAD_FOLDER"]) / stored_name
    file.save(save_path)
    size = save_path.stat().st_size
    ext = save_path.suffix.lstrip(".").lower()

    # Generate a summary when possible.
    summariser = FileSummariser()
    text = summariser.extract_text(str(save_path))
    summary = summariser.summarise(text, max_sentences=5) if text else ""

    repo = FileRepository(get_db(), current_user_id())
    repo.add(
        filename=stored_name,
        original_name=safe_name,
        file_type=ext,
        size_bytes=size,
        summary=summary,
    )
    flash("File uploaded and summarised.", "success")
    return redirect(url_for("files.index"))


@files_bp.route("/<int:file_id>")
@login_required
def download(file_id: int):
    repo = FileRepository(get_db(), current_user_id())
    rec = repo.get(file_id)
    if not rec:
        flash("File not found.", "error")
        return redirect(url_for("files.index"))
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        rec.filename,
        as_attachment=True,
        download_name=rec.original_name,
    )


@files_bp.route("/<int:file_id>/delete", methods=["POST"])
@login_required
def delete(file_id: int):
    repo = FileRepository(get_db(), current_user_id())
    rec = repo.get(file_id)
    if rec:
        try:
            (Path(current_app.config["UPLOAD_FOLDER"]) / rec.filename).unlink(missing_ok=True)
        except OSError:
            pass
        repo.delete(file_id)
    return redirect(url_for("files.index"))


@files_bp.route("/<int:file_id>/flashcards")
@login_required
def flashcards(file_id: int):
    repo = FileRepository(get_db(), current_user_id())
    rec = repo.get(file_id)
    if not rec:
        return jsonify({"error": "not found"}), 404
    path = Path(current_app.config["UPLOAD_FOLDER"]) / rec.filename
    summariser = FileSummariser()
    text = summariser.extract_text(str(path))
    return jsonify({"cards": summariser.flashcards(text, n=6)})


@files_bp.route("/<int:file_id>/resummarise", methods=["POST"])
@login_required
def resummarise(file_id: int):
    repo = FileRepository(get_db(), current_user_id())
    rec = repo.get(file_id)
    if not rec:
        return jsonify({"error": "not found"}), 404
    path = Path(current_app.config["UPLOAD_FOLDER"]) / rec.filename
    summariser = FileSummariser()
    text = summariser.extract_text(str(path))
    new_summary = summariser.summarise(text, max_sentences=6)
    repo.update_summary(file_id, new_summary)
    return jsonify({"summary": new_summary})
