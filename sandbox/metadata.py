"""Provider metadata and config-derived display resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderCatalogEntry:
    vendor: str | None
    description: str
    provider_type: str


PROVIDER_CATALOG: dict[str, ProviderCatalogEntry] = {
    "local": ProviderCatalogEntry(
        vendor=None,
        description="Direct host access",
        provider_type="local",
    ),
    "daytona": ProviderCatalogEntry(
        vendor="Daytona",
        description="Managed cloud or self-host Daytona sandboxes",
        provider_type="cloud",
    ),
    "e2b": ProviderCatalogEntry(
        vendor="E2B",
        description="Cloud sandbox with runtime metrics",
        provider_type="cloud",
    ),
    "agentbay": ProviderCatalogEntry(
        vendor="Alibaba Cloud",
        description="Remote Linux sandbox",
        provider_type="cloud",
    ),
    "docker": ProviderCatalogEntry(
        vendor=None,
        description="Isolated container sandbox",
        provider_type="container",
    ),
}


def load_config_payload(config_name: str, *, sandboxes_dir: Path) -> dict[str, Any]:
    if config_name == "local":
        return {"provider": "local"}
    config_path = sandboxes_dir / f"{config_name}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Sandbox config not found: {config_path}")
    payload = json.loads(config_path.read_text())
    if not isinstance(payload, dict):
        raise RuntimeError(f"Sandbox config is not a JSON object: {config_path}")
    return payload


def resolve_provider_name(config_name: str, *, sandboxes_dir: Path) -> str:
    payload = load_config_payload(config_name, sandboxes_dir=sandboxes_dir)
    provider = str(payload.get("provider") or "").strip()
    if not provider:
        raise RuntimeError(f"Sandbox config missing provider: {config_name}")
    return provider


def get_provider_catalog(provider_name: str) -> ProviderCatalogEntry:
    entry = PROVIDER_CATALOG.get(provider_name)
    if not entry:
        raise RuntimeError(f"Unsupported provider type: {provider_name}")
    return entry


def resolve_provider_type(provider_name: str, config_name: str, *, sandboxes_dir: Path) -> str:
    if provider_name != "daytona" or config_name == "local":
        return get_provider_catalog(provider_name).provider_type

    # @@@daytona-target-kind - one provider type maps to cloud/self-host via config target.
    payload = load_config_payload(config_name, sandboxes_dir=sandboxes_dir)
    daytona = payload.get("daytona") if isinstance(payload.get("daytona"), dict) else {}
    target = str(daytona.get("target") or "").strip().lower()
    return "cloud" if target == "cloud" else "container"


def resolve_console_url(provider_name: str, config_name: str, *, sandboxes_dir: Path) -> str | None:
    payload = load_config_payload(config_name, sandboxes_dir=sandboxes_dir)
    override = str(payload.get("console_url") or "").strip()
    if override:
        return override
    if provider_name == "agentbay":
        return "https://agentbay.console.aliyun.com/overview"
    if provider_name == "e2b":
        return "https://e2b.dev"
    if provider_name == "daytona":
        daytona = payload.get("daytona") if isinstance(payload.get("daytona"), dict) else {}
        target = str(daytona.get("target") or "").strip().lower()
        if target == "cloud":
            return "https://app.daytona.io"
        api_url = str(daytona.get("api_url") or "").strip().rstrip("/")
        return api_url[:-4] if api_url.endswith("/api") else api_url
    return None
