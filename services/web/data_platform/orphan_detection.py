from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from services.sandbox.providers import get_provider


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def detect_orphans() -> list[dict[str, Any]]:
    """
    Query all provider APIs for instances.
    Cross-reference with sandbox.db sessions.
    Return instances not tracked in sandbox.db.
    """
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return []

    orphans = []

    with _connect(db_path) as conn:
        # Get all known instance_ids from sandbox_leases
        known_instances = {
            row["current_instance_id"]
            for row in conn.execute(
                "SELECT current_instance_id FROM sandbox_leases WHERE current_instance_id IS NOT NULL"
            ).fetchall()
        }

        # Get all provider names from sandbox_leases
        providers = {
            row["provider_name"]
            for row in conn.execute("SELECT DISTINCT provider_name FROM sandbox_leases").fetchall()
        }

    # Query each provider for all instances
    for provider_name in providers:
        try:
            provider = get_provider(provider_name)
            # @@@todo - Add list_all_instances() method to provider interface
            # For now, return empty list as providers don't expose this yet
            # instances = provider.list_all_instances()
            instances = []

            for instance in instances:
                instance_id = instance.get("id") or instance.get("instance_id")
                if instance_id and instance_id not in known_instances:
                    orphans.append(
                        {
                            "provider": provider_name,
                            "instance_id": instance_id,
                            "created_at": instance.get("created_at"),
                            "state": instance.get("state") or instance.get("status"),
                            "metadata": instance,
                        }
                    )
        except Exception as e:
            # Log but don't fail - continue checking other providers
            print(f"Failed to query provider {provider_name}: {e}")
            continue

    return orphans


async def adopt_orphan(provider: str, instance_id: str, thread_id: str) -> dict[str, Any]:
    """
    Create a session record in sandbox.db for an orphan instance.
    Link it to the specified thread_id.
    """
    # @@@todo - Implement adoption logic
    # This requires:
    # 1. Create a new lease record with the instance_id
    # 2. Create a new terminal record
    # 3. Create a new chat_session record linking thread_id to the lease
    # 4. Update provider state to track the instance
    raise NotImplementedError("Orphan adoption not yet implemented")


async def destroy_orphan(provider: str, instance_id: str) -> dict[str, Any]:
    """
    Call provider API to destroy the instance.
    Do NOT create a session record.
    """
    try:
        provider_obj = get_provider(provider)
        # @@@todo - Add destroy_instance() method to provider interface
        # result = await provider_obj.destroy_instance(instance_id)
        raise NotImplementedError("Provider destroy_instance() not yet implemented")
    except Exception as e:
        return {"success": False, "error": str(e)}
