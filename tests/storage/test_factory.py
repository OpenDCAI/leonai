import pytest

factory = pytest.importorskip("core.storage.factory")
StorageConfigError = factory.StorageConfigError
validate_storage_startup = factory.validate_storage_startup


def test_supabase_pool_mode_whitespace_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("LEON_STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("LEON_SUPABASE_DSN", "postgresql://postgres:pw@localhost:5432/postgres")
    monkeypatch.setenv("LEON_SUPABASE_POOL_MODE", "   ")
    monkeypatch.setenv("LEON_SUPABASE_SERVICE_ROLE_KEY", "service-role")

    with pytest.raises(StorageConfigError, match="Missing required env var: LEON_SUPABASE_POOL_MODE"):
        validate_storage_startup()
