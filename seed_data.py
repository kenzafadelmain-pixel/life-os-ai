"""
seed_data.py
============

Populates LIFE OS AI with a fully-furnished demo account.

Run once after install:
    python seed_data.py

Creates:
    * a demo user (demo@lifeos.ai / aurora-demo-2026)
    * 6 tasks across all statuses
    * 4 subjects with realistic exam dates and varied progress
    * 14 days of productivity logs + ~20 study sessions
    * 8 mood journal entries with varied emotion
    * 3 long-term memories Aurora can quote in chat

Idempotent: re-running won't duplicate the demo user.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from app import create_app
from app.core.database import DatabaseManager
from app.core.emotion import EmotionDetector
from app.models.chat import ChatRepository
from app.models.data import (FileRepository, MemoryRepository,
                              MoodRepository, ProductivityLogRepository)
from app.models.study import StudyPlanner
from app.models.task import TaskManager
from app.models.user import UserRepository


DEMO_EMAIL = "demo@lifeos.ai"
DEMO_PASSWORD = "aurora-demo-2026"

JOURNAL_ENTRIES = [
    "Hit a great flow state today. Knocked out two big tasks and felt focused for hours. "
    "Energy is high, sleep was solid. Want to ride this wave tomorrow.",
    "Feeling overwhelmed. Three deadlines stacked and I keep context-switching. "
    "Need to cut something or this week is going to break me.",
    "Calm morning. Did a long walk before opening the laptop and it changed everything. "
    "I'm going to make this a daily ritual.",
    "Tired. Couldn't sleep last night, brain wouldn't stop spinning. "
    "Productivity is going to be lower today and I have to be okay with that.",
    "Really excited about the new project. So motivated to start that I can barely sit still. "
    "Trying to channel it into a clear plan first.",
    "Anxious about the upcoming exam. Studied for 4 hours but it doesn't feel like enough. "
    "I keep checking the date on my phone.",
    "Steady day. Nothing dramatic — finished what I planned, ate well, slept early. "
    "These are the days that quietly compound.",
    "Bit of a low. Compared myself to others on social media and it stung. "
    "Closing the apps and going to read instead.",
]

TASKS = [
    ("Finish thesis chapter 3", "Outline + write the methodology section.",  3, +5, "todo"),
    ("Review feedback from advisor", "Address all comments in the draft.",   2, +2, "todo"),
    ("Pomodoro: linear algebra problem set", "10 problems, focus mode.",     2, +1, "doing"),
    ("Prepare slides for project defence", "30-minute deck, dry-run twice.", 4, +12, "doing"),
    ("Sign up for graduation gown rental", "",                               1, +20, "todo"),
    ("Email professor about reference letter", "",                           2, -3, "done"),
]

SUBJECTS = [
    ("Machine Learning", 30, +18),
    ("Linear Algebra",   25, +24),
    ("Software Architecture", 18, +35),
    ("Statistics for ML",     22, +12),
]

MEMORIES = [
    ("graduation_project", "Building LIFE OS AI — final year project, due in 6 weeks."),
    ("focus_hours", "Strongest focus window is 4-7 PM. Avoid scheduling shallow work then."),
    ("recovery_anchor", "30-minute walk before opening the laptop has been a game-changer."),
]


def seed() -> None:
    app = create_app()
    with app.app_context():
        db = DatabaseManager(app.config["DATABASE_PATH"])
        db.init_schema()

        users = UserRepository(db)
        existing = users.get_by_email(DEMO_EMAIL)
        if existing:
            print(f"⚠  Demo user already exists (id={existing.id}). Wiping & re-seeding their data…")
            db.execute("DELETE FROM tasks            WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM study_sessions   WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM subjects         WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM mood_entries     WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM productivity_logs WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM memories         WHERE user_id = ?", (existing.id,))
            db.execute("DELETE FROM chat_sessions    WHERE user_id = ?", (existing.id,))
            user = existing
        else:
            user = users.create("Demo Student", DEMO_EMAIL, DEMO_PASSWORD)
            print(f"✓  Created demo user (id={user.id})")

        uid = user.id

        # ---------- Tasks ---------------------------------------------------
        tm = TaskManager(db, uid)
        for title, desc, prio, days_offset, status in TASKS:
            due = (date.today() + timedelta(days=days_offset)).isoformat() if days_offset is not None else None
            tid = tm.create(title, desc, priority=prio, due_date=due)
            if status != "todo":
                tm.set_status(tid, status)
        print(f"✓  Inserted {len(TASKS)} tasks")

        # ---------- Subjects + study sessions ------------------------------
        sp = StudyPlanner(db, uid)
        subject_ids = []
        for name, target, exam_offset in SUBJECTS:
            sid = sp.add_subject(
                name=name,
                target_hours=target,
                exam_date=(date.today() + timedelta(days=exam_offset)).isoformat(),
            )
            subject_ids.append(sid)
        print(f"✓  Inserted {len(SUBJECTS)} subjects")

        # Study sessions — ~20 sessions across the last 14 days
        random.seed(7)
        for _ in range(22):
            days_back = random.randint(0, 13)
            hour = random.choices(
                [9, 10, 14, 15, 16, 17, 18, 19, 22, 23],
                weights=[2, 3, 3, 4, 5, 6, 5, 3, 1, 1],
            )[0]
            started = datetime.now() - timedelta(days=days_back, hours=datetime.now().hour - hour)
            duration = random.choice([25, 25, 50, 50, 50, 90])
            # Higher focus during peak window
            focus = random.randint(8, 10) if 16 <= hour <= 19 else random.randint(5, 8)
            db.execute(
                """INSERT INTO study_sessions
                   (user_id, subject_id, started_at, duration_min, focus_score, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (uid, random.choice(subject_ids),
                 started.replace(microsecond=0).isoformat(sep=" "),
                 duration, focus, "Seeded session"),
            )
        print("✓  Inserted 22 study sessions")

        # ---------- Productivity logs --------------------------------------
        prod = ProductivityLogRepository(db, uid)
        for i in range(13, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            # rising trend + some variance
            base = 55 + (13 - i) * 1.5 + random.randint(-8, 8)
            base = max(20, min(95, int(round(base))))
            db.execute(
                """INSERT OR REPLACE INTO productivity_logs
                   (user_id, log_date, focus_minutes, deep_work_min, breaks_min,
                    sleep_hours, productivity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (uid, d,
                 random.randint(90, 240),       # focus
                 random.randint(40, 160),       # deep work
                 random.randint(15, 70),        # breaks
                 round(random.uniform(6.2, 8.1), 1),  # sleep
                 base),
            )
        print("✓  Inserted 14 productivity logs")

        # ---------- Mood journal ------------------------------------------
        mood = MoodRepository(db, uid)
        detector = EmotionDetector()
        for i, text in enumerate(JOURNAL_ENTRIES):
            analysis = detector.analyse(text)
            ts = (datetime.now() - timedelta(days=i, hours=random.randint(0, 5)))
            db.execute(
                """INSERT INTO mood_entries
                   (user_id, journal, sentiment, emotion, stress_level, motivation, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (uid, text, analysis["sentiment"], analysis["emotion"],
                 analysis["stress"], analysis["motivation"],
                 ts.replace(microsecond=0).isoformat(sep=" ")),
            )
        print(f"✓  Inserted {len(JOURNAL_ENTRIES)} mood entries")

        # ---------- Memories ----------------------------------------------
        memory = MemoryRepository(db, uid)
        for k, v in MEMORIES:
            memory.remember(k, v)
        print(f"✓  Inserted {len(MEMORIES)} Aurora memories")

        # ---------- A starter chat session --------------------------------
        chat = ChatRepository(db, uid)
        sid = chat.create_session("Welcome — first conversation")
        chat.append_message(sid, "user",
            "Hey Aurora. Set me up for a productive next two weeks.")
        chat.append_message(sid, "assistant",
            "Welcome to LIFE OS. I've already absorbed your subjects, tasks, and last "
            "fortnight of productivity logs. Three observations to start:\n\n"
            "**1. Your peak focus window is 4–7 PM.** Schedule your hardest work there.\n"
            "**2. Sleep average is healthy** at ~7.3h — keep it.\n"
            "**3. Your trend slope is +1.6/day** — small and steady. "
            "Don't over-correct. Pick one habit (the morning walk you mentioned) and lock it.\n\n"
            "What do you want to focus on first?")
        print("✓  Seeded one starter chat session")

        print(f"""
─────────────────────────────────────────────
✓ DEMO ACCOUNT READY
─────────────────────────────────────────────
  Email:    {DEMO_EMAIL}
  Password: {DEMO_PASSWORD}

  Start the server with:  python run.py
  Then sign in at:        http://127.0.0.1:5000
─────────────────────────────────────────────
""")


if __name__ == "__main__":
    seed()
