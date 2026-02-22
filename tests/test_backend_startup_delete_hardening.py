import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Keep repo root ahead of tests/ to avoid importing tests/config as top-level config package.
ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) in sys.path:
    sys.path.remove(str(TESTS_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.web.routers import threads as threads_router
from backend.web.services import sandbox_service


class _ManagerStub:
    def __init__(self):
        self.destroy_calls: list[str] = []

    def destroy_thread_resources(self, thread_id: str) -> bool:
        self.destroy_calls.append(thread_id)
        return True


def _make_app():
    state = SimpleNamespace(
        agent_pool={},
        thread_sandbox={},
        thread_cwd={},
        thread_locks={},
        thread_locks_guard=asyncio.Lock(),
        thread_tasks={},
    )
    return SimpleNamespace(state=state)


def test_verify_provider_dependency_parity_fails_loudly(tmp_path: Path, monkeypatch):
    sandboxes_dir = tmp_path / "sandboxes"
    sandboxes_dir.mkdir(parents=True, exist_ok=True)
    (sandboxes_dir / "e2b.json").write_text(
        """
        {
          "provider": "e2b",
          "e2b": { "api_key": "test-key" }
        }
        """.strip()
    )

    monkeypatch.setattr(sandbox_service, "SANDBOXES_DIR", sandboxes_dir)
    monkeypatch.setattr(
        sandbox_service.importlib.util,
        "find_spec",
        lambda module_name: None if module_name == "e2b" else object(),
    )

    with pytest.raises(RuntimeError) as exc_info:
        sandbox_service.verify_provider_dependency_parity()
    message = str(exc_info.value)
    assert "missing_module='e2b'" in message
    assert "pip install -r backend/web/requirements.txt" in message


def test_delete_thread_recovers_from_provider_manager_mismatch(monkeypatch):
    manager = _ManagerStub()
    app = _make_app()

    monkeypatch.setattr(threads_router, "resolve_thread_sandbox", lambda _app, _thread_id: "e2b")
    monkeypatch.setattr(threads_router, "delete_thread_in_db", lambda _thread_id: None)
    monkeypatch.setattr(sandbox_service, "init_providers_and_managers", lambda: ({}, {"e2b_primary": manager}))
    monkeypatch.setattr(
        sandbox_service,
        "lookup_sandbox_for_thread",
        lambda _thread_id, db_path=None: "e2b_primary",
    )

    result = asyncio.run(threads_router.delete_thread("thread-1", app=app))
    assert result["ok"] is True
    assert manager.destroy_calls == ["thread-1"]
