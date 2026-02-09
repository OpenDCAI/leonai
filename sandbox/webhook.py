"""Provider webhook payload parsing into lease observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class LeaseObservation:
    provider_name: str
    provider_instance_id: str
    status: str  # running | paused | detached | unknown
    observed_at: datetime | None
    event_type: str


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _str(v: Any) -> str:
    return v if isinstance(v, str) else ""


def _parse_e2b(payload: dict[str, Any]) -> LeaseObservation:
    event_type = _str(payload.get("type"))
    instance_id = _str(payload.get("sandboxId"))
    observed_at = _parse_dt(payload.get("timestamp"))
    if not event_type:
        raise ValueError("E2B webhook missing 'type'")
    if not instance_id:
        raise ValueError("E2B webhook missing 'sandboxId'")

    if event_type in {"sandbox.lifecycle.created", "sandbox.lifecycle.resumed", "sandbox.lifecycle.updated"}:
        status = "running"
    elif event_type == "sandbox.lifecycle.paused":
        status = "paused"
    elif event_type == "sandbox.lifecycle.killed":
        status = "detached"
    else:
        raise ValueError(f"Unsupported E2B event type: {event_type}")

    return LeaseObservation(
        provider_name="e2b",
        provider_instance_id=instance_id,
        status=status,
        observed_at=observed_at,
        event_type=event_type,
    )


def _parse_daytona(payload: dict[str, Any]) -> LeaseObservation:
    event_type = _str(payload.get("event"))
    data = payload.get("data")
    data_obj = data if isinstance(data, dict) else {}
    observed_at = _parse_dt(payload.get("timestamp"))
    if not event_type:
        raise ValueError("Daytona webhook missing 'event'")

    instance_id = _str(data_obj.get("sandboxId")) or _str(data_obj.get("sandbox_id")) or _str(data_obj.get("id"))
    if not instance_id:
        raise ValueError("Daytona webhook missing sandbox id in data")

    lower_event = event_type.lower()
    state = _str(data_obj.get("state")) or _str(data_obj.get("status"))
    lower_state = state.lower()

    if lower_event in {"sandbox.created", "sandbox.started", "sandbox.recovered"}:
        status = "running"
    elif lower_event in {"sandbox.stopped", "sandbox.paused", "sandbox.archived"}:
        status = "paused"
    elif lower_event in {"sandbox.deleted", "sandbox.removed", "sandbox.destroyed"}:
        status = "detached"
    elif lower_event == "sandbox.state.updated":
        if lower_state in {"running", "started"}:
            status = "running"
        elif lower_state in {"stopped", "paused", "archived"}:
            status = "paused"
        elif lower_state in {"deleted", "destroyed", "removed"}:
            status = "detached"
        else:
            raise ValueError(f"Unsupported Daytona state in sandbox.state.updated: {state}")
    else:
        raise ValueError(f"Unsupported Daytona event type: {event_type}")

    return LeaseObservation(
        provider_name="daytona",
        provider_instance_id=instance_id,
        status=status,
        observed_at=observed_at,
        event_type=event_type,
    )


def parse_provider_webhook(provider_name: str, payload: dict[str, Any]) -> LeaseObservation:
    """Parse webhook payload from a supported provider."""
    name = provider_name.strip().lower()
    if name == "e2b":
        return _parse_e2b(payload)
    if name == "daytona":
        return _parse_daytona(payload)
    raise ValueError(f"Unsupported webhook provider: {provider_name}")
