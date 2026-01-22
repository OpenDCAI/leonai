"""Path validation utilities for Anthropic tools middleware."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def validate_virtual_path(
    path: str, *, allowed_prefixes: Sequence[str] | None = None
) -> str:
    """Validate and normalize virtual file path for security.

    Args:
        path: The path to validate.
        allowed_prefixes: Optional list of allowed path prefixes.

    Returns:
        Normalized canonical path.

    Raises:
        ValueError: If path contains traversal sequences or violates prefix rules.
    """
    if ".." in path or path.startswith("~"):
        msg = f"Path traversal not allowed: {path}"
        raise ValueError(msg)

    normalized = os.path.normpath(path)
    normalized = normalized.replace("\\", "/")

    if not normalized.startswith("/"):
        normalized = f"/{normalized}"

    if allowed_prefixes is not None and not any(
        normalized.startswith(prefix) for prefix in allowed_prefixes
    ):
        msg = f"Path must start with one of {allowed_prefixes}: {path}"
        raise ValueError(msg)

    return normalized


def validate_and_resolve_filesystem_path(
    path: str, root_path: Path, allowed_prefixes: list[str] | None = None
) -> Path:
    """Validate and resolve a virtual path to filesystem path.

    Args:
        path: Virtual path (e.g., `/file.txt` or `/src/main.py`).
        root_path: Root directory for file operations.
        allowed_prefixes: Optional list of allowed virtual path prefixes.

    Returns:
        Resolved absolute filesystem path within `root_path`.

    Raises:
        ValueError: If path contains traversal attempts, escapes root directory,
            or violates `allowed_prefixes` restrictions.
    """
    if not path.startswith("/"):
        path = "/" + path

    if ".." in path or "~" in path:
        msg = "Path traversal not allowed"
        raise ValueError(msg)

    relative = path.lstrip("/")
    full_path = (root_path / relative).resolve()

    try:
        full_path.relative_to(root_path)
    except ValueError:
        msg = f"Path outside root directory: {path}"
        raise ValueError(msg) from None

    if allowed_prefixes:
        virtual_path = "/" + str(full_path.relative_to(root_path))
        allowed = any(
            virtual_path.startswith(prefix) or virtual_path == prefix.rstrip("/")
            for prefix in allowed_prefixes
        )
        if not allowed:
            msg = f"Path must start with one of: {allowed_prefixes}"
            raise ValueError(msg)

    return full_path


def list_directory(files: dict[str, dict], path: str) -> list[str]:
    """List files in a directory.

    Args:
        files: Files `dict`.
        path: Normalized directory path.

    Returns:
        Sorted list of file paths in the directory.
    """
    dir_path = path if path.endswith("/") else f"{path}/"

    matching_files = []
    for file_path in files:
        if file_path.startswith(dir_path):
            relative = file_path[len(dir_path) :]
            if "/" not in relative:
                matching_files.append(file_path)

    return sorted(matching_files)
