"""
PredictionEngine
================

The headline AI feature. From recent logs it computes:

* **burnout_risk**         — 0..100, based on stress, sleep, focus minutes.
* **productivity_forecast**— next-7-day projection using a simple weighted
                              linear regression over the last 14 days.
* **study_outlook**        — projected completion % per subject by exam date.
* **task_completion_prob** — probability the user will complete their open
                              tasks on time, based on historical completion
                              cadence.
* **emotional_stability**  — variance of sentiment + stress over 2 weeks.

Each method returns plain dicts ready for JSON serialisation.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Optional

from app.core.database import DatabaseManager


def _safe_avg(values):
    return mean(values) if values else 0.0


class PredictionEngine:
    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------- burnout
    def burnout_risk(self) -> dict:
        stress_row = self.db.query_one(
            """SELECT AVG(stress_level) AS s, AVG(motivation) AS m
               FROM mood_entries WHERE user_id = ?
               AND created_at >= date('now','-13 days')""",
            (self.user_id,),
        )
        prod_row = self.db.query_one(
            """SELECT AVG(focus_minutes) AS f, AVG(sleep_hours) AS sl,
                      AVG(productivity) AS p
               FROM productivity_logs WHERE user_id = ?
               AND log_date >= date('now','-13 days')""",
            (self.user_id,),
        )
        s = (stress_row["s"] if stress_row and stress_row["s"] else 5)
        m = (stress_row["m"] if stress_row and stress_row["m"] else 5)
        f = (prod_row["f"]  if prod_row and prod_row["f"]  else 180)
        sl = (prod_row["sl"] if prod_row and prod_row["sl"] else 7)

        # Risk goes UP with stress + focus minutes, DOWN with motivation + sleep.
        risk = 0.0
        risk += (s - 5) * 8           # stress contribution
        risk -= (m - 5) * 4           # motivation buffer
        risk += max(0, f - 300) * 0.1 # over-extension
        risk += max(0, 7 - sl) * 9    # sleep debt

        risk = max(0, min(100, int(round(50 + risk))))

        if risk < 30:
            label, color = "Healthy", "#34d399"
            msg = "You're in a sustainable rhythm. Keep your recovery habits."
        elif risk < 60:
            label, color = "Watch", "#facc15"
            msg = "Mild build-up — schedule one full off-evening this week."
        elif risk < 80:
            label, color = "Elevated", "#fb923c"
            msg = "You're trending toward overload. Cut one obligation and prioritise sleep."
        else:
            label, color = "High", "#fb7185"
            msg = "Burnout risk is high. Take a real recovery day in the next 48 hours."

        return {
            "risk": risk, "label": label, "color": color, "message": msg,
            "inputs": {
                "avg_stress": round(s, 1),
                "avg_motivation": round(m, 1),
                "avg_focus_min": round(f),
                "avg_sleep_hours": round(sl, 1),
            },
        }

    # ------------------------------------------------- forecast
    def productivity_forecast(self) -> dict:
        """Naive linear projection over the next 7 days."""
        rows = self.db.query(
            """SELECT log_date, productivity FROM productivity_logs
               WHERE user_id = ? AND log_date >= date('now','-13 days')
               ORDER BY log_date""",
            (self.user_id,),
        )
        if len(rows) < 3:
            return {"history": [], "forecast": [], "trend": "stable",
                    "message": "Need a few more days of logs to forecast."}

        xs = list(range(len(rows)))
        ys = [r["productivity"] for r in rows]

        # OLS slope/intercept
        x_mean, y_mean = mean(xs), mean(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den = sum((x - x_mean) ** 2 for x in xs) or 1
        slope = num / den
        intercept = y_mean - slope * x_mean

        forecast = []
        today = date.today()
        for i in range(1, 8):
            value = max(0, min(100, intercept + slope * (len(rows) - 1 + i)))
            forecast.append({
                "date": (today + timedelta(days=i)).isoformat(),
                "value": round(value, 1),
            })

        if slope > 0.7:
            trend = "rising"
            msg = "Trajectory is climbing — keep your current routine and ride it."
        elif slope < -0.7:
            trend = "falling"
            msg = "If you continue this routine, productivity will dip next week. "\
                  "Adjust one habit (sleep, focus block, breaks)."
        else:
            trend = "stable"
            msg = "Productivity holding steady. A small habit change could unlock another 10%."

        return {
            "history": [{"date": r["log_date"], "value": r["productivity"]} for r in rows],
            "forecast": forecast,
            "trend": trend,
            "slope": round(slope, 2),
            "message": msg,
        }

    # ------------------------------------------------- task probability
    def task_completion_probability(self) -> dict:
        """Probability of finishing all open tasks before their due dates."""
        stats = self.db.query_one(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
               FROM tasks WHERE user_id = ?""",
            (self.user_id,),
        )
        if not stats or not stats["total"]:
            return {"probability": 50, "label": "Unknown", "message": "Add a few tasks first."}

        rate = (stats["done"] / stats["total"]) if stats["total"] else 0
        # Open tasks waiting:
        open_with_deadlines = self.db.query_one(
            """SELECT COUNT(*) AS n FROM tasks
               WHERE user_id = ? AND status != 'done' AND due_date IS NOT NULL""",
            (self.user_id,),
        )
        open_n = open_with_deadlines["n"] if open_with_deadlines else 0

        prob = 100 * (rate ** max(1, open_n / 3))
        prob = int(round(max(5, min(95, prob))))

        if prob >= 75:
            label, msg = "On track", "Strong completion history — keep the cadence."
        elif prob >= 50:
            label, msg = "Manageable", "Trim one task or extend a deadline to lock in this score."
        else:
            label, msg = "At risk", "Cut scope. Pick the top 3 must-finish tasks for this week."

        return {"probability": prob, "label": label, "message": msg,
                "open_with_deadlines": open_n,
                "historical_completion": round(rate * 100, 1)}

    # ------------------------------------------------- emotional stability
    def emotional_stability(self) -> dict:
        rows = self.db.query(
            """SELECT sentiment, stress_level FROM mood_entries
               WHERE user_id = ? AND created_at >= date('now','-13 days')""",
            (self.user_id,),
        )
        if len(rows) < 3:
            return {"score": 50, "label": "Not enough data",
                    "message": "Log a few more journal entries for a stability read."}

        s = [r["sentiment"] for r in rows]
        st = [r["stress_level"] for r in rows]
        sd = pstdev(s) if len(s) > 1 else 0
        sd_st = pstdev(st) if len(st) > 1 else 0
        # Lower variance + higher mean sentiment ⇒ higher stability
        score = int(round(100 - (sd * 50) - (sd_st * 5) + (mean(s) * 20)))
        score = max(0, min(100, score))
        if score >= 70: label, msg = "Steady", "Your emotional baseline is steady."
        elif score >= 40: label, msg = "Variable", "Some swings — track triggers in your journal."
        else: label, msg = "Volatile", "Strong swings. Anchor with daily routines and reach out for support."
        return {"score": score, "label": label, "message": msg}

    # ------------------------------------------------- summary card
    def summary_card(self) -> dict:
        return {
            "burnout": self.burnout_risk(),
            "forecast": self.productivity_forecast(),
            "tasks": self.task_completion_probability(),
            "emotion": self.emotional_stability(),
        }
