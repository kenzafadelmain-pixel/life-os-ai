"""
DatabaseManager
===============

A small but production-shaped wrapper around SQLite. Responsibilities:

* Open connections with row factory + foreign-key enforcement.
* Hold the full DDL for the LIFE OS AI schema in one place.
* Provide convenience `query`, `execute`, and `executemany` helpers used by
  the higher-level repository classes (UserRepository, TaskRepository …).

Why a class, not free functions? Two reasons:
1. The project brief asks for OOP architecture and a `DatabaseManager` class.
2. A single instance can be shared by route handlers via `current_app`, while
   tests can spin up an in-memory instance against a `":memory:"` path.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


# ----------------------------------------------------------------------------
# DDL — kept inline so the project is self-bootstrapping.
# ----------------------------------------------------------------------------
SCHEMA_DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        email           TEXT    NOT NULL UNIQUE,
        password_hash   TEXT    NOT NULL,
        avatar_seed     TEXT    NOT NULL DEFAULT 'spark',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title           TEXT    NOT NULL DEFAULT 'New conversation',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role            TEXT    NOT NULL CHECK (role IN ('user','assistant','system')),
        content         TEXT    NOT NULL,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title           TEXT    NOT NULL,
        description     TEXT,
        status          TEXT    NOT NULL DEFAULT 'todo'
                                CHECK (status IN ('todo','doing','done')),
        priority        INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 4),
        due_date        DATE,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at    TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS subjects (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name            TEXT    NOT NULL,
        target_hours    REAL    NOT NULL DEFAULT 10,
        exam_date       DATE,
        color           TEXT    NOT NULL DEFAULT '#7c5cff',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS study_sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id      INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
        started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        duration_min    INTEGER NOT NULL,
        focus_score     INTEGER NOT NULL DEFAULT 7 CHECK (focus_score BETWEEN 1 AND 10),
        notes           TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS mood_entries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        journal         TEXT    NOT NULL,
        sentiment       REAL    NOT NULL,      -- -1 .. +1
        emotion         TEXT    NOT NULL,      -- e.g. 'calm', 'anxious'
        stress_level    INTEGER NOT NULL CHECK (stress_level BETWEEN 1 AND 10),
        motivation      INTEGER NOT NULL CHECK (motivation BETWEEN 1 AND 10),
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS productivity_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        log_date        DATE    NOT NULL,
        focus_minutes   INTEGER NOT NULL DEFAULT 0,
        deep_work_min   INTEGER NOT NULL DEFAULT 0,
        breaks_min      INTEGER NOT NULL DEFAULT 0,
        sleep_hours     REAL    NOT NULL DEFAULT 7.0,
        productivity    INTEGER NOT NULL DEFAULT 50,  -- 0..100
        UNIQUE (user_id, log_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS files (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        filename        TEXT    NOT NULL,
        original_name   TEXT    NOT NULL,
        file_type       TEXT    NOT NULL,
        summary         TEXT,
        size_bytes      INTEGER NOT NULL DEFAULT 0,
        uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS memories (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        key             TEXT    NOT NULL,
        value           TEXT    NOT NULL,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, key)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        ai_provider     TEXT    NOT NULL DEFAULT 'local',
        theme           TEXT    NOT NULL DEFAULT 'aurora',
        notifications   INTEGER NOT NULL DEFAULT 1,
        coach_tone      TEXT    NOT NULL DEFAULT 'supportive'
    );
    """,
    # Indices that accelerate the heavy queries on the dashboard.
    "CREATE INDEX IF NOT EXISTS idx_tasks_user        ON tasks(user_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_messages_session  ON chat_messages(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_mood_user_date    ON mood_entries(user_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_prod_user_date    ON productivity_logs(user_id, log_date);",
    "CREATE INDEX IF NOT EXISTS idx_study_user_date   ON study_sessions(user_id, started_at);",
)


class DatabaseManager:
    """Thin OO wrapper over SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._in_memory = db_path == ":memory:"
        # For in-memory databases the schema lives on the connection itself,
        # so we must reuse one persistent connection across operations.
        self._persistent: sqlite3.Connection | None = None
        if not self._in_memory:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------- connection
    def _connect(self) -> sqlite3.Connection:
        # We intentionally *don't* use detect_types=PARSE_DECLTYPES: the
        # default converters for TIMESTAMP/DATE are deprecated in Python
        # 3.12+, and our domain layer treats those columns as ISO strings
        # already.
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context-managed connection with automatic commit / rollback.

        For on-disk databases we open + close a fresh connection per call
        (fine for SQLite + Flask's request scope).

        For in-memory databases (used by tests) we keep a single connection
        alive for the lifetime of the manager — otherwise every call would
        get an empty database.
        """
        if self._in_memory:
            if self._persistent is None:
                self._persistent = self._connect()
            conn = self._persistent
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            # NOTE: we deliberately do NOT close here.
            return

        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------------------------------------------------------- helpers
    def init_schema(self) -> None:
        with self.connection() as conn:
            for stmt in SCHEMA_DDL:
                conn.executescript(stmt)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return list(conn.execute(sql, params))

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Run a write and return the new lastrowid (or 0)."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid or 0

    def executemany(self, sql: str, seq_params: Iterable[Sequence[Any]]) -> None:
        with self.connection() as conn:
            conn.executemany(sql, seq_params)
