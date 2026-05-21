"""
ProductivityAnalyzer
====================

Reads the user's productivity_logs + mood + study + task data and produces:

* an overall productivity score (0..100)
* a list of human-readable insights ("You focus best between 4PM–7PM")
* a stress indicator
* a weekly trend dataset for the dashboard charts

The class is intentionally pure-Python with no numpy/pandas dependency so
it ships clean and small.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean
from typing import Optional

from app.core.database import DatabaseManager


class ProductivityAnalyzer:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    # ---------------------------------------------------- score
    def overall_score(self) -> int:
        """Composite score blending focus minutes, completion rate, mood."""
        focus = self.db.query_one(
            """SELECT AVG(productivity) AS p FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now','-6 days')""",
            (self.user_id,),
        )
        focus_score = (focus["p"] or 50) if focus else 50

        task = self.db.query_one(
            """SELECT
                 COALESCE(SUM(CASE WHEN status='done' THEN 1 END), 0) AS done,
                 COUNT(*) AS total
               FROM tasks WHERE user_id = ?""",
            (self.user_id,),
        )
        done = task["done"] if task else 0
        total = task["total"] if task else 0
        completion = (done / total) * 100 if total else 50

        mood = self.db.query_one(
            """SELECT AVG(motivation) AS m FROM mood_entries
               WHERE user_id = ? AND created_at >= date('now','-6 days')""",
            (self.user_id,),
        )
        mood_score = ((mood["m"] or 5) / 10.0) * 100

        return int(round(0.45 * focus_score + 0.35 * completion + 0.20 * mood_score))

    # ---------------------------------------------------- weekly trend
    def weekly_trend(self) -> list[dict]:
        """Productivity by day for the last 14 days."""
        rows = self.db.query(
            """SELECT log_date, productivity FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now','-13 days')
               ORDER BY log_date""",
            (self.user_id,),
        )
        return [{"date": r["log_date"], "value": r["productivity"]} for r in rows]

    # ---------------------------------------------------- recommendations
    def recommendations(self) -> list[dict]:
        """Generate natural-language insights from observed patterns."""
        notes: list[dict] = []

        # 1. Best window of day (by study sessions' average focus score)
        rows = self.db.query(
            """SELECT CAST(strftime('%H', started_at) AS INTEGER) AS h,
                      AVG(focus_score) AS f, COUNT(*) AS n
               FROM study_sessions WHERE user_id = ?
               GROUP BY h HAVING n >= 2 ORDER BY f DESC LIMIT 1""",
            (self.user_id,),
        )
        if rows:
            h = rows[0]["h"]
            window = f"{h:02d}:00–{(h + 3) % 24:02d}:00"
            notes.append({
                "icon": "⚡",
                "title": "Your peak focus window",
                "body":  f"Your highest focus scores cluster around **{window}**. "
                         f"Schedule deep work there and protect it.",
            })

        # 2. Late-night productivity drop
        late = self.db.query_one(
            """SELECT AVG(focus_score) AS late FROM study_sessions
               WHERE user_id = ? AND CAST(strftime('%H', started_at) AS INTEGER) >= 23""",
            (self.user_id,),
        )
        day = self.db.query_one(
            """SELECT AVG(focus_score) AS day FROM study_sessions
               WHERE user_id = ? AND CAST(strftime('%H', started_at) AS INTEGER) BETWEEN 9 AND 18""",
            (self.user_id,),
        )
        if late and day and late["late"] and day["day"] and late["late"] < day["day"] - 1.5:
            notes.append({
                "icon": "🌙",
                "title": "Diminishing returns after midnight",
                "body":  "Focus quality drops significantly after 11 PM. Move those sessions earlier "
                         "and reclaim sleep — net output goes *up*.",
            })

        # 3. Stress trend
        stress = self.db.query_one(
            """SELECT AVG(stress_level) AS s FROM mood_entries
               WHERE user_id = ? AND created_at >= date('now','-6 days')""",
            (self.user_id,),
        )
        if stress and stress["s"] and stress["s"] >= 7:
            notes.append({
                "icon": "🩺",
                "title": "Elevated stress signal",
                "body":  "Your average stress level this week is high. Cut one commitment, "
                         "schedule a real break, and reduce evening screens.",
            })

        # 4. Procrastination signal
        overdue = self.db.query_one(
            """SELECT COUNT(*) AS n FROM tasks
               WHERE user_id = ? AND status != 'done' AND due_date < DATE('now')""",
            (self.user_id,),
        )
        if overdue and overdue["n"] >= 3:
            notes.append({
                "icon": "⏰",
                "title": f"{overdue['n']} tasks overdue",
                "body":  "Pick the *smallest* overdue task and finish it in the next 25 minutes. "
                         "Momentum beats motivation.",
            })

        # 5. Sleep correlation
        sleep = self.db.query_one(
            """SELECT AVG(sleep_hours) AS h FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now','-6 days')""",
            (self.user_id,),
        )
        if sleep and sleep["h"] and sleep["h"] < 6.5:
            notes.append({
                "icon": "💤",
                "title": "Sleep debt building up",
                "body":  f"Average {sleep['h']:.1f}h/night this week. Productivity will plateau "
                         f"until you get a 7h+ stretch.",
            })

        # 6. Default cheer if nothing else triggered
        if not notes:
            notes.append({
                "icon": "✨",
                "title": "Steady week",
                "body":  "No red flags. Log a journal entry and a study session today to keep your trends rich.",
            })

        return notes

    # ---------------------------------------------------- activity feed
    def activity_feed(self, limit: int = 8) -> list[dict]:
        """Mixed recent activity across modules — for the dashboard timeline."""
        rows = self.db.query(
            """SELECT 'task'  AS kind, id, title AS label, created_at AS ts FROM tasks
                WHERE user_id = ?
               UNION ALL
               SELECT 'mood'  AS kind, id, emotion AS label, created_at AS ts FROM mood_entries
                WHERE user_id = ?
               UNION ALL
               SELECT 'study' AS kind, id, COALESCE(notes, 'Study session') AS label,
                      started_at AS ts FROM study_sessions WHERE user_id = ?
               ORDER BY ts DESC LIMIT ?""",
            (self.user_id, self.user_id, self.user_id, limit),
        )
        return [dict(r) for r in rows]
