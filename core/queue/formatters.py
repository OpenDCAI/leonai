"""XML formatters for steer messages and task notifications.

Matches Claude Code's system-reminder convention so the LLM treats
injected content as authoritative system instructions.
"""


def format_steer_reminder(content: str) -> str:
    """Format user steer message as system-reminder XML."""
    return (
        "<system-reminder>\n"
        "The user sent a new message while you were working:\n"
        f"{content}\n\n"
        "IMPORTANT: After completing your current task, "
        "you MUST address the user's message above. Do not ignore it.\n"
        "</system-reminder>"
    )


def format_task_notification(
    task_id: str,
    status: str,
    summary: str,
    result: str | None = None,
    usage: dict | None = None,
    description: str | None = None,
) -> str:
    """Format background task completion as system-reminder XML."""
    parts = [
        "<system-reminder>",
        "<task-notification>",
        f"  <task-id>{task_id}</task-id>",
        f"  <status>{status}</status>",
    ]
    if description:
        parts.append(f"  <description>{description}</description>")
    parts.append(f"  <summary>{summary}</summary>")
    if result is not None:
        # Truncate long results to avoid flooding context
        truncated = result[:2000] + "..." if len(result) > 2000 else result
        parts.append(f"  <result>{truncated}</result>")
    if usage:
        parts.append(f"  <usage>{usage}</usage>")
    parts.append("</task-notification>")
    parts.append("</system-reminder>")
    return "\n".join(parts)
