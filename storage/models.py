"""Shared storage domain models — provider-neutral data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FileOperationRow:
    id: str
    thread_id: str
    checkpoint_id: str
    timestamp: float
    operation_type: str
    file_path: str
    before_content: str | None
    after_content: str
    changes: list[dict] | None
    status: str = "applied"
