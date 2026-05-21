"""Voice assistant routes.

The browser handles speech-to-text via the Web Speech API; we only need to
synthesise the AI's reply server-side via gTTS, when available.
"""
from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request

from app.core.auth import login_required
from app.core.services import VoiceAssistant

voice_bp = Blueprint("voice", __name__)


@voice_bp.route("/speak", methods=["POST"])
@login_required
def speak():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Empty text"}), 400

    va = VoiceAssistant(lang=current_app.config.get("TTS_LANG", "en"))
    audio = va.synthesise(text)
    if not audio:
        return jsonify({"error": "TTS unavailable"}), 503
    return Response(audio, mimetype="audio/mpeg")
