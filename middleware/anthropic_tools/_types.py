"""Type definitions for Anthropic tools middleware."""

from __future__ import annotations

from typing import Annotated, NotRequired

from langchain.agents.middleware.types import AgentState
from typing_extensions import TypedDict


class FileData(TypedDict):
    """Data structure for storing file contents."""

    content: list[str]
    created_at: str
    modified_at: str


def files_reducer(
    left: dict[str, FileData] | None, right: dict[str, FileData | None]
) -> dict[str, FileData]:
    """Custom reducer that merges file updates.

    Args:
        left: Existing files dict.
        right: New files dict to merge (`None` values delete files).

    Returns:
        Merged `dict` where right overwrites left for matching keys.
    """
    if left is None:
        return {k: v for k, v in right.items() if v is not None}

    result = {**left}
    for k, v in right.items():
        if v is None:
            result.pop(k, None)
        else:
            result[k] = v
    return result


class AnthropicToolsState(AgentState):
    """State schema for Anthropic text editor and memory tools."""

    text_editor_files: NotRequired[Annotated[dict[str, FileData], files_reducer]]
    memory_files: NotRequired[Annotated[dict[str, FileData], files_reducer]]
