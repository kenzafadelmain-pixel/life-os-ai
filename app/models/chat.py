"""
Chat-session persistence — sessions, messages, transcript helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.database import DatabaseManager


@dataclass
class ChatSession:
    id: int
    title: str
    created_at: datetime


@dataclass
class ChatMessage:
    id: int
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    created_at: datetime


class ChatRepository:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    # ----- sessions -------------------------------------------------------
    def list_sessions(self) -> list[ChatSession]:
        rows = self.db.query(
            "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_id,),
        )
        return [ChatSession(r["id"], r["title"], r["created_at"]) for r in rows]

    def create_session(self, title: str = "New conversation") -> int:
        return self.db.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (self.user_id, title),
        )

    def rename_session(self, session_id: int, title: str) -> None:
        self.db.execute(
            "UPDATE chat_sessions SET title = ? WHERE id = ? AND user_id = ?",
            (title.strip()[:80], session_id, self.user_id),
        )

    def delete_session(self, session_id: int) -> None:
        self.db.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, self.user_id),
        )

    def get_session(self, session_id: int) -> Optional[ChatSession]:
        row = self.db.query_one(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, self.user_id),
        )
        if not row:
            return None
        return ChatSession(row["id"], row["title"], row["created_at"])

    # ----- messages -------------------------------------------------------
    def append_message(self, session_id: int, role: str, content: str) -> int:
        return self.db.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )

    def messages(self, session_id: int) -> list[ChatMessage]:
        rows = self.db.query(
            """SELECT id, role, content, created_at FROM chat_messages
               WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        )
        return [ChatMessage(r["id"], r["role"], r["content"], r["created_at"]) for r in rows]

    def transcript_for_api(self, session_id: int, limit: int = 20) -> list[dict]:
        """Latest `limit` messages formatted as {role, content} pairs."""
        rows = self.db.query(
            """SELECT role, content FROM chat_messages
               WHERE session_id = ? ORDER BY id DESC LIMIT ?""",
            (session_id, limit),
        )
        ordered = list(reversed([dict(r) for r in rows]))
        return ordered
