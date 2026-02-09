"""Lifecycle state machine contracts for chat sessions and lease instances.

Fail-loud policy:
- Invalid state strings raise immediately.
- Illegal transitions raise immediately.
"""

from __future__ import annotations

from enum import StrEnum


class ChatSessionState(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
    CLOSED = "closed"
    FAILED = "failed"


class LeaseInstanceState(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    DETACHED = "detached"
    UNKNOWN = "unknown"


def parse_chat_session_state(value: str | None) -> ChatSessionState:
    if value is None:
        raise RuntimeError("ChatSession state is required")
    try:
        return ChatSessionState(value)
    except ValueError as e:
        raise RuntimeError(f"Invalid ChatSession state: {value}") from e


def parse_lease_instance_state(value: str | None) -> LeaseInstanceState:
    if value is None:
        return LeaseInstanceState.DETACHED
    lowered = value.lower()
    if lowered in {"deleted", "dead", "stopped"}:
        return LeaseInstanceState.DETACHED
    try:
        return LeaseInstanceState(lowered)
    except ValueError as e:
        raise RuntimeError(f"Invalid LeaseInstance state: {value}") from e


def assert_chat_session_transition(
    current: ChatSessionState | None,
    target: ChatSessionState,
    *,
    reason: str,
) -> None:
    if current is None:
        if target != ChatSessionState.ACTIVE:
            raise RuntimeError(f"Illegal chat session transition: <new> -> {target} ({reason})")
        return
    if current == target:
        return

    allowed: set[tuple[ChatSessionState, ChatSessionState]] = {
        (ChatSessionState.ACTIVE, ChatSessionState.IDLE),
        (ChatSessionState.ACTIVE, ChatSessionState.PAUSED),
        (ChatSessionState.ACTIVE, ChatSessionState.CLOSED),
        (ChatSessionState.ACTIVE, ChatSessionState.FAILED),
        (ChatSessionState.IDLE, ChatSessionState.ACTIVE),
        (ChatSessionState.IDLE, ChatSessionState.PAUSED),
        (ChatSessionState.IDLE, ChatSessionState.CLOSED),
        (ChatSessionState.IDLE, ChatSessionState.FAILED),
        (ChatSessionState.PAUSED, ChatSessionState.ACTIVE),
        (ChatSessionState.PAUSED, ChatSessionState.CLOSED),
        (ChatSessionState.PAUSED, ChatSessionState.FAILED),
        (ChatSessionState.FAILED, ChatSessionState.CLOSED),
    }
    if (current, target) not in allowed:
        raise RuntimeError(f"Illegal chat session transition: {current} -> {target} ({reason})")


def assert_lease_instance_transition(
    current: LeaseInstanceState | None,
    target: LeaseInstanceState,
    *,
    reason: str,
) -> None:
    if current is None:
        current = LeaseInstanceState.DETACHED
    if current == target:
        return

    allowed: set[tuple[LeaseInstanceState, LeaseInstanceState]] = {
        (LeaseInstanceState.DETACHED, LeaseInstanceState.RUNNING),
        (LeaseInstanceState.DETACHED, LeaseInstanceState.UNKNOWN),
        (LeaseInstanceState.RUNNING, LeaseInstanceState.PAUSED),
        (LeaseInstanceState.RUNNING, LeaseInstanceState.DETACHED),
        (LeaseInstanceState.RUNNING, LeaseInstanceState.UNKNOWN),
        (LeaseInstanceState.PAUSED, LeaseInstanceState.RUNNING),
        (LeaseInstanceState.PAUSED, LeaseInstanceState.DETACHED),
        (LeaseInstanceState.PAUSED, LeaseInstanceState.UNKNOWN),
        (LeaseInstanceState.UNKNOWN, LeaseInstanceState.RUNNING),
        (LeaseInstanceState.UNKNOWN, LeaseInstanceState.PAUSED),
        (LeaseInstanceState.UNKNOWN, LeaseInstanceState.DETACHED),
    }
    if (current, target) not in allowed:
        raise RuntimeError(f"Illegal lease transition: {current} -> {target} ({reason})")

