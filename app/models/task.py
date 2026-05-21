"""
Task domain — model class + the TaskManager required by the project brief.

The TaskManager exposes the high-level operations the UI calls:
  * create / update / delete tasks
  * change status (todo / doing / done)
  * fetch grouped buckets for the kanban board
  * suggest next-up tasks based on priority + due date

It deliberately swallows SQL so the route layer reads like business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from app.core.database import DatabaseManager


PRIORITY_LABELS = {1: "Low", 2: "Normal", 3: "High", 4: "Critical"}
STATUS_ORDER = ("todo", "doing", "done")


@dataclass
class Task:
    id: int
    user_id: int
    title: str
    description: str
    status: str
    priority: int
    due_date: Optional[date]
    created_at: datetime
    completed_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "Task":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"] or "",
            status=row["status"],
            priority=row["priority"],
            due_date=row["due_date"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, "Normal")

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status == "done":
            return False
        d = self.due_date if isinstance(self.due_date, date) else date.fromisoformat(str(self.due_date))
        return d < date.today()


@dataclass
class TaskBoard:
    todo: list[Task] = field(default_factory=list)
    doing: list[Task] = field(default_factory=list)
    done: list[Task] = field(default_factory=list)


class TaskManager:
    """OO façade over the tasks table."""

    def __init__(self, db: DatabaseManager, user_id: int):
        self.db = db
        self.user_id = user_id

    # ----- queries --------------------------------------------------------
    def get(self, task_id: int) -> Optional[Task]:
        row = self.db.query_one(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, self.user_id),
        )
        return Task.from_row(row) if row else None

    def list_all(self) -> list[Task]:
        rows = self.db.query(
            """SELECT * FROM tasks WHERE user_id = ?
               ORDER BY status, priority DESC, COALESCE(due_date, '9999-12-31')""",
            (self.user_id,),
        )
        return [Task.from_row(r) for r in rows]

    def board(self) -> TaskBoard:
        board = TaskBoard()
        for task in self.list_all():
            getattr(board, task.status).append(task)
        return board

    def stats(self) -> dict:
        rows = self.db.query(
            """SELECT status, COUNT(*) AS n FROM tasks
               WHERE user_id = ? GROUP BY status""",
            (self.user_id,),
        )
        counts = {r["status"]: r["n"] for r in rows}
        total = sum(counts.values())
        done = counts.get("done", 0)
        return {
            "total": total,
            "todo": counts.get("todo", 0),
            "doing": counts.get("doing", 0),
            "done": done,
            "completion_rate": int(round((done / total) * 100)) if total else 0,
        }

    def next_up(self, limit: int = 5) -> list[Task]:
        """Highest-leverage tasks first: priority desc, then nearest due date."""
        rows = self.db.query(
            """SELECT * FROM tasks
               WHERE user_id = ? AND status != 'done'
               ORDER BY priority DESC, COALESCE(due_date, '9999-12-31') ASC
               LIMIT ?""",
            (self.user_id, limit),
        )
        return [Task.from_row(r) for r in rows]

    # ----- commands -------------------------------------------------------
    def create(
        self,
        title: str,
        description: str = "",
        priority: int = 2,
        due_date: Optional[str] = None,
    ) -> int:
        return self.db.execute(
            """INSERT INTO tasks (user_id, title, description, priority, due_date)
               VALUES (?, ?, ?, ?, ?)""",
            (self.user_id, title.strip(), description.strip(), priority, due_date or None),
        )

    def update(self, task_id: int, **fields) -> None:
        allowed = {"title", "description", "priority", "due_date", "status"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return
        params.extend([task_id, self.user_id])
        self.db.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            params,
        )

    def set_status(self, task_id: int, status: str) -> None:
        if status not in STATUS_ORDER:
            raise ValueError(f"Invalid status: {status}")
        completed = "CURRENT_TIMESTAMP" if status == "done" else "NULL"
        self.db.execute(
            f"""UPDATE tasks SET status = ?, completed_at = {completed}
                WHERE id = ? AND user_id = ?""",
            (status, task_id, self.user_id),
        )

    def delete(self, task_id: int) -> None:
        self.db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, self.user_id),
        )
