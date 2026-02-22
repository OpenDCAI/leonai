import pytest
from fastapi import HTTPException

from backend.web.routers.settings import browse_filesystem


@pytest.mark.asyncio
async def test_browse_filesystem_keeps_404_for_missing_path(tmp_path):
    missing = tmp_path / "missing-dir"

    with pytest.raises(HTTPException) as exc_info:
        await browse_filesystem(path=str(missing))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Path does not exist"


@pytest.mark.asyncio
async def test_browse_filesystem_keeps_400_for_file_path(tmp_path):
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        await browse_filesystem(path=str(file_path))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Path is not a directory"
