from backend.web.monitor_core import resource_probe


class _FakeProvider:
    def get_metrics(self, session_id: str):
        return None


def test_refresh_resource_snapshots_probes_unique_leases(monkeypatch):
    monkeypatch.setattr(resource_probe, "ensure_resource_snapshot_table", lambda: None)
    monkeypatch.setattr(
        resource_probe,
        "init_providers_and_managers",
        lambda: (
            {"p1": _FakeProvider()},
            {"p1": object()},
        ),
    )
    monkeypatch.setattr(
        resource_probe,
        "load_all_sessions",
        lambda _: [
            {"provider": "p1", "session_id": "s-1", "lease_id": "l-1", "status": "running"},
            {"provider": "p1", "session_id": "s-2", "lease_id": "l-1", "status": "paused"},
            {"provider": "p1", "session_id": "s-3", "lease_id": "l-2", "status": "paused"},
        ],
    )

    calls: list[dict] = []

    def _fake_probe(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "error": None}

    monkeypatch.setattr(resource_probe, "probe_and_upsert_for_instance", _fake_probe)

    result = resource_probe.refresh_resource_snapshots()
    assert result["probed"] == 2
    assert result["errors"] == 0
    assert {call["lease_id"] for call in calls} == {"l-1", "l-2"}
    assert calls[0]["probe_mode"] in {"running_runtime", "non_running_sdk"}
