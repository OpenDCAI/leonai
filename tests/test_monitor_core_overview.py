import json

from backend.web.monitor_core import overview


def test_list_resource_providers_maps_status_and_metric_metadata(tmp_path, monkeypatch):
    (tmp_path / "docker_dev.json").write_text(json.dumps({"provider": "docker"}))

    monkeypatch.setattr(overview, "SANDBOXES_DIR", tmp_path)
    monkeypatch.setattr(
        overview,
        "available_sandbox_types",
        lambda: [
            {"name": "local", "available": True},
            {"name": "docker_dev", "available": False, "reason": "docker daemon down"},
        ],
    )
    monkeypatch.setattr(
        overview,
        "_list_sessions_fast",
        lambda: [
            {
                "provider": "local",
                "session_id": "sess-local-1",
                "thread_id": "thread-local-1",
                "status": "running",
                "created_at": "2026-03-03T00:00:00",
            },
            {
                "provider": "docker_dev",
                "session_id": "sess-docker-1",
                "thread_id": "thread-docker-1",
                "status": "paused",
                "created_at": "2026-03-03T00:00:00",
            },
        ],
    )

    payload = overview.list_resource_providers()
    assert "summary" in payload
    assert "providers" in payload
    assert payload["summary"]["total_providers"] == 2
    assert payload["summary"]["active_providers"] == 1
    assert payload["summary"]["unavailable_providers"] == 1
    assert payload["summary"]["running_sessions"] == 1

    local = next(item for item in payload["providers"] if item["id"] == "local")
    assert local["status"] == "active"
    assert local["telemetry"]["running"]["used"] == 1
    assert local["telemetry"]["running"]["source"] == "sandbox_db"
    assert local["telemetry"]["running"]["freshness"] == "cached"

    docker = next(item for item in payload["providers"] if item["id"] == "docker_dev")
    assert docker["status"] == "unavailable"
    assert docker["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert docker["sessions"][0]["status"] == "paused"


def test_list_resource_providers_marks_ready_when_no_running_sessions(tmp_path, monkeypatch):
    (tmp_path / "e2b_test.json").write_text(json.dumps({"provider": "e2b"}))

    monkeypatch.setattr(overview, "SANDBOXES_DIR", tmp_path)
    monkeypatch.setattr(
        overview,
        "available_sandbox_types",
        lambda: [{"name": "e2b_test", "available": True}],
    )
    monkeypatch.setattr(overview, "_list_sessions_fast", lambda: [])

    payload = overview.list_resource_providers()
    assert len(payload["providers"]) == 1
    assert payload["summary"]["active_providers"] == 0
    assert payload["summary"]["running_sessions"] == 0

    e2b = payload["providers"][0]
    assert e2b["id"] == "e2b_test"
    assert e2b["status"] == "ready"
    assert e2b["telemetry"]["running"]["used"] == 0
    assert e2b["telemetry"]["cpu"]["freshness"] == "stale"
