"""Resource overview aggregation for monitor core."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from backend.web.core.config import SANDBOXES_DIR
from backend.web.services.sandbox_service import available_sandbox_types
from sandbox.metadata import get_provider_catalog, resolve_console_url, resolve_provider_name, resolve_provider_type
from sandbox.provider import ProviderCapability, RESOURCE_CAPABILITY_KEYS
from sandbox.db import DEFAULT_DB_PATH

def _declared_capabilities(provider_name: str) -> dict[str, bool]:
    if provider_name == "local":
        from sandbox.local import LocalSessionProvider

        declared = getattr(LocalSessionProvider, "CAPABILITY", None)
    elif provider_name == "docker":
        from sandbox.providers.docker import DockerProvider

        declared = getattr(DockerProvider, "CAPABILITY", None)
    elif provider_name == "e2b":
        from sandbox.providers.e2b import E2BProvider

        declared = getattr(E2BProvider, "CAPABILITY", None)
    elif provider_name == "daytona":
        from sandbox.providers.daytona import DaytonaProvider

        declared = getattr(DaytonaProvider, "CAPABILITY", None)
    elif provider_name == "agentbay":
        from sandbox.providers.agentbay import AgentBayProvider

        declared = getattr(AgentBayProvider, "CAPABILITY", None)
    else:
        raise RuntimeError(f"Unsupported provider type: {provider_name}")

    if not isinstance(declared, ProviderCapability):
        raise RuntimeError(f"Provider {provider_name} missing class CAPABILITY declaration")

    # @@@capability-contract-surface - monitor consumes only agreed capability keys for stable front-end shape.
    normalized = declared.declared_resource_capabilities()
    return {key: normalized[key] for key in RESOURCE_CAPABILITY_KEYS}
def _to_resource_status(available: bool, running_count: int) -> str:
    if not available:
        return "unavailable"
    return "active" if running_count > 0 else "ready"


def _to_session_status(raw_status: str | None) -> str:
    status = (raw_status or "").strip().lower()
    if status == "paused":
        return "paused"
    if status in {"destroyed", "stopped", "closed", "terminated", "error"}:
        return "stopped"
    return "running"


def _metric(used: float | int | None, limit: float | int | None, unit: str, source: str, freshness: str) -> dict[str, Any]:
    return {
        "used": used,
        "limit": limit,
        "unit": unit,
        "source": source,
        "freshness": freshness,
    }


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _list_sessions_fast() -> list[dict[str, Any]]:
    if not DEFAULT_DB_PATH.exists():
        return []

    with sqlite3.connect(str(DEFAULT_DB_PATH), timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        if not _table_exists(conn, "chat_sessions"):
            return []
        if not _table_exists(conn, "sandbox_leases"):
            return []

        rows = conn.execute(
            """
            SELECT
                cs.chat_session_id AS session_id,
                cs.thread_id AS thread_id,
                cs.status AS status,
                cs.started_at AS created_at,
                sl.provider_name AS provider
            FROM chat_sessions cs
            LEFT JOIN sandbox_leases sl ON cs.lease_id = sl.lease_id
            ORDER BY cs.started_at DESC
            """
        ).fetchall()

    sessions: list[dict[str, Any]] = []
    for row in rows:
        sessions.append(
            {
                "provider": row["provider"] or "local",
                "session_id": row["session_id"],
                "thread_id": row["thread_id"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
        )
    return sessions


def list_resource_providers() -> dict[str, Any]:
    # @@@overview-fast-path - avoid provider-network calls; overview uses DB session snapshot.
    sessions = _list_sessions_fast()
    grouped_sessions: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        # @@@provider-instance-identity - session.provider is config-instance name (not provider kind).
        provider_instance = str(session.get("provider") or "local")
        grouped_sessions.setdefault(provider_instance, []).append(session)

    providers: list[dict[str, Any]] = []
    for item in available_sandbox_types():
        config_name = str(item["name"])
        available = bool(item.get("available"))
        provider_name = resolve_provider_name(config_name, sandboxes_dir=SANDBOXES_DIR)
        catalog = get_provider_catalog(provider_name)

        provider_sessions = grouped_sessions.get(config_name, [])
        normalized_sessions: list[dict[str, Any]] = []
        running_count = 0
        for session in provider_sessions:
            normalized = _to_session_status(session.get("status"))
            if normalized == "running":
                running_count += 1
            normalized_sessions.append(
                {
                    "id": str(session.get("session_id") or ""),
                    "threadId": str(session.get("thread_id") or ""),
                    "agentId": "default",
                    "agentName": "Default",
                    "status": normalized,
                    "startedAt": str(session.get("created_at") or ""),
                }
            )

        providers.append(
            {
                "id": config_name,
                "name": config_name,
                "description": catalog.description,
                "vendor": catalog.vendor,
                "type": resolve_provider_type(provider_name, config_name, sandboxes_dir=SANDBOXES_DIR),
                "status": _to_resource_status(available, running_count),
                "unavailableReason": item.get("reason"),
                "error": (
                    {"code": "PROVIDER_UNAVAILABLE", "message": str(item.get("reason"))}
                    if not available and item.get("reason")
                    else None
                ),
                "capabilities": _declared_capabilities(provider_name),
                "telemetry": {
                    "running": _metric(running_count, None, "sandbox", "sandbox_db", "cached"),
                    "cpu": _metric(None, None, "cores", "unknown", "stale"),
                    "memory": _metric(None, None, "GB", "unknown", "stale"),
                    "disk": _metric(None, None, "GB", "unknown", "stale"),
                },
                "consoleUrl": resolve_console_url(provider_name, config_name, sandboxes_dir=SANDBOXES_DIR),
                "sessions": normalized_sessions,
            }
        )

    summary = {
        "snapshot_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_providers": len(providers),
        "active_providers": len([p for p in providers if p.get("status") == "active"]),
        "unavailable_providers": len([p for p in providers if p.get("status") == "unavailable"]),
        "running_sessions": sum(int((p.get("telemetry") or {}).get("running", {}).get("used") or 0) for p in providers),
    }

    return {"summary": summary, "providers": providers}
