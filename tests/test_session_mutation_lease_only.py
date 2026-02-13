import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

# services.web depends on FastAPI, which is intentionally not a hard dependency of leonai.
pytest.importorskip("fastapi")

from services.web import main as web_main


def test_mutate_session_auto_adopts_orphan_then_mutates(monkeypatch):
    lease = MagicMock()
    lease.lease_id = "lease-adopted"
    lease.pause_instance.return_value = True
    lease_store = MagicMock()
    lease_store.get.return_value = None
    lease_store.adopt_instance.return_value = lease
    manager_provider = object()
    manager = SimpleNamespace(provider=manager_provider, lease_store=lease_store)
    session = {
        "session_id": "sess-1",
        "provider": "e2b",
        "thread_id": "(orphan)",
        "lease_id": None,
        "status": "running",
    }

    monkeypatch.setattr(web_main, "_init_providers_and_managers", lambda: ({}, {"e2b": manager}))
    monkeypatch.setattr(web_main, "_load_all_sessions", lambda _m: [session])
    monkeypatch.setattr(web_main, "_find_session_and_manager", lambda *_a, **_k: (session, manager))

    result = web_main._mutate_sandbox_session(session_id="sess-1", action="pause", provider_hint="e2b")
    assert result["ok"] is True
    assert result["mode"] == "manager_lease"
    assert result["lease_id"] == "lease-adopted"
    lease_store.adopt_instance.assert_called_once()
    lease.pause_instance.assert_called_once_with(manager_provider)


def test_mutate_session_uses_lease_with_manager_provider(monkeypatch):
    lease = MagicMock()
    lease.pause_instance.return_value = True
    lease_store = MagicMock()
    lease_store.get.return_value = lease
    manager_provider = object()
    manager = SimpleNamespace(provider=manager_provider, lease_store=lease_store)
    session = {
        "session_id": "sess-2",
        "provider": "e2b",
        "thread_id": "(untracked)",
        "lease_id": "lease-2",
    }

    monkeypatch.setattr(web_main, "_init_providers_and_managers", lambda: ({}, {"e2b": manager}))
    monkeypatch.setattr(web_main, "_load_all_sessions", lambda _m: [session])
    monkeypatch.setattr(web_main, "_find_session_and_manager", lambda *_a, **_k: (session, manager))

    result = web_main._mutate_sandbox_session(session_id="sess-2", action="pause", provider_hint="e2b")
    assert result["ok"] is True
    assert result["mode"] == "manager_lease"
    lease.pause_instance.assert_called_once_with(manager_provider)
