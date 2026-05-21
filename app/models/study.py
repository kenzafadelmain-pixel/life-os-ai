"""
Study management — subjects, sessions, Pomodoro stats.

`StudyPlanner` generates AI-shaped study schedules from the user's subjects,
target hours and exam dates. The recommendation logic is deterministic and
local (no network needed) so it works in any environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database import DatabaseManager


@dataclass
class Subject:
    id: int
    name: str
    target_hours: float
    exam_date: Optional[date]
    color: str

    @classmethod
    def from_row(cls, row) -> "Subject":
        return cls(
            id=row["id"],
            name=row["name"],
            target_hours=row["target_hours"],
            exam_date=row["exam_date"],
            color=row["color"],
        )


@dataclass
class StudySession:
    id: int
    subject_id: Optional[int]
    subject_name: Optional[str]
    started_at: datetime
    duration_min: int
    focus_score: int
    notes: str

    @classmethod
    def from_row(cls, row) -> "StudySession":
        return cls(
            id=row["id"],
            subject_id=row["subject_id"],
            subject_name=row["subject_name"] if "subject_name" in row.keys() else None,
            started_at=row["started_at"],
            duration_min=row["duration_min"],
            focus_score=row["focus_score"],
            notes=row["notes"] or "",
        )


class StudyPlanner:
    """High-level operations for the study system."""

    PALETTE = ["#7c5cff", "#22d3ee", "#f472b6", "#facc15", "#34d399", "#fb7185"]

    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    # ----- subjects -------------------------------------------------------
    def list_subjects(self) -> list[Subject]:
        rows = self.db.query(
            "SELECT * FROM subjects WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_id,),
        )
        return [Subject.from_row(r) for r in rows]

    def add_subject(
        self,
        name: str,
        target_hours: float = 10,
        exam_date: Optional[str] = None,
    ) -> int:
        existing = self.list_subjects()
        color = self.PALETTE[len(existing) % len(self.PALETTE)]
        return self.db.execute(
            """INSERT INTO subjects (user_id, name, target_hours, exam_date, color)
               VALUES (?, ?, ?, ?, ?)""",
            (self.user_id, name.strip(), target_hours, exam_date or None, color),
        )

    def delete_subject(self, subject_id: int) -> None:
        self.db.execute(
            "DELETE FROM subjects WHERE id = ? AND user_id = ?",
            (subject_id, self.user_id),
        )

    # ----- sessions -------------------------------------------------------
    def log_session(
        self,
        subject_id: Optional[int],
        duration_min: int,
        focus_score: int = 7,
        notes: str = "",
    ) -> int:
        return self.db.execute(
            """INSERT INTO study_sessions
               (user_id, subject_id, duration_min, focus_score, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (self.user_id, subject_id, duration_min, focus_score, notes.strip()),
        )

    def recent_sessions(self, limit: int = 20) -> list[StudySession]:
        rows = self.db.query(
            """SELECT s.*, sub.name AS subject_name
               FROM study_sessions s
               LEFT JOIN subjects sub ON sub.id = s.subject_id
               WHERE s.user_id = ?
               ORDER BY s.started_at DESC LIMIT ?""",
            (self.user_id, limit),
        )
        return [StudySession.from_row(r) for r in rows]

    # ----- analytics ------------------------------------------------------
    def progress_per_subject(self) -> list[dict]:
        rows = self.db.query(
            """SELECT sub.id, sub.name, sub.target_hours, sub.color, sub.exam_date,
                      COALESCE(SUM(s.duration_min), 0) / 60.0 AS hours_done
               FROM subjects sub
               LEFT JOIN study_sessions s ON s.subject_id = sub.id
               WHERE sub.user_id = ?
               GROUP BY sub.id
               ORDER BY sub.created_at DESC""",
            (self.user_id,),
        )
        result = []
        for r in rows:
            target = r["target_hours"] or 1
            pct = min(100, round((r["hours_done"] / target) * 100))
            result.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "color": r["color"],
                    "exam_date": r["exam_date"],
                    "hours_done": round(r["hours_done"], 1),
                    "target_hours": r["target_hours"],
                    "progress_pct": pct,
                    "days_to_exam": _days_until(r["exam_date"]),
                }
            )
        return result

    def total_minutes_this_week(self) -> int:
        row = self.db.query_one(
            """SELECT COALESCE(SUM(duration_min), 0) AS m FROM study_sessions
               WHERE user_id = ? AND started_at >= date('now','-6 days')""",
            (self.user_id,),
        )
        return int(row["m"] if row else 0)

    # ----- AI planner -----------------------------------------------------
    def generate_plan(self, days: int = 7) -> list[dict]:
        """Return a `days`-long study plan, prioritising soonest exams."""
        subjects = self.list_subjects()
        if not subjects:
            return []

        # Score each subject — closer exams + higher remaining target = higher
        # priority. We then distribute 2 daily 50-minute Pomodoro blocks across
        # the top subjects.
        progress = {p["id"]: p for p in self.progress_per_subject()}
        ranked = sorted(
            subjects,
            key=lambda s: (
                _days_until(s.exam_date) if s.exam_date else 999,
                -(progress.get(s.id, {}).get("target_hours", 0)
                  - progress.get(s.id, {}).get("hours_done", 0)),
            ),
        )

        plan = []
        today = date.today()
        for i in range(days):
            day = today + timedelta(days=i)
            picks = [ranked[(i + j) % len(ranked)] for j in range(min(2, len(ranked)))]
            plan.append(
                {
                    "date": day.isoformat(),
                    "weekday": day.strftime("%A"),
                    "blocks": [
                        {"subject": s.name, "color": s.color, "minutes": 50}
                        for s in picks
                    ],
                }
            )
        return plan


def _days_until(value) -> Optional[int]:
    if not value:
        return None
    d = value if isinstance(value, date) else date.fromisoformat(str(value))
    return (d - date.today()).days
