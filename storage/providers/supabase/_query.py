"""Shared query helpers for Supabase provider repos."""

from __future__ import annotations

from typing import Any


def rows(response: Any, operation: str) -> list[dict[str, Any]]:
    """Extract and validate row list from a Supabase response."""
    if isinstance(response, dict):
        payload = response.get("data")
    else:
        payload = getattr(response, "data", None)
    if payload is None:
        raise RuntimeError(
            f"Supabase repo expected `.data` payload for {operation}. "
            "Check Supabase client compatibility."
        )
    if not isinstance(payload, list):
        raise RuntimeError(
            f"Supabase repo expected list payload for {operation}, "
            f"got {type(payload).__name__}."
        )
    for row in payload:
        if not isinstance(row, dict):
            raise RuntimeError(
                f"Supabase repo expected dict row for {operation}, "
                f"got {type(row).__name__}."
            )
    return payload


def order(query: Any, column: str, *, desc: bool, operation: str) -> Any:
    if not hasattr(query, "order"):
        raise RuntimeError(
            f"Supabase repo expects query.order(column, desc=bool) for {operation}. "
            "Provide a supabase-py compatible query object."
        )
    return query.order(column, desc=desc)


def limit(query: Any, value: int, operation: str) -> Any:
    if not hasattr(query, "limit"):
        raise RuntimeError(
            f"Supabase repo expects query.limit(value) for {operation}. "
            "Provide a supabase-py compatible query object."
        )
    return query.limit(value)


def in_(query: Any, column: str, values: list[str], operation: str) -> Any:
    if not hasattr(query, "in_"):
        raise RuntimeError(
            f"Supabase repo expects query.in_(column, values) for {operation}. "
            "Provide a supabase-py compatible query object."
        )
    return query.in_(column, values)


def gt(query: Any, column: str, value: Any, operation: str) -> Any:
    if not hasattr(query, "gt"):
        raise RuntimeError(
            f"Supabase repo expects query.gt(column, value) for {operation}. "
            "Provide a supabase-py compatible query object."
        )
    return query.gt(column, value)


def gte(query: Any, column: str, value: Any, operation: str) -> Any:
    if not hasattr(query, "gte"):
        raise RuntimeError(
            f"Supabase repo expects query.gte(column, value) for {operation}. "
            "Provide a supabase-py compatible query object."
        )
    return query.gte(column, value)
