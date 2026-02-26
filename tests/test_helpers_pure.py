from pathlib import Path

from backend.web.utils.helpers import extract_webhook_instance_id, resolve_local_workspace_path


def test_resolve_local_workspace_path_normalizes_relative_workspace_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace" / "nested").mkdir(parents=True)

    resolved = resolve_local_workspace_path(
        raw_path="nested",
        local_workspace_root=Path("workspace"),
    )

    assert resolved == (tmp_path / "workspace" / "nested").resolve()


def test_extract_webhook_instance_id_trims_surrounding_whitespace() -> None:
    assert extract_webhook_instance_id({"session_id": "  inst-123  "}) == "inst-123"
    assert extract_webhook_instance_id({"data": {"id": "\ninst-456\t"}}) == "inst-456"
