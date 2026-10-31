import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "tasks.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite database connection."""

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the tasks table if it does not exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK(priority IN ('low', 'medium', 'high')),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'completed')),
                created_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a SQLite row to a dictionary."""

    if row is None:
        return None

    return dict(row)


def create_task(
    title: str,
    description: str = "",
    due_date: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """Create a task."""

    title = title.strip()
    priority = priority.lower()

    if not title:
        raise ValueError("Task title cannot be empty.")

    if priority not in {"low", "medium", "high"}:
        raise ValueError("Priority must be low, medium, or high.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, description, due_date, priority)
            VALUES (?, ?, ?, ?)
            """,
            (title, description.strip(), due_date, priority),
        )

        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return row_to_dict(row)


def list_tasks(
    status: str = "all",
    priority: str = "all",
) -> list[dict[str, Any]]:
    """List tasks with optional filters."""

    if status not in {"all", "pending", "completed"}:
        raise ValueError("Invalid task status.")

    if priority not in {"all", "low", "medium", "high"}:
        raise ValueError("Invalid task priority.")

    query = "SELECT * FROM tasks WHERE 1=1"
    parameters: list[str] = []

    if status != "all":
        query += " AND status = ?"
        parameters.append(status)

    if priority != "all":
        query += " AND priority = ?"
        parameters.append(priority)

    query += " ORDER BY id DESC"

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

        return [dict(row) for row in rows]


def get_task(task_id: int) -> dict[str, Any] | None:
    """Get a task by ID."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        return row_to_dict(row)


def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
) -> dict[str, Any] | None:
    """Update provided task fields."""

    existing = get_task(task_id)

    if existing is None:
        return None

    updates: dict[str, Any] = {}

    if title is not None:
        title = title.strip()

        if not title:
            raise ValueError("Task title cannot be empty.")

        updates["title"] = title

    if description is not None:
        updates["description"] = description.strip()

    if due_date is not None:
        updates["due_date"] = due_date

    if priority is not None:
        priority = priority.lower()

        if priority not in {"low", "medium", "high"}:
            raise ValueError("Invalid task priority.")

        updates["priority"] = priority

    if not updates:
        return existing

    assignments = ", ".join(
        f"{column} = ?" for column in updates
    )

    query = f"""
        UPDATE tasks
        SET {assignments},
            updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE id = ?
    """

    parameters = list(updates.values()) + [task_id]

    with get_connection() as connection:
        connection.execute(query, parameters)

    return get_task(task_id)


def complete_task(task_id: int) -> dict[str, Any] | None:
    """Mark a task as completed."""

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ?
            """,
            (task_id,),
        )

    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    """Delete a task by ID."""

    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

        return cursor.rowcount > 0


def get_overdue_tasks() -> list[dict[str, Any]]:
    """Get pending tasks with deadlines before today."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = 'pending'
              AND due_date IS NOT NULL
              AND date(due_date) < date('now', 'localtime')
            ORDER BY due_date ASC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def get_task_summary() -> dict[str, int]:
    """Get total, pending, and completed task counts."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
                    0
                ) AS pending,
                COALESCE(
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END),
                    0
                ) AS completed
            FROM tasks
            """
        ).fetchone()

        return {
            "total": row["total"],
            "pending": row["pending"],
            "completed": row["completed"],
        }


initialize_database()