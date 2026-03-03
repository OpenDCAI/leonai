"""Control capabilities for monitor core."""

from typing import Any

from backend.web.services.sandbox_service import (
    find_session_and_manager,
    init_providers_and_managers,
    load_all_sessions,
    mutate_sandbox_session,
)


def list_sessions() -> list[dict[str, Any]]:
    """Return all sessions from configured providers."""
    _, managers = init_providers_and_managers()
    return load_all_sessions(managers)


def get_session_metrics(session_id: str, provider_name: str | None = None) -> dict[str, Any]:
    """Fetch runtime metrics for one session."""
    providers, managers = init_providers_and_managers()
    sessions = load_all_sessions(managers)
    session, _ = find_session_and_manager(sessions, managers, session_id, provider_name=provider_name)
    if not session:
        raise RuntimeError(f"Session not found: {session_id}")

    provider_obj = providers.get(session["provider"])
    if not provider_obj:
        return {"session_id": session["session_id"], "metrics": None}

    metrics = provider_obj.get_metrics(session["session_id"])
    web_url = provider_obj.get_web_url(session["session_id"]) if hasattr(provider_obj, "get_web_url") else None

    payload: dict[str, Any] = {"session_id": session["session_id"], "metrics": None, "web_url": web_url}
    if metrics:
        payload["metrics"] = {
            "cpu_percent": metrics.cpu_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "memory_total_mb": metrics.memory_total_mb,
            "disk_used_gb": metrics.disk_used_gb,
            "disk_total_gb": metrics.disk_total_gb,
            "network_rx_kbps": metrics.network_rx_kbps,
            "network_tx_kbps": metrics.network_tx_kbps,
        }
    return payload


def mutate_session(session_id: str, action: str, provider_hint: str | None = None) -> dict[str, Any]:
    """Mutate one sandbox session state."""
    return mutate_sandbox_session(session_id=session_id, action=action, provider_hint=provider_hint)
