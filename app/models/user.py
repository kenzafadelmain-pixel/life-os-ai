"""
User domain model + repository.

We use a tiny data-mapper pattern: dataclass-style entities + a repository
class that knows how to load/save them through the DatabaseManager. This keeps
SQL out of the routes and makes the codebase pleasant to read.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.core.database import DatabaseManager


@dataclass
class User:
    id: int
    name: str
    email: str
    avatar_seed: str
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            avatar_seed=row["avatar_seed"],
            created_at=row["created_at"],
        )


class UserRepository:
    """Encapsulates persistence concerns for User entities."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ---------- queries ---------------------------------------------------
    def get(self, user_id: int) -> Optional[User]:
        row = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return User.from_row(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.db.query_one(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
        )
        return User.from_row(row) if row else None

    # ---------- commands --------------------------------------------------
    def create(self, name: str, email: str, password: str) -> User:
        if self.get_by_email(email):
            raise ValueError("An account with that email already exists.")

        password_hash = generate_password_hash(password)
        user_id = self.db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash),
        )
        # Seed defaults so the dashboard isn't empty on first login.
        self.db.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        user = self.get(user_id)
        assert user is not None
        return user

    def verify_password(self, email: str, password: str) -> Optional[User]:
        row = self.db.query_one(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
        )
        if not row or not check_password_hash(row["password_hash"], password):
            return None
        return User.from_row(row)

    def update_profile(self, user_id: int, name: str, avatar_seed: str) -> None:
        self.db.execute(
            "UPDATE users SET name = ?, avatar_seed = ? WHERE id = ?",
            (name.strip(), avatar_seed, user_id),
        )

    def update_password(self, user_id: int, new_password: str) -> None:
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )
