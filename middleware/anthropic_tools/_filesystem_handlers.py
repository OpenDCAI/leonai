"""Filesystem-based file operation handlers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import ToolMessage
from langgraph.types import Command

from ._path_utils import validate_and_resolve_filesystem_path

if TYPE_CHECKING:
    pass


def handle_view(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
    max_file_size_bytes: int,
) -> Command:
    """Handle view command for filesystem storage."""
    path = args["path"]
    full_path = validate_and_resolve_filesystem_path(path, root_path, allowed_prefixes)

    if not full_path.exists() or not full_path.is_file():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    if full_path.stat().st_size > max_file_size_bytes:
        max_mb = max_file_size_bytes / 1024 / 1024
        msg = f"File too large: {path} exceeds {max_mb}MB"
        raise ValueError(msg)

    try:
        content = full_path.read_text()
    except UnicodeDecodeError as e:
        msg = f"Cannot decode file {path}: {e}"
        raise ValueError(msg) from e

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    formatted_lines = [f"{i + 1}|{line}" for i, line in enumerate(lines)]
    formatted_content = "\n".join(formatted_lines)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=formatted_content,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_create(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
) -> Command:
    """Handle create command for filesystem storage."""
    path = args["path"]
    file_text = args["file_text"]

    full_path = validate_and_resolve_filesystem_path(path, root_path, allowed_prefixes)

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(file_text + "\n")

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"File created: {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_str_replace(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
) -> Command:
    """Handle str_replace command for filesystem storage."""
    path = args["path"]
    old_str = args["old_str"]
    new_str = args.get("new_str", "")

    full_path = validate_and_resolve_filesystem_path(path, root_path, allowed_prefixes)

    if not full_path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    content = full_path.read_text()

    if old_str not in content:
        msg = f"String not found in file: {old_str}"
        raise ValueError(msg)

    new_content = content.replace(old_str, new_str, 1)
    full_path.write_text(new_content)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"String replaced in {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_insert(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
) -> Command:
    """Handle insert command for filesystem storage."""
    path = args["path"]
    insert_line = args["insert_line"]
    text_to_insert = args["new_str"]

    full_path = validate_and_resolve_filesystem_path(path, root_path, allowed_prefixes)

    if not full_path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    content = full_path.read_text()
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
        had_trailing_newline = True
    else:
        had_trailing_newline = False

    new_lines = text_to_insert.split("\n")
    updated_lines = lines[:insert_line] + new_lines + lines[insert_line:]

    new_content = "\n".join(updated_lines)
    if had_trailing_newline:
        new_content += "\n"
    full_path.write_text(new_content)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Text inserted in {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_delete(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
) -> Command:
    """Handle delete command for filesystem storage."""
    path = args["path"]
    full_path = validate_and_resolve_filesystem_path(path, root_path, allowed_prefixes)

    if full_path.is_file():
        full_path.unlink()
    elif full_path.is_dir():
        shutil.rmtree(full_path)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"File deleted: {path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )


def handle_rename(
    args: dict,
    tool_call_id: str | None,
    tool_name: str,
    root_path: Path,
    allowed_prefixes: list[str] | None,
) -> Command:
    """Handle rename command for filesystem storage."""
    old_path = args["old_path"]
    new_path = args["new_path"]

    old_full = validate_and_resolve_filesystem_path(old_path, root_path, allowed_prefixes)
    new_full = validate_and_resolve_filesystem_path(new_path, root_path, allowed_prefixes)

    if not old_full.exists():
        msg = f"File not found: {old_path}"
        raise ValueError(msg)

    new_full.parent.mkdir(parents=True, exist_ok=True)
    old_full.rename(new_full)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"File renamed: {old_path} -> {new_path}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }
    )
