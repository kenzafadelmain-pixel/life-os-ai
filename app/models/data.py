"""
Smaller domain models — Mood entries, productivity logs, files, AI memory.

Each class is a focused repository for one table; the heavier analytics live
in `app/core/analyzer.py` and `app/core/predictor.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.database import DatabaseManager


# ---------------------------------------------------------------- mood
@dataclass
class MoodEntry:
    id: int
    journal: str
    sentiment: float
    emotion: str
    stress_level: int
    motivation: int
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "MoodEntry":
        return cls(
            id=row["id"],
            journal=row["journal"],
            sentiment=row["sentiment"],
            emotion=row["emotion"],
            stress_level=row["stress_level"],
            motivation=row["motivation"],
            created_at=row["created_at"],
        )


class MoodRepository:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    def add(
        self,
        journal: str,
        sentiment: float,
        emotion: str,
        stress: int,
        motivation: int,
    ) -> int:
        return self.db.execute(
            """INSERT INTO mood_entries
               (user_id, journal, sentiment, emotion, stress_level, motivation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.user_id, journal.strip(), sentiment, emotion, stress, motivation),
        )

    def recent(self, limit: int = 30) -> list[MoodEntry]:
        rows = self.db.query(
            """SELECT * FROM mood_entries WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (self.user_id, limit),
        )
        return [MoodEntry.from_row(r) for r in rows]

    def weekly_average(self) -> dict:
        row = self.db.query_one(
            """SELECT AVG(sentiment) AS s, AVG(stress_level) AS st,
                      AVG(motivation) AS m, COUNT(*) AS n
               FROM mood_entries
               WHERE user_id = ? AND created_at >= date('now','-6 days')""",
            (self.user_id,),
        )
        if not row or not row["n"]:
            return {"sentiment": 0.0, "stress": 5, "motivation": 5, "entries": 0}
        return {
            "sentiment": round(row["s"] or 0, 2),
            "stress": round(row["st"] or 5, 1),
            "motivation": round(row["m"] or 5, 1),
            "entries": row["n"],
        }

    def trend(self, days: int = 14) -> list[dict]:
        rows = self.db.query(
            """SELECT DATE(created_at) AS d,
                      AVG(sentiment) AS s,
                      AVG(stress_level) AS st,
                      AVG(motivation) AS m
               FROM mood_entries
               WHERE user_id = ? AND created_at >= date('now', ?)
               GROUP BY DATE(created_at) ORDER BY d""",
            (self.user_id, f"-{days - 1} days"),
        )
        return [
            {
                "date": r["d"],
                "sentiment": round(r["s"] or 0, 2),
                "stress": round(r["st"] or 5, 1),
                "motivation": round(r["m"] or 5, 1),
            }
            for r in rows
        ]


# ---------------------------------------------------------- productivity
class ProductivityLogRepository:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    def upsert_today(
        self,
        focus_minutes: int,
        deep_work_min: int,
        breaks_min: int,
        sleep_hours: float,
        productivity: int,
    ) -> None:
        self.db.execute(
            """INSERT INTO productivity_logs
               (user_id, log_date, focus_minutes, deep_work_min, breaks_min,
                sleep_hours, productivity)
               VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, log_date) DO UPDATE SET
                 focus_minutes = excluded.focus_minutes,
                 deep_work_min = excluded.deep_work_min,
                 breaks_min    = excluded.breaks_min,
                 sleep_hours   = excluded.sleep_hours,
                 productivity  = excluded.productivity""",
            (self.user_id, focus_minutes, deep_work_min, breaks_min,
             sleep_hours, productivity),
        )

    def heatmap(self, days: int = 35) -> list[dict]:
        rows = self.db.query(
            """SELECT log_date, productivity FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now', ?)
               ORDER BY log_date""",
            (self.user_id, f"-{days - 1} days"),
        )
        return [{"date": r["log_date"], "value": r["productivity"]} for r in rows]

    def latest(self, limit: int = 30) -> list[dict]:
        rows = self.db.query(
            """SELECT * FROM productivity_logs WHERE user_id = ?
               ORDER BY log_date DESC LIMIT ?""",
            (self.user_id, limit),
        )
        return [dict(r) for r in rows]

    def weekly_avg(self) -> int:
        row = self.db.query_one(
            """SELECT AVG(productivity) AS p FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now','-6 days')""",
            (self.user_id,),
        )
        if not row or row["p"] is None:
            return 0
        return int(round(row["p"]))


# ---------------------------------------------------------------- files
@dataclass
class StoredFile:
    id: int
    filename: str
    original_name: str
    file_type: str
    summary: str
    size_bytes: int
    uploaded_at: datetime

    @classmethod
    def from_row(cls, row) -> "StoredFile":
        return cls(
            id=row["id"],
            filename=row["filename"],
            original_name=row["original_name"],
            file_type=row["file_type"],
            summary=row["summary"] or "",
            size_bytes=row["size_bytes"],
            uploaded_at=row["uploaded_at"],
        )


class FileRepository:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    def add(
        self,
        filename: str,
        original_name: str,
        file_type: str,
        size_bytes: int,
        summary: str = "",
    ) -> int:
        return self.db.execute(
            """INSERT INTO files
               (user_id, filename, original_name, file_type, summary, size_bytes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.user_id, filename, original_name, file_type, summary, size_bytes),
        )

    def list(self) -> list[StoredFile]:
        rows = self.db.query(
            "SELECT * FROM files WHERE user_id = ? ORDER BY uploaded_at DESC",
            (self.user_id,),
        )
        return [StoredFile.from_row(r) for r in rows]

    def get(self, file_id: int) -> Optional[StoredFile]:
        row = self.db.query_one(
            "SELECT * FROM files WHERE id = ? AND user_id = ?",
            (file_id, self.user_id),
        )
        return StoredFile.from_row(row) if row else None

    def update_summary(self, file_id: int, summary: str) -> None:
        self.db.execute(
            "UPDATE files SET summary = ? WHERE id = ? AND user_id = ?",
            (summary, file_id, self.user_id),
        )

    def delete(self, file_id: int) -> None:
        self.db.execute(
            "DELETE FROM files WHERE id = ? AND user_id = ?",
            (file_id, self.user_id),
        )


# ---------------------------------------------------------------- memory
class MemoryRepository:
    """Long-term key/value memory the AI assistant draws from."""

    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    def remember(self, key: str, value: str) -> None:
        self.db.execute(
            """INSERT INTO memories (user_id, key, value) VALUES (?, ?, ?)
               ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value""",
            (self.user_id, key.strip(), value.strip()),
        )

    def all(self) -> list[dict]:
        rows = self.db.query(
            "SELECT key, value, created_at FROM memories WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_id,),
        )
        return [dict(r) for r in rows]

    def context_string(self, limit: int = 8) -> str:
        rows = self.db.query(
            "SELECT key, value FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (self.user_id, limit),
        )
        if not rows:
            return ""
        return "\n".join(f"- {r['key']}: {r['value']}" for r in rows)

    def forget(self, key: str) -> None:
        self.db.execute(
            "DELETE FROM memories WHERE user_id = ? AND key = ?",
            (self.user_id, key),
        )
