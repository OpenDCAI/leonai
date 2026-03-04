import sqlite3
import json
from pathlib import Path

from backend.web.monitor_core import overview


def test_list_resource_providers_maps_status_and_metric_metadata(tmp_path, monkeypatch):
    (tmp_path / "docker_dev.json").write_text(json.dumps({"provider": "docker"}))

    monkeypatch.setattr(overview, "SANDBOXES_DIR", tmp_path)
    db_path = tmp_path / "leon.db"
    monkeypatch.setattr(overview, "DB_PATH", Path(db_path))
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE thread_config (thread_id TEXT PRIMARY KEY, agent TEXT)")
        conn.execute("INSERT INTO thread_config (thread_id, agent) VALUES (?, ?)", ("thread-local-1", "member-1"))
        conn.commit()
    monkeypatch.setattr(overview, "_member_name_map", lambda: {"member-1": "Alice"})
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
    assert local["sessions"][0]["threadId"] == "thread-local-1"
    assert local["sessions"][0]["agentId"] == "member-1"
    assert local["sessions"][0]["agentName"] == "Alice"

    docker = next(item for item in payload["providers"] if item["id"] == "docker_dev")
    assert docker["status"] == "unavailable"
    assert docker["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert docker["sessions"][0]["status"] == "paused"
    assert docker["sessions"][0]["agentName"] == "Leon"


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


def test_list_resource_providers_prefers_config_console_url_override(tmp_path, monkeypatch):
    (tmp_path / "daytona_selfhost.json").write_text(
        json.dumps(
            {
                "provider": "daytona",
                "console_url": "https://ops.example.com/daytona",
                "daytona": {"target": "local", "api_url": "https://daytona.example.com/api"},
            }
        )
    )

    monkeypatch.setattr(overview, "SANDBOXES_DIR", tmp_path)
    monkeypatch.setattr(
        overview,
        "available_sandbox_types",
        lambda: [{"name": "daytona_selfhost", "available": True}],
    )
    monkeypatch.setattr(overview, "_list_sessions_fast", lambda: [])

    payload = overview.list_resource_providers()
    provider = payload["providers"][0]
    assert provider["id"] == "daytona_selfhost"
    assert provider["consoleUrl"] == "https://ops.example.com/daytona"
    assert provider["type"] == "container"


def test_thread_owner_uses_agent_ref_as_name_when_member_lookup_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "leon.db"
    monkeypatch.setattr(overview, "DB_PATH", Path(db_path))
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE thread_config (thread_id TEXT PRIMARY KEY, agent TEXT)")
        conn.execute("INSERT INTO thread_config (thread_id, agent) VALUES (?, ?)", ("thread-1", "Lex"))
        conn.commit()
    monkeypatch.setattr(overview, "_member_name_map", lambda: {})

    owners = overview._thread_owners(["thread-1", "thread-2"])
    assert owners["thread-1"]["agent_id"] == "Lex"
    assert owners["thread-1"]["agent_name"] == "Lex"
    assert owners["thread-2"]["agent_id"] is None
    assert owners["thread-2"]["agent_name"] == "Leon"
