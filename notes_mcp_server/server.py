from fastmcp import FastMCP

from notes_mcp_server import database


mcp = FastMCP("Notes MCP Server")


@mcp.tool
def save_note(
    title: str,
    content: str,
    tags: str = "",
) -> dict:
    """Save a new note.

    Args:
        title: Short title of the note.
        content: Full note content.
        tags: Optional comma-separated tags.
    """

    note = database.save_note(
        title=title,
        content=content,
        tags=tags,
    )

    return {
        "success": True,
        "message": "Note saved successfully.",
        "note": note,
    }


@mcp.tool
def list_notes() -> dict:
    """List all saved notes."""

    notes = database.list_notes()

    return {
        "success": True,
        "count": len(notes),
        "notes": notes,
    }


@mcp.tool
def get_note(note_id: int) -> dict:
    """Retrieve a note by ID.

    Args:
        note_id: ID of the note.
    """

    note = database.get_note(note_id)

    if note is None:
        return {
            "success": False,
            "message": f"Note {note_id} was not found.",
        }

    return {
        "success": True,
        "note": note,
    }


@mcp.tool
def search_notes(query: str) -> dict:
    """Search notes by title, content, or tags.

    Args:
        query: Keyword or phrase to search for.
    """

    notes = database.search_notes(query)

    return {
        "success": True,
        "count": len(notes),
        "notes": notes,
    }


@mcp.tool
def update_note(
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    tags: str | None = None,
) -> dict:
    """Update an existing note.

    Args:
        note_id: ID of the note.
        title: Optional new title.
        content: Optional new content.
        tags: Optional new tags.
    """

    note = database.update_note(
        note_id=note_id,
        title=title,
        content=content,
        tags=tags,
    )

    if note is None:
        return {
            "success": False,
            "message": f"Note {note_id} was not found.",
        }

    return {
        "success": True,
        "message": "Note updated successfully.",
        "note": note,
    }


@mcp.tool
def delete_note(note_id: int) -> dict:
    """Delete a note by ID.

    Args:
        note_id: ID of the note.
    """

    deleted = database.delete_note(note_id)

    if not deleted:
        return {
            "success": False,
            "message": f"Note {note_id} was not found.",
        }

    return {
        "success": True,
        "message": f"Note {note_id} deleted successfully.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")