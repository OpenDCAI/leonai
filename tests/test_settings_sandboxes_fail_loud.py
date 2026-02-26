import asyncio

import pytest
from fastapi import HTTPException

from backend.web.routers import settings as settings_router


def test_list_sandbox_configs_fails_loud_on_invalid_json(tmp_path, monkeypatch):
    sandbox_dir = tmp_path / "sandboxes"
    sandbox_dir.mkdir()
    (sandbox_dir / "broken.json").write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(settings_router, "SANDBOXES_DIR", sandbox_dir)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(settings_router.list_sandbox_configs())

    assert exc_info.value.status_code == 500
    assert "broken.json" in str(exc_info.value.detail)
