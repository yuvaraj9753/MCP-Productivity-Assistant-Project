import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "notes.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite database connection."""

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the notes table if it does not exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )


def row_to_dict(
    row: sqlite3.Row | None,
) -> dict[str, Any] | None:
    """Convert a database row to a dictionary."""

    if row is None:
        return None

    return dict(row)


def save_note(
    title: str,
    content: str,
    tags: str = "",
) -> dict[str, Any]:
    """Save a new note."""

    title = title.strip()
    content = content.strip()

    if not title:
        raise ValueError("Note title cannot be empty.")

    if not content:
        raise ValueError("Note content cannot be empty.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
            """,
            (title, content, tags.strip()),
        )

        row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return row_to_dict(row)


def list_notes() -> list[dict[str, Any]]:
    """Return all saved notes."""

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM notes ORDER BY id DESC"
        ).fetchall()

        return [dict(row) for row in rows]


def get_note(note_id: int) -> dict[str, Any] | None:
    """Retrieve a note by ID."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()

        return row_to_dict(row)


def search_notes(
    query: str,
) -> list[dict[str, Any]]:
    """Search notes by title, content, or tags."""

    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty.")

    search_pattern = f"%{query}%"

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM notes
            WHERE title LIKE ?
               OR content LIKE ?
               OR tags LIKE ?
            ORDER BY id DESC
            """,
            (search_pattern, search_pattern, search_pattern),
        ).fetchall()

        return [dict(row) for row in rows]


def update_note(
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    tags: str | None = None,
) -> dict[str, Any] | None:
    """Update the supplied fields of a note."""

    existing = get_note(note_id)

    if existing is None:
        return None

    updates: dict[str, str] = {}

    if title is not None:
        title = title.strip()

        if not title:
            raise ValueError("Note title cannot be empty.")

        updates["title"] = title

    if content is not None:
        content = content.strip()

        if not content:
            raise ValueError("Note content cannot be empty.")

        updates["content"] = content

    if tags is not None:
        updates["tags"] = tags.strip()

    if not updates:
        return existing

    assignments = ", ".join(
        f"{column} = ?" for column in updates
    )

    query = f"""
        UPDATE notes
        SET {assignments},
            updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE id = ?
    """

    parameters = list(updates.values()) + [note_id]

    with get_connection() as connection:
        connection.execute(query, parameters)

    return get_note(note_id)


def delete_note(note_id: int) -> bool:
    """Delete a note by ID."""

    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM notes WHERE id = ?",
            (note_id,),
        )

        return cursor.rowcount > 0


initialize_database()