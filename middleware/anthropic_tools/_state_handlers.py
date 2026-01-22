"""State-based file operation handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import ToolMessage
from langgraph.types import Command

from ._path_utils import list_directory, validate_virtual_path

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._types import AnthropicToolsState, FileData


def handle_view(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle view command for state-based storage."""
    path = args["path"]
    normalized_path = validate_virtual_path(path, allowed_prefixes=allowed_prefixes)

    files = cast("dict[str, Any]", state.get(state_key, {}))
    file_data = files.get(normalized_path)

    if file_data is None:
        matching = list_directory(files, normalized_path)

        if matching:
            content = "\n".join(matching)
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=content,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    ]
                }
            )

        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    lines_content = file_data["content"]
    formatted_lines = [f"{i + 1}|{line}" for i, line in enumerate(lines_content)]
    content = "\n".join(formatted_lines)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=content,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_create(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle create command for state-based storage."""
    path = args["path"]
    file_text = args["file_text"]

    normalized_path = validate_virtual_path(path, allowed_prefixes=allowed_prefixes)

    files = cast("dict[str, Any]", state.get(state_key, {}))
    existing = files.get(normalized_path)

    now = datetime.now(UTC).isoformat()
    created_at = existing["created_at"] if existing else now

    content_lines = file_text.split("\n")

    return Command(
        update={
            state_key: {
                normalized_path: {
                    "content": content_lines,
                    "created_at": created_at,
                    "modified_at": now,
                }
            },
            "messages": [
                ToolMessage(
                    content=f"File created: {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
        }
    )


def handle_str_replace(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle str_replace command for state-based storage."""
    path = args["path"]
    old_str = args["old_str"]
    new_str = args.get("new_str", "")

    normalized_path = validate_virtual_path(path, allowed_prefixes=allowed_prefixes)

    files = cast("dict[str, Any]", state.get(state_key, {}))
    file_data = files.get(normalized_path)
    if file_data is None:
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    lines_content = file_data["content"]
    content = "\n".join(lines_content)

    if old_str not in content:
        msg = f"String not found in file: {old_str}"
        raise ValueError(msg)

    new_content = content.replace(old_str, new_str, 1)
    new_lines = new_content.split("\n")

    now = datetime.now(UTC).isoformat()

    return Command(
        update={
            state_key: {
                normalized_path: {
                    "content": new_lines,
                    "created_at": file_data["created_at"],
                    "modified_at": now,
                }
            },
            "messages": [
                ToolMessage(
                    content=f"String replaced in {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
        }
    )


def handle_insert(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle insert command for state-based storage."""
    path = args["path"]
    insert_line = args["insert_line"]
    text_to_insert = args["new_str"]

    normalized_path = validate_virtual_path(path, allowed_prefixes=allowed_prefixes)

    files = cast("dict[str, Any]", state.get(state_key, {}))
    file_data = files.get(normalized_path)
    if file_data is None:
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    lines_content = file_data["content"]
    new_lines = text_to_insert.split("\n")

    updated_lines = (
        lines_content[:insert_line] + new_lines + lines_content[insert_line:]
    )

    now = datetime.now(UTC).isoformat()

    return Command(
        update={
            state_key: {
                normalized_path: {
                    "content": updated_lines,
                    "created_at": file_data["created_at"],
                    "modified_at": now,
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Text inserted in {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
        }
    )


def handle_delete(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle delete command for state-based storage."""
    path = args["path"]

    normalized_path = validate_virtual_path(path, allowed_prefixes=allowed_prefixes)

    return Command(
        update={
            state_key: {normalized_path: None},
            "messages": [
                ToolMessage(
                    content=f"File deleted: {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
        }
    )


def handle_rename(
    args: dict,
    state: AnthropicToolsState,
    tool_call_id: str | None,
    tool_name: str,
    state_key: str,
    allowed_prefixes: Sequence[str] | None,
) -> Command:
    """Handle rename command for state-based storage."""
    old_path = args["old_path"]
    new_path = args["new_path"]

    normalized_old = validate_virtual_path(old_path, allowed_prefixes=allowed_prefixes)
    normalized_new = validate_virtual_path(new_path, allowed_prefixes=allowed_prefixes)

    files = cast("dict[str, Any]", state.get(state_key, {}))
    file_data = files.get(normalized_old)
    if file_data is None:
        msg = f"File not found: {old_path}"
        raise ValueError(msg)

    now = datetime.now(UTC).isoformat()
    file_data_copy = file_data.copy()
    file_data_copy["modified_at"] = now

    return Command(
        update={
            state_key: {
                normalized_old: None,
                normalized_new: file_data_copy,
            },
            "messages": [
                ToolMessage(
                    content=f"File renamed: {old_path} -> {new_path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
        }
    )
