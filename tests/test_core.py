"""
Sanity tests for LIFE OS AI domain logic.

These tests use an in-memory SQLite database so they do NOT touch the real
data in `instance/life_os.db`. Run with:

    python -m unittest discover tests

They cover the core OOP modules — DatabaseManager, UserRepository,
TaskManager, EmotionDetector, ProductivityAnalyzer, PredictionEngine,
and the AIChatbot local fallback.
"""
import unittest
from datetime import date, timedelta

from app.core.database import DatabaseManager
from app.core.emotion import EmotionDetector
from app.core.chatbot import AIChatbot, LocalIntelligenceEngine
from app.core.analyzer import ProductivityAnalyzer
from app.core.predictor import PredictionEngine
from app.models.user import UserRepository
from app.models.task import TaskManager
from app.models.data import MoodRepository, ProductivityLogRepository


def fresh_db() -> DatabaseManager:
    db = DatabaseManager(":memory:")
    db.init_schema()
    return db


class TestDatabase(unittest.TestCase):
    def test_schema_creates(self):
        db = fresh_db()
        rows = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = {r["name"] for r in rows}
        for required in (
            "users", "tasks", "chat_sessions", "chat_messages",
            "subjects", "study_sessions", "mood_entries",
            "productivity_logs", "files", "memories", "settings",
        ):
            self.assertIn(required, names)


class TestUsers(unittest.TestCase):
    def test_create_and_login(self):
        db = fresh_db()
        users = UserRepository(db)
        u = users.create("Test", "t@example.com", "abc12345")
        self.assertEqual(u.email, "t@example.com")
        self.assertIsNotNone(users.verify_password("t@example.com", "abc12345"))
        self.assertIsNone(users.verify_password("t@example.com", "wrong-pw"))

    def test_duplicate_email_rejected(self):
        db = fresh_db()
        users = UserRepository(db)
        users.create("A", "a@example.com", "abc12345")
        with self.assertRaises(ValueError):
            users.create("B", "a@example.com", "abc12345")


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()
        self.user = UserRepository(self.db).create("U", "u@x.com", "abc12345")
        self.mgr = TaskManager(self.db, self.user.id)

    def test_create_and_board(self):
        self.mgr.create("Write thesis", "chapter 3", priority=3)
        self.mgr.create("Buy milk", priority=1)
        board = self.mgr.board()
        self.assertEqual(len(board.todo), 2)
        self.assertEqual(self.mgr.stats()["total"], 2)

    def test_status_change(self):
        tid = self.mgr.create("Task")
        self.mgr.set_status(tid, "doing")
        self.assertEqual(self.mgr.get(tid).status, "doing")
        self.mgr.set_status(tid, "done")
        stats = self.mgr.stats()
        self.assertEqual(stats["done"], 1)
        self.assertEqual(stats["completion_rate"], 100)

    def test_overdue_detection(self):
        past = (date.today() - timedelta(days=2)).isoformat()
        tid = self.mgr.create("Old task", due_date=past)
        self.assertTrue(self.mgr.get(tid).is_overdue)


class TestEmotion(unittest.TestCase):
    def setUp(self):
        self.det = EmotionDetector()

    def test_positive_text(self):
        r = self.det.analyse("I feel happy, grateful, and focused today!")
        self.assertGreater(r["sentiment"], 0)
        self.assertIn(r["emotion"], ("happy", "motivated", "calm"))

    def test_negative_text(self):
        r = self.det.analyse("I am stressed, anxious, and exhausted. I want to cry.")
        self.assertLess(r["sentiment"], 0)
        self.assertIn(r["emotion"], ("anxious", "sad", "tired"))
        self.assertGreaterEqual(r["stress"], 6)

    def test_empty_text(self):
        r = self.det.analyse("")
        self.assertEqual(r["sentiment"], 0.0)
        self.assertEqual(r["emotion"], "neutral")


class TestChatbot(unittest.TestCase):
    def test_local_fallback_always_replies(self):
        bot = AIChatbot()  # no keys → local engine
        self.assertEqual(bot.provider, "local")
        history = [{"role": "user", "content": "I'm feeling stressed about exams."}]
        reply = bot.reply(history, user_profile={"name": "Alex"})
        self.assertTrue(len(reply) > 10)

    def test_local_engine_routes_keywords(self):
        eng = LocalIntelligenceEngine()
        r = eng.chat([{"role": "user", "content": "hello there"}],
                     "name: Sam")
        self.assertIn("Sam", r)  # name interpolation


class TestAnalyzerAndPredictor(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()
        u = UserRepository(self.db).create("U", "u@x.com", "abc12345")
        self.uid = u.id

    def test_score_with_no_data(self):
        a = ProductivityAnalyzer(self.db, self.uid)
        # With nothing logged, score lands in the neutral middle band.
        self.assertGreaterEqual(a.overall_score(), 0)
        self.assertLessEqual(a.overall_score(), 100)

    def test_burnout_risk_shape(self):
        # Seed some productivity logs.
        repo = ProductivityLogRepository(self.db, self.uid)
        for _ in range(5):
            repo.upsert_today(120, 60, 30, 7.5, 70)
        p = PredictionEngine(self.db, self.uid).burnout_risk()
        for key in ("risk", "label", "color", "message"):
            self.assertIn(key, p)
        self.assertTrue(0 <= p["risk"] <= 100)

    def test_forecast_needs_enough_history(self):
        p = PredictionEngine(self.db, self.uid).productivity_forecast()
        self.assertIn("history", p)
        self.assertIn("forecast", p)


if __name__ == "__main__":
    unittest.main()
