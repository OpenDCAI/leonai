from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


async def pause_session(thread_id: str) -> dict[str, Any]:
    """
    Set desired_state = 'paused' for session.
    Call provider pause API.
    Return operation result + convergence status.
    """
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return {"success": False, "error": "sandbox.db not found"}

    with _connect(db_path) as conn:
        # Get session info
        session = conn.execute(
            """
            SELECT cs.lease_id, sl.provider_name, sl.current_instance_id, sl.observed_state
            FROM chat_sessions cs
            JOIN sandbox_leases sl ON sl.lease_id = cs.lease_id
            WHERE cs.thread_id = ? AND cs.status IN ('active', 'idle')
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()

        if not session:
            return {"success": False, "error": "No active session found for thread"}

        lease_id = session["lease_id"]
        provider_name = session["provider_name"]
        instance_id = session["current_instance_id"]

        # Update desired_state in sandbox_leases
        conn.execute(
            "UPDATE sandbox_leases SET desired_state = 'paused' WHERE lease_id = ?",
            (lease_id,),
        )
        conn.commit()

    # Call provider pause API
    try:
        # @@@todo - Import provider dynamically and call pause
        # provider = get_provider(provider_name)
        # await provider.pause_instance(instance_id)

        # Poll for convergence (max 30s)
        converged = False
        for _ in range(30):
            with _connect(db_path) as conn:
                state = conn.execute(
                    "SELECT observed_state FROM sandbox_leases WHERE lease_id = ?",
                    (lease_id,),
                ).fetchone()
                if state and state["observed_state"] == "paused":
                    converged = True
                    break
            time.sleep(1)

        return {
            "success": True,
            "converged": converged,
            "thread_id": thread_id,
            "lease_id": lease_id,
            "desired_state": "paused",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def resume_session(thread_id: str) -> dict[str, Any]:
    """Set desired_state = 'running', call provider resume."""
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return {"success": False, "error": "sandbox.db not found"}

    with _connect(db_path) as conn:
        session = conn.execute(
            """
            SELECT cs.lease_id, sl.provider_name, sl.current_instance_id
            FROM chat_sessions cs
            JOIN sandbox_leases sl ON sl.lease_id = cs.lease_id
            WHERE cs.thread_id = ? AND cs.status IN ('idle', 'paused')
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()

        if not session:
            return {"success": False, "error": "No paused/idle session found for thread"}

        lease_id = session["lease_id"]
        provider_name = session["provider_name"]
        instance_id = session["current_instance_id"]

        conn.execute(
            "UPDATE sandbox_leases SET desired_state = 'running' WHERE lease_id = ?",
            (lease_id,),
        )
        conn.commit()

    try:
        # @@@todo - Import provider dynamically and call resume
        # provider = get_provider(provider_name)
        # await provider.resume_instance(instance_id)

        converged = False
        for _ in range(30):
            with _connect(db_path) as conn:
                state = conn.execute(
                    "SELECT observed_state FROM sandbox_leases WHERE lease_id = ?",
                    (lease_id,),
                ).fetchone()
                if state and state["observed_state"] == "running":
                    converged = True
                    break
            time.sleep(1)

        return {
            "success": True,
            "converged": converged,
            "thread_id": thread_id,
            "lease_id": lease_id,
            "desired_state": "running",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def destroy_session(thread_id: str) -> dict[str, Any]:
    """Set desired_state = 'destroyed', call provider destroy."""
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return {"success": False, "error": "sandbox.db not found"}

    with _connect(db_path) as conn:
        session = conn.execute(
            """
            SELECT cs.lease_id, cs.chat_session_id, sl.provider_name, sl.current_instance_id
            FROM chat_sessions cs
            JOIN sandbox_leases sl ON sl.lease_id = cs.lease_id
            WHERE cs.thread_id = ?
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()

        if not session:
            return {"success": False, "error": "No session found for thread"}

        lease_id = session["lease_id"]
        chat_session_id = session["chat_session_id"]
        provider_name = session["provider_name"]
        instance_id = session["current_instance_id"]

        # Update desired_state
        conn.execute(
            "UPDATE sandbox_leases SET desired_state = 'destroyed' WHERE lease_id = ?",
            (lease_id,),
        )
        # Mark session as ended
        conn.execute(
            "UPDATE chat_sessions SET status = 'ended', ended_at = datetime('now'), close_reason = 'operator_destroy' WHERE chat_session_id = ?",
            (chat_session_id,),
        )
        conn.commit()

    try:
        # @@@todo - Import provider dynamically and call destroy
        # provider = get_provider(provider_name)
        # await provider.destroy_instance(instance_id)

        return {
            "success": True,
            "thread_id": thread_id,
            "lease_id": lease_id,
            "chat_session_id": chat_session_id,
            "desired_state": "destroyed",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
