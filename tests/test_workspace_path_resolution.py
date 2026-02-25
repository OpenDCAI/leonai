from pathlib import Path

from backend.web.utils.helpers import resolve_local_workspace_path


def test_resolve_local_workspace_path_accepts_relative_workspace_root(tmp_path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.chdir(tmp_path)

    resolved = resolve_local_workspace_path("src/main.py", local_workspace_root=Path("workspace"))

    assert resolved == (workspace_root / "src/main.py").resolve()
