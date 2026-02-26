from pathlib import Path

from backend.web.utils.helpers import resolve_local_workspace_path


def test_resolve_local_workspace_path_normalizes_relative_workspace_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace" / "nested").mkdir(parents=True)

    resolved = resolve_local_workspace_path(
        raw_path="nested",
        local_workspace_root=Path("workspace"),
    )

    assert resolved == (tmp_path / "workspace" / "nested").resolve()
