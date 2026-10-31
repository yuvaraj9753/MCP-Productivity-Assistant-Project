from datetime import date

from fastmcp import FastMCP

from task_mcp_server import database


mcp = FastMCP("Task MCP Server")


@mcp.tool
def create_task(
    title: str,
    description: str = "",
    due_date: str | None = None,
    priority: str = "medium",
) -> dict:
    """Create a task with a title, optional description and deadline.

    Args:
        title: Short title of the task.
        description: Additional task details.
        due_date: Optional deadline in YYYY-MM-DD format.
        priority: Task priority: low, medium, or high.
    """

    if due_date is not None:
        try:
            date.fromisoformat(due_date)
        except ValueError as exc:
            raise ValueError(
                "due_date must use YYYY-MM-DD format."
            ) from exc

    task = database.create_task(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
    )

    return {
        "success": True,
        "message": "Task created successfully.",
        "task": task,
    }


@mcp.tool
def list_tasks(
    status: str = "all",
    priority: str = "all",
) -> dict:
    """List tasks, optionally filtered by status and priority.

    Args:
        status: all, pending, or completed.
        priority: all, low, medium, or high.
    """

    tasks = database.list_tasks(status, priority)

    return {
        "success": True,
        "count": len(tasks),
        "tasks": tasks,
    }


@mcp.tool
def get_task(task_id: int) -> dict:
    """Retrieve one task by its ID.

    Args:
        task_id: ID of the task.
    """

    task = database.get_task(task_id)

    if task is None:
        return {
            "success": False,
            "message": f"Task {task_id} was not found.",
        }

    return {"success": True, "task": task}


@mcp.tool
def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
) -> dict:
    """Update a task's fields.

    Args:
        task_id: ID of the task.
        title: Optional new title.
        description: Optional new description.
        due_date: Optional new deadline in YYYY-MM-DD format.
        priority: Optional priority: low, medium, or high.
    """

    if due_date is not None:
        try:
            date.fromisoformat(due_date)
        except ValueError as exc:
            raise ValueError(
                "due_date must use YYYY-MM-DD format."
            ) from exc

    task = database.update_task(
        task_id=task_id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
    )

    if task is None:
        return {
            "success": False,
            "message": f"Task {task_id} was not found.",
        }

    return {
        "success": True,
        "message": "Task updated successfully.",
        "task": task,
    }


@mcp.tool
def complete_task(task_id: int) -> dict:
    """Mark a task as completed.

    Args:
        task_id: ID of the task.
    """

    task = database.complete_task(task_id)

    if task is None:
        return {
            "success": False,
            "message": f"Task {task_id} was not found.",
        }

    return {
        "success": True,
        "message": "Task marked as completed.",
        "task": task,
    }


@mcp.tool
def delete_task(task_id: int) -> dict:
    """Delete a task by its ID.

    Args:
        task_id: ID of the task.
    """

    deleted = database.delete_task(task_id)

    if not deleted:
        return {
            "success": False,
            "message": f"Task {task_id} was not found.",
        }

    return {
        "success": True,
        "message": f"Task {task_id} deleted successfully.",
    }


@mcp.tool
def get_overdue_tasks() -> dict:
    """Get pending tasks whose deadlines have passed."""

    tasks = database.get_overdue_tasks()

    return {
        "success": True,
        "count": len(tasks),
        "tasks": tasks,
    }


@mcp.tool
def get_task_summary() -> dict:
    """Get total, pending, and completed task counts."""

    return {
        "success": True,
        "summary": database.get_task_summary(),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")