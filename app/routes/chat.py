"""AI Chat Assistant — sessions, history, message exchange."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from app.core import get_db
from app.core.auth import current_user_id, login_required
from app.core.chatbot import AIChatbot
from app.models.chat import ChatRepository
from app.models.data import MemoryRepository
from app.models.user import UserRepository

chat_bp = Blueprint("chat", __name__)


def _chatbot() -> AIChatbot:
    cfg = current_app.config
    return AIChatbot(
        openai_key=cfg["OPENAI_API_KEY"],
        gemini_key=cfg["GEMINI_API_KEY"],
        openai_model=cfg["AI_MODEL_OPENAI"],
        gemini_model=cfg["AI_MODEL_GEMINI"],
    )


@chat_bp.route("/", methods=["GET"])
@login_required
def index():
    db = get_db()
    uid = current_user_id()
    repo = ChatRepository(db, uid)
    sessions = repo.list_sessions()
    active_id = request.args.get("session", type=int)
    if not active_id and sessions:
        active_id = sessions[0].id
    messages = repo.messages(active_id) if active_id else []
    return render_template(
        "chat.html",
        sessions=sessions,
        active_id=active_id,
        messages=messages,
        provider=_chatbot().provider,
    )


@chat_bp.route("/new", methods=["POST"])
@login_required
def new_session():
    db = get_db()
    uid = current_user_id()
    repo = ChatRepository(db, uid)
    sid = repo.create_session()
    return redirect(url_for("chat.index", session=sid))


@chat_bp.route("/delete/<int:session_id>", methods=["POST"])
@login_required
def delete_session(session_id: int):
    repo = ChatRepository(get_db(), current_user_id())
    repo.delete_session(session_id)
    return redirect(url_for("chat.index"))


@chat_bp.route("/send", methods=["POST"])
@login_required
def send():
    """AJAX endpoint — receives a user message, returns the AI reply."""
    db = get_db()
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    user_text = (data.get("message") or "").strip()
    session_id = data.get("session_id")

    if not user_text:
        return jsonify({"error": "Message is empty."}), 400

    repo = ChatRepository(db, uid)

    # Create a session on the fly if none given.
    if not session_id:
        session_id = repo.create_session()
    else:
        if not repo.get_session(int(session_id)):
            session_id = repo.create_session()

    session_id = int(session_id)
    repo.append_message(session_id, "user", user_text)

    # Set or refine the session title from the first message.
    sess = repo.get_session(session_id)
    if sess and sess.title == "New conversation":
        repo.rename_session(session_id, _chatbot().summarise_title(user_text))

    user = UserRepository(db).get(uid)
    memory = MemoryRepository(db, uid).context_string()
    history = repo.transcript_for_api(session_id, limit=24)
    bot = _chatbot()
    answer = bot.reply(
        history,
        user_profile={"name": user.name if user else ""},
        memory_context=memory,
    )
    repo.append_message(session_id, "assistant", answer)

    return jsonify({
        "answer": answer,
        "session_id": session_id,
        "provider": bot.provider,
    })


@chat_bp.route("/rename/<int:session_id>", methods=["POST"])
@login_required
def rename(session_id: int):
    title = (request.form.get("title") or "").strip()
    if not title:
        return redirect(url_for("chat.index", session=session_id))
    ChatRepository(get_db(), current_user_id()).rename_session(session_id, title)
    return redirect(url_for("chat.index", session=session_id))
