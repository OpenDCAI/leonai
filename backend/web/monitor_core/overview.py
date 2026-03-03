"""Resource overview aggregation for monitor core."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.web.core.config import SANDBOXES_DIR
from backend.web.services.sandbox_service import available_sandbox_types
from sandbox.db import DEFAULT_DB_PATH


@dataclass(frozen=True)
class ProviderCatalogEntry:
    vendor: str | None
    description: str
    provider_type: str
    capabilities: dict[str, bool]


PROVIDER_CATALOG: dict[str, ProviderCatalogEntry] = {
    "local": ProviderCatalogEntry(
        vendor=None,
        description="Direct host access",
        provider_type="local",
        capabilities={
            "filesystem": True,
            "terminal": True,
            "metrics": False,
            "screenshot": False,
            "web": False,
            "process": False,
            "hooks": False,
            "snapshot": False,
        },
    ),
    "daytona": ProviderCatalogEntry(
        vendor="Daytona",
        description="Managed cloud or self-host Daytona sandboxes",
        provider_type="cloud",
        capabilities={
            "filesystem": True,
            "terminal": True,
            "metrics": True,
            "screenshot": False,
            "web": False,
            "process": True,
            "hooks": True,
            "snapshot": False,
        },
    ),
    "e2b": ProviderCatalogEntry(
        vendor="E2B",
        description="Cloud sandbox with runtime metrics",
        provider_type="cloud",
        capabilities={
            "filesystem": True,
            "terminal": True,
            "metrics": True,
            "screenshot": False,
            "web": False,
            "process": False,
            "hooks": False,
            "snapshot": True,
        },
    ),
    "agentbay": ProviderCatalogEntry(
        vendor="Alibaba Cloud",
        description="Remote Linux sandbox",
        provider_type="cloud",
        capabilities={
            "filesystem": True,
            "terminal": True,
            "metrics": True,
            "screenshot": True,
            "web": True,
            "process": True,
            "hooks": False,
            "snapshot": False,
        },
    ),
    "docker": ProviderCatalogEntry(
        vendor=None,
        description="Isolated container sandbox",
        provider_type="container",
        capabilities={
            "filesystem": True,
            "terminal": True,
            "metrics": True,
            "screenshot": False,
            "web": False,
            "process": True,
            "hooks": False,
            "snapshot": False,
        },
    ),
}


def _read_config_payload(config_name: str) -> dict[str, Any]:
    if config_name == "local":
        return {"provider": "local"}
    config_path = SANDBOXES_DIR / f"{config_name}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Sandbox config not found: {config_path}")
    payload = json.loads(config_path.read_text())
    if not isinstance(payload, dict):
        raise RuntimeError(f"Sandbox config is not a JSON object: {config_path}")
    return payload


def _read_provider_name(config_name: str) -> str:
    payload = _read_config_payload(config_name)
    provider = str(payload.get("provider") or "").strip()
    if not provider:
        raise RuntimeError(f"Sandbox config missing provider: {config_name}")
    return provider


def _resolve_type(provider_name: str, config_name: str) -> str:
    if provider_name != "daytona" or config_name == "local":
        entry = PROVIDER_CATALOG.get(provider_name)
        return entry.provider_type if entry else "container"

    # @@@daytona-target-kind - one provider type maps to cloud/self-host via config target.
    payload = _read_config_payload(config_name)
    daytona = payload.get("daytona") if isinstance(payload.get("daytona"), dict) else {}
    target = str(daytona.get("target") or "").strip().lower()
    return "cloud" if target == "cloud" else "container"


def _resolve_console_url(provider_name: str, config_name: str) -> str | None:
    if provider_name == "agentbay":
        return "https://agentbay.console.aliyun.com/overview"
    if provider_name == "e2b":
        return "https://e2b.dev"
    if provider_name == "daytona":
        payload = _read_config_payload(config_name)
        daytona = payload.get("daytona") if isinstance(payload.get("daytona"), dict) else {}
        target = str(daytona.get("target") or "").strip().lower()
        if target == "cloud":
            return "https://app.daytona.io"
        api_url = str(daytona.get("api_url") or "").strip().rstrip("/")
        return api_url[:-4] if api_url.endswith("/api") else api_url
    return None


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
        provider_name = _read_provider_name(config_name)
        catalog = PROVIDER_CATALOG.get(provider_name)
        if not catalog:
            raise RuntimeError(f"Unsupported provider type: {provider_name}")

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
                "type": _resolve_type(provider_name, config_name),
                "status": _to_resource_status(available, running_count),
                "unavailableReason": item.get("reason"),
                "error": (
                    {"code": "PROVIDER_UNAVAILABLE", "message": str(item.get("reason"))}
                    if not available and item.get("reason")
                    else None
                ),
                "capabilities": catalog.capabilities,
                "telemetry": {
                    "running": _metric(running_count, None, "sandbox", "sandbox_db", "cached"),
                    "cpu": _metric(None, None, "cores", "unknown", "stale"),
                    "memory": _metric(None, None, "GB", "unknown", "stale"),
                    "disk": _metric(None, None, "GB", "unknown", "stale"),
                },
                "consoleUrl": _resolve_console_url(provider_name, config_name),
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
