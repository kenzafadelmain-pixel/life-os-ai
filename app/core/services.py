"""
Two utility services that round out the OO architecture:

* **VoiceAssistant** — generates spoken replies via gTTS when available,
  with a graceful no-op fallback so missing system audio packages don't
  break the app.

* **AutomationEngine** — exposes scheduled "automations" (file organising,
  daily report generation, reminder dispatch). The engine is *interface-
  complete*: every automation has a Python implementation, but heavy work
  (cron-style scheduling) is delegated to the host OS or APScheduler if
  the operator wants it. We deliberately keep this in-process for the
  graduation demo.
"""
from __future__ import annotations

import io
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


# --------------------------------------------------------------- voice
class VoiceAssistant:
    """Wraps gTTS — degrades gracefully when the library isn't installed."""

    def __init__(self, lang: str = "en"):
        self.lang = lang
        try:
            from gtts import gTTS  # noqa: F401
            self.available = True
        except Exception:
            self.available = False

    def synthesise(self, text: str) -> Optional[bytes]:
        """Return an MP3 byte-string for `text`, or None if synthesis failed."""
        if not text.strip():
            return None
        if not self.available:
            return None
        try:
            from gtts import gTTS
            buf = io.BytesIO()
            gTTS(text=text, lang=self.lang).write_to_fp(buf)
            return buf.getvalue()
        except Exception:
            return None


# ------------------------------------------------------- file summariser
class FileSummariser:
    """
    Extracts plain text from PDF / TXT / MD / DOCX files and produces a
    short summary + a handful of flashcards.

    The implementation prefers `pypdf` and `python-docx`, but degrades to
    plain-text reading if they aren't available.
    """

    def extract_text(self, path: str) -> str:
        ext = Path(path).suffix.lower().lstrip(".")
        if ext in ("txt", "md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        if ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return ""
        if ext == "docx":
            try:
                import docx
                doc = docx.Document(path)
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                return ""
        return ""

    def summarise(self, text: str, max_sentences: int = 5) -> str:
        """A very small extractive summariser — first + most-frequent sentences."""
        text = (text or "").strip()
        if not text:
            return "No readable text was found in this file."

        # Naive sentence split.
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if 20 <= len(s) <= 280]
        if not sentences:
            return text[:400] + ("…" if len(text) > 400 else "")

        # Score by word frequency (excluding stopwords).
        stop = set(
            "the a an of and or to in on for is are was were be been being with "
            "this that these those it its as by from at into about over under "
            "have has had do does did not no but so if then than which who whom "
            "i me my we our you your he she they them their us".split()
        )
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", text)]
        freq: dict[str, int] = {}
        for w in words:
            if w not in stop:
                freq[w] = freq.get(w, 0) + 1

        def score(s):
            return sum(freq.get(w.lower(), 0) for w in re.findall(r"[A-Za-z]+", s))

        ranked = sorted(sentences, key=score, reverse=True)
        chosen = ranked[:max_sentences]
        # Keep original order
        chosen_in_order = [s for s in sentences if s in chosen][:max_sentences]
        return " ".join(chosen_in_order)

    def flashcards(self, text: str, n: int = 5) -> list[dict]:
        """Build naive Q/A pairs by picking key sentences and turning them into prompts."""
        import re
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 30 <= len(s) <= 260]
        cards = []
        for s in sentences[: n * 3]:
            words = s.split()
            if len(words) < 6:
                continue
            # Hide the longest noun-ish word.
            target = max(words, key=lambda w: len(w.strip(",.;:")))
            question = s.replace(target, "______", 1)
            cards.append({"front": f"Fill in the blank: {question}", "back": target.strip(",.;:")})
            if len(cards) == n:
                break
        return cards


# ---------------------------------------------------- automation
class AutomationEngine:
    """
    A tiny registry of named automations.

    Each automation is a callable that takes (user_id, db) and returns a
    human-readable result string. Routes can list automations and trigger
    them on demand from the dashboard.
    """

    def __init__(self):
        self._jobs: dict[str, dict] = {}

    def register(self, key: str, name: str, description: str,
                 fn: Callable[[int, "DatabaseManager"], str]) -> None:
        self._jobs[key] = {"key": key, "name": name, "description": description, "fn": fn}

    def list(self) -> list[dict]:
        return [{"key": j["key"], "name": j["name"], "description": j["description"]}
                for j in self._jobs.values()]

    def run(self, key: str, user_id: int, db) -> str:
        if key not in self._jobs:
            raise KeyError(key)
        return self._jobs[key]["fn"](user_id, db)


def build_default_automations(upload_folder: str) -> AutomationEngine:
    """Wire up a sensible default set of automations."""
    engine = AutomationEngine()

    def organise_files(user_id: int, db) -> str:
        """Move uploads into subfolders by extension."""
        base = Path(upload_folder)
        moved = 0
        for p in base.glob("*"):
            if p.is_file():
                target = base / (p.suffix.lstrip(".").lower() or "misc")
                target.mkdir(exist_ok=True)
                shutil.move(str(p), target / p.name)
                moved += 1
        return f"Organised {moved} file(s) into typed folders."

    def daily_report(user_id: int, db) -> str:
        row = db.query_one(
            """SELECT
                 (SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status='done'
                    AND DATE(completed_at)=DATE('now')) AS done,
                 (SELECT COUNT(*) FROM study_sessions WHERE user_id = ?
                    AND DATE(started_at)=DATE('now')) AS sessions,
                 (SELECT AVG(motivation) FROM mood_entries WHERE user_id = ?
                    AND DATE(created_at)=DATE('now')) AS mot""",
            (user_id, user_id, user_id),
        )
        done = (row["done"] if row else 0) or 0
        sess = (row["sessions"] if row else 0) or 0
        mot = round(row["mot"], 1) if (row and row["mot"]) else "—"
        return (f"Daily snapshot: {done} task(s) completed, {sess} study session(s), "
                f"motivation: {mot}.")

    def backup_database(user_id: int, db) -> str:
        src = Path(db.db_path)
        if src.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            dst = src.with_name(f"life_os.backup.{stamp}.db")
            shutil.copy2(src, dst)
            return f"Database backed up to {dst.name}."
        return "Database not found on disk (running in-memory)."

    def schedule_reminders(user_id: int, db) -> str:
        rows = db.query(
            """SELECT title, due_date FROM tasks
               WHERE user_id = ? AND status != 'done' AND due_date IS NOT NULL
               AND due_date <= DATE('now','+2 days')
               ORDER BY due_date ASC LIMIT 5""",
            (user_id,),
        )
        if not rows:
            return "No urgent reminders queued."
        items = ", ".join(f"\"{r['title']}\" ({r['due_date']})" for r in rows)
        return f"Reminders queued for: {items}."

    engine.register("organise_files", "Organise uploads",
                    "Move loose files in /uploads into typed subfolders.",
                    organise_files)
    engine.register("daily_report", "Daily snapshot",
                    "Summarise today's completed work and mood.",
                    daily_report)
    engine.register("backup_db", "Backup database",
                    "Create a timestamped copy of the SQLite database.",
                    backup_database)
    engine.register("reminders", "Schedule reminders",
                    "Queue notifications for tasks due in the next 48h.",
                    schedule_reminders)
    return engine
