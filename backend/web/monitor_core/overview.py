"""Resource overview aggregation for monitor core."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.web.core.config import SANDBOXES_DIR
from backend.web.services.sandbox_service import available_sandbox_types
from sandbox.config import SandboxConfig

from .control import list_sessions


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


def _read_provider_name(config_name: str) -> str:
    if config_name == "local":
        return "local"
    config_path = SANDBOXES_DIR / f"{config_name}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Sandbox config not found: {config_path}")
    payload = json.loads(config_path.read_text())
    provider = str(payload.get("provider") or "").strip()
    if not provider:
        raise RuntimeError(f"Sandbox config missing provider: {config_path}")
    return provider


def _resolve_type(provider_name: str, config_name: str) -> str:
    if provider_name != "daytona" or config_name == "local":
        entry = PROVIDER_CATALOG.get(provider_name)
        return entry.provider_type if entry else "container"

    config = SandboxConfig.load(config_name)
    # @@@daytona-target-kind - one provider type maps to cloud/self-host via config target.
    target = (config.daytona.target or "").strip().lower()
    return "cloud" if target == "cloud" else "container"


def _resolve_console_url(provider_name: str, config_name: str) -> str | None:
    if provider_name == "agentbay":
        return "https://agentbay.console.aliyun.com/overview"
    if provider_name == "e2b":
        return "https://e2b.dev"
    if provider_name == "daytona":
        config = SandboxConfig.load(config_name)
        if (config.daytona.target or "").strip().lower() == "cloud":
            return "https://app.daytona.io"
        api_url = (config.daytona.api_url or "").strip().rstrip("/")
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


def list_resource_providers() -> dict[str, Any]:
    sessions = list_sessions()
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
                "capabilities": catalog.capabilities,
                "telemetry": {
                    "running": {"used": running_count, "limit": None, "unit": "sandbox", "source": "derived"},
                    "cpu": {"used": None, "limit": None, "unit": "cores", "source": "unknown"},
                    "memory": {"used": None, "limit": None, "unit": "GB", "source": "unknown"},
                    "disk": {"used": None, "limit": None, "unit": "GB", "source": "unknown"},
                },
                "consoleUrl": _resolve_console_url(provider_name, config_name),
                "sessions": normalized_sessions,
            }
        )

    return {"providers": providers}
