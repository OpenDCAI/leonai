"""Background probe for lease resource snapshots."""

from __future__ import annotations

from typing import Any

from backend.web.services.sandbox_service import init_providers_and_managers, load_all_sessions
from sandbox.resource_snapshot import ensure_resource_snapshot_table, probe_and_upsert_for_instance


def refresh_resource_snapshots() -> dict[str, Any]:
    ensure_resource_snapshot_table()
    providers, managers = init_providers_and_managers()
    sessions = load_all_sessions(managers)

    seen_leases: set[str] = set()
    probed = 0
    errors = 0
    for session in sessions:
        lease_id = str(session.get("lease_id") or "").strip()
        provider_key = str(session.get("provider") or "").strip()
        instance_id = str(session.get("session_id") or "").strip()
        status = str(session.get("status") or "unknown").strip().lower()

        if not lease_id or not provider_key or not instance_id:
            continue
        if lease_id in seen_leases:
            continue
        seen_leases.add(lease_id)

        provider = providers.get(provider_key)
        if provider is None:
            errors += 1
            continue

        probe_mode = "running_runtime" if status == "running" else "non_running_sdk"
        result = probe_and_upsert_for_instance(
            lease_id=lease_id,
            provider_name=provider_key,
            observed_state=status,
            probe_mode=probe_mode,
            provider=provider,
            instance_id=instance_id,
        )
        probed += 1
        if not result["ok"]:
            errors += 1

    return {"probed": probed, "errors": errors}
