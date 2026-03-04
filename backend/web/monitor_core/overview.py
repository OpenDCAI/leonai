"""Resource overview aggregation for monitor core."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from backend.web.core.config import DB_PATH
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


def _member_name_map() -> dict[str, str]:
    try:
        from backend.web.services.member_service import list_members

        members = list_members()
    except Exception:
        return {}

    mapping: dict[str, str] = {}
    for member in members:
        member_id = str(member.get("id") or "").strip()
        member_name = str(member.get("name") or "").strip()
        if member_id and member_name:
            mapping[member_id] = member_name
    return mapping


def _thread_agent_refs(thread_ids: list[str]) -> dict[str, str]:
    unique_thread_ids = sorted({tid for tid in thread_ids if tid})
    if not unique_thread_ids or not DB_PATH.exists():
        return {}

    placeholders = ",".join(["?"] * len(unique_thread_ids))
    with sqlite3.connect(str(DB_PATH), timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='thread_config' LIMIT 1"
        ).fetchone()
        if table is None:
            return {}

        rows = conn.execute(
            f"SELECT thread_id, agent FROM thread_config WHERE thread_id IN ({placeholders})",
            unique_thread_ids,
        ).fetchall()

    refs: dict[str, str] = {}
    for row in rows:
        thread_id = str(row["thread_id"] or "").strip()
        agent_ref = str(row["agent"] or "").strip()
        if thread_id and agent_ref:
            refs[thread_id] = agent_ref
    return refs


def _thread_owners(thread_ids: list[str]) -> dict[str, dict[str, str | None]]:
    refs = _thread_agent_refs(thread_ids)
    member_names = _member_name_map()

    owners: dict[str, dict[str, str | None]] = {}
    for thread_id in thread_ids:
        agent_ref = refs.get(thread_id)
        if not agent_ref:
            owners[thread_id] = {"agent_id": None, "agent_name": "Leon"}
            continue

        # @@@agent-name-resolution - thread_config.agent may be member id or direct display name.
        owners[thread_id] = {
            "agent_id": agent_ref,
            "agent_name": member_names.get(agent_ref, agent_ref),
        }
    return owners


def list_resource_providers() -> dict[str, Any]:
    # @@@overview-fast-path - avoid provider-network calls; overview uses DB session snapshot.
    sessions = _list_sessions_fast()
    grouped_sessions: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        # @@@provider-instance-identity - session.provider is config-instance name (not provider kind).
        provider_instance = str(session.get("provider") or "local")
        grouped_sessions.setdefault(provider_instance, []).append(session)

    owners = _thread_owners([str(session.get("thread_id") or "") for session in sessions])

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
            thread_id = str(session.get("thread_id") or "")
            owner = owners.get(thread_id, {"agent_id": None, "agent_name": "Leon"})
            normalized_sessions.append(
                {
                    "id": str(session.get("session_id") or ""),
                    "threadId": thread_id,
                    "agentId": str(owner.get("agent_id") or ""),
                    "agentName": str(owner.get("agent_name") or "Leon"),
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
