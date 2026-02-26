"""Runtime wiring helpers for storage strategy selection."""

from __future__ import annotations

import importlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Literal

from core.storage.container import StorageContainer

StorageStrategy = Literal["sqlite", "supabase"]


def build_storage_container(
    *,
    main_db_path: str | Path | None = None,
    eval_db_path: str | Path | None = None,
    strategy: str | None = None,
    supabase_client: Any | None = None,
    supabase_client_factory: str | None = None,
    env: Mapping[str, str] | None = None,
) -> StorageContainer:
    """Build a runtime storage container from config/environment."""
    env_map = env if env is not None else os.environ
    raw_strategy = strategy if strategy is not None else env_map.get("LEON_STORAGE_STRATEGY")
    resolved_strategy = _resolve_strategy(raw_strategy)

    if resolved_strategy == "sqlite":
        return StorageContainer(
            main_db_path=main_db_path,
            eval_db_path=eval_db_path,
            strategy="sqlite",
        )

    client = supabase_client
    if client is None:
        factory_ref = (
            supabase_client_factory
            if supabase_client_factory is not None
            else env_map.get("LEON_SUPABASE_CLIENT_FACTORY")
        )
        if not factory_ref:
            raise RuntimeError(
                "Supabase storage strategy requires runtime config. "
                "Set LEON_SUPABASE_CLIENT_FACTORY=<module>:<callable> "
                "or inject supabase_client explicitly."
            )
        factory = _load_factory(factory_ref)
        client = factory()

    _ensure_supabase_client(client)
    return StorageContainer(
        main_db_path=main_db_path,
        eval_db_path=eval_db_path,
        strategy="supabase",
        supabase_client=client,
    )


def _resolve_strategy(raw: str | None) -> StorageStrategy:
    value = (raw or "sqlite").strip().lower()
    if value in {"", "sqlite"}:
        return "sqlite"
    if value == "supabase":
        return "supabase"
    raise RuntimeError(
        f"Invalid LEON_STORAGE_STRATEGY value: {raw!r}. "
        "Supported values: sqlite, supabase."
    )


def _load_factory(factory_ref: str) -> Callable[[], Any]:
    module_name, sep, attr_name = factory_ref.partition(":")
    if not sep or not module_name or not attr_name:
        raise RuntimeError(
            "Invalid LEON_SUPABASE_CLIENT_FACTORY format. "
            "Expected '<module>:<callable>'."
        )

    # @@@factory-path-import - keep runtime client wiring pluggable without adding hard deps in core storage package.
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - failure path asserted via RuntimeError text
        raise RuntimeError(
            f"Failed to import supabase client factory module {module_name!r}: {exc}"
        ) from exc

    try:
        factory = getattr(module, attr_name)
    except AttributeError as exc:
        raise RuntimeError(
            f"Supabase client factory {factory_ref!r} is missing attribute {attr_name!r}."
        ) from exc

    if not callable(factory):
        raise RuntimeError(f"Supabase client factory {factory_ref!r} must be callable.")
    return factory


def _ensure_supabase_client(client: Any) -> None:
    if client is None:
        raise RuntimeError("Supabase client factory returned None.")
    table_method = getattr(client, "table", None)
    if not callable(table_method):
        raise RuntimeError(
            "Supabase client must expose a callable table(name) API. "
            "Check LEON_SUPABASE_CLIENT_FACTORY output."
        )
