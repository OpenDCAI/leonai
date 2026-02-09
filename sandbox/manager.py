"""Sandbox session manager.

Orchestrates: Thread → ChatSession → Runtime → Terminal → Lease → Instance
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from sandbox.capability import SandboxCapability
from sandbox.chat_session import ChatSessionManager, ChatSessionPolicy
from sandbox.db import DEFAULT_DB_PATH
from sandbox.lease import LeaseStore
from sandbox.provider import SandboxProvider
from sandbox.terminal import TerminalStore


def lookup_sandbox_for_thread(thread_id: str, db_path: Path | None = None) -> str | None:
    import sqlite3

    target_db = db_path or DEFAULT_DB_PATH
    if not target_db.exists():
        return None

    with sqlite3.connect(str(target_db), timeout=5) as conn:
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "abstract_terminals" not in existing or "sandbox_leases" not in existing:
            return None

        row = conn.execute(
            """
            SELECT sl.provider_name
            FROM abstract_terminals at
            JOIN sandbox_leases sl ON at.lease_id = sl.lease_id
            WHERE at.thread_id = ?
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()
        return row[0] if row else None


class SandboxManager:
    def __init__(
        self,
        provider: SandboxProvider,
        db_path: Path | None = None,
        default_context_id: str | None = None,
        on_session_ready: Callable[[str, str], None] | None = None,
    ):
        self.provider = provider
        self.provider_capability = provider.get_capability()
        self.default_context_id = default_context_id
        self._on_session_ready = on_session_ready

        self.db_path = db_path or DEFAULT_DB_PATH
        self.terminal_store = TerminalStore(db_path=self.db_path)
        self.lease_store = LeaseStore(db_path=self.db_path)
        self.session_manager = ChatSessionManager(
            provider=provider,
            db_path=self.db_path,
            default_policy=ChatSessionPolicy(),
        )

    def _build_context_id(self, thread_id: str) -> str | None:
        if self.provider.name in ("agentbay", "docker"):
            return f"leon-{thread_id}"
        return None

    def _default_terminal_cwd(self) -> str:
        for attr in ("default_cwd", "default_context_path", "mount_path"):
            if hasattr(self.provider, attr):
                value = getattr(self.provider, attr)
                if isinstance(value, str) and value:
                    return value
        return "/home/user"

    def _fire_session_ready(self, session_id: str, reason: str) -> None:
        if self._on_session_ready:
            self._on_session_ready(session_id, reason)

    def _ensure_bound_instance(self, lease) -> None:
        if self.provider_capability.eager_instance_binding and not lease.get_instance():
            lease.ensure_active_instance(self.provider)

    def close(self):
        return None

    def get_sandbox(self, thread_id: str) -> SandboxCapability:
        session = self.session_manager.get(thread_id)
        if session:
            # @@@activity-resume - Any new activity against a paused thread must resume before command execution.
            if session.status == "paused":
                if not self.resume_session(thread_id):
                    raise RuntimeError(f"Failed to resume paused session for thread {thread_id}")
                session = self.session_manager.get(thread_id)
                if not session:
                    raise RuntimeError(f"Session disappeared after resume for thread {thread_id}")
            self._ensure_bound_instance(session.lease)
            return SandboxCapability(session)

        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            terminal_id = f"term-{uuid.uuid4().hex[:12]}"
            lease_id = f"lease-{uuid.uuid4().hex[:12]}"
            lease = self.lease_store.create(lease_id, self.provider.name)
            initial_cwd = self._default_terminal_cwd()
            terminal = self.terminal_store.create(
                terminal_id=terminal_id,
                thread_id=thread_id,
                lease_id=lease_id,
                initial_cwd=initial_cwd,
            )
        else:
            lease = self.lease_store.get(terminal.lease_id)
            if not lease:
                lease = self.lease_store.create(terminal.lease_id, self.provider.name)

        self._ensure_bound_instance(lease)

        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        session = self.session_manager.create(
            session_id=session_id,
            thread_id=thread_id,
            terminal=terminal,
            lease=lease,
        )

        instance = lease.get_instance()
        if instance:
            self._fire_session_ready(instance.instance_id, "create")

        return SandboxCapability(session)

    def enforce_idle_timeouts(self) -> int:
        """Pause expired leases and close chat sessions.

        Rule:
        - If a chat session is idle past idle_ttl_sec, or older than max_duration_sec:
          1) pause physical lease instance (remote providers)
          2) close chat session runtime + mark session closed
        """
        now = datetime.now()
        count = 0

        for row in self.session_manager.list_active():
            session_id = row.get("session_id")
            thread_id = row.get("thread_id")
            started_at_raw = row.get("started_at")
            last_active_raw = row.get("last_active_at")
            if not session_id or not thread_id or not started_at_raw or not last_active_raw:
                continue

            started_at = datetime.fromisoformat(str(started_at_raw))
            last_active_at = datetime.fromisoformat(str(last_active_raw))
            idle_ttl_sec = int(row.get("idle_ttl_sec") or 0)
            max_duration_sec = int(row.get("max_duration_sec") or 0)

            idle_elapsed = (now - last_active_at).total_seconds()
            total_elapsed = (now - started_at).total_seconds()
            if idle_elapsed <= idle_ttl_sec and total_elapsed <= max_duration_sec:
                continue

            terminal = self.terminal_store.get(thread_id)
            lease = self.lease_store.get(terminal.lease_id) if terminal else None
            if lease:
                status = lease.refresh_instance_status(self.provider)
                if status == "running" and not lease.pause_instance(self.provider):
                    raise RuntimeError(f"Failed to pause expired lease {lease.lease_id} for thread {thread_id}")

            self.session_manager.delete(session_id, reason="idle_timeout")
            count += 1

        return count

    def get_or_create_session(self, thread_id: str):
        from sandbox.provider import SessionInfo
        from sandbox.runtime import RemoteWrappedRuntime

        capability = self.get_sandbox(thread_id)
        instance = capability._session.lease.get_instance()

        if not instance and isinstance(capability._session.runtime, RemoteWrappedRuntime):
            instance = capability._session.lease.ensure_active_instance(capability._session.runtime.provider)

        return SessionInfo(
            session_id=instance.instance_id if instance else "local",
            provider=self.provider.name,
            status="running",
        )

    def pause_session(self, thread_id: str) -> bool:
        """Pause session for thread."""
        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return False

        lease = self.lease_store.get(terminal.lease_id)
        if not lease:
            return False

        if not lease.pause_instance(self.provider):
            return False

        session = self.session_manager.get(thread_id)
        if session and session.status != "paused":
            self.session_manager.pause(session.session_id)
        return True

    def _get_thread_lease(self, thread_id: str):
        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return None
        return self.lease_store.get(terminal.lease_id)

    def _ensure_chat_session(self, thread_id: str) -> None:
        if self.session_manager.get(thread_id):
            return
        self.get_sandbox(thread_id)

    def resume_session(self, thread_id: str) -> bool:
        lease = self._get_thread_lease(thread_id)
        if not lease:
            return False

        if not lease.resume_instance(self.provider):
            return False

        session = self.session_manager.get(thread_id)
        if session:
            self.session_manager.resume(session.session_id)
        else:
            self._ensure_chat_session(thread_id)
        return True

    def pause_all_sessions(self) -> int:
        sessions = self.session_manager.list_all()
        count = 0
        for session_data in sessions:
            if self.pause_session(session_data["thread_id"]):
                count += 1
        return count

    def destroy_session(self, thread_id: str, session_id: str | None = None) -> bool:
        session = self.session_manager.get(thread_id)
        if session:
            self.session_manager.delete(session.session_id)

        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return False

        lease = self.lease_store.get(terminal.lease_id)
        if not lease:
            return False

        lease.destroy_instance(self.provider)
        return True

    def list_sessions(self) -> list[dict]:
        sessions: list[dict] = []

        terminals = self.terminal_store.list_all()
        threads_by_lease: dict[str, list[str]] = {}
        for term in terminals:
            lease_id = term.get("lease_id")
            thread_id = term.get("thread_id")
            if lease_id and thread_id:
                threads_by_lease.setdefault(lease_id, []).append(thread_id)

        rows = self.session_manager.list_all()
        active_rows = [r for r in rows if r.get("status") in {"active", "idle", "paused"}]
        chat_by_thread: dict[str, dict] = {row["thread_id"]: row for row in active_rows if row.get("thread_id")}
        inspect_visible = self.provider_capability.inspect_visible

        seen_instance_ids: set[str] = set()

        for lease_row in self.lease_store.list_by_provider(self.provider.name):
            lease_id = lease_row["lease_id"]
            lease = self.lease_store.get(lease_id)
            if not lease:
                continue

            instance = lease.get_instance()
            if not instance:
                continue

            status = lease.refresh_instance_status(self.provider)
            refreshed_instance = lease.get_instance()
            if not refreshed_instance or status in {"detached", "deleted", "stopped", "dead"}:
                continue

            seen_instance_ids.add(refreshed_instance.instance_id)
            threads = sorted(set(threads_by_lease.get(lease_id) or []))

            if not threads:
                sessions.append(
                    {
                        "session_id": refreshed_instance.instance_id,
                        "thread_id": "(untracked)",
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": lease_row.get("created_at"),
                        "last_active": lease_row.get("updated_at"),
                        "lease_id": lease_id,
                        "instance_id": refreshed_instance.instance_id,
                        "chat_session_id": None,
                        "source": "lease",
                        "inspect_visible": inspect_visible,
                    }
                )
                continue

            for thread_id in threads:
                chat = chat_by_thread.get(thread_id)
                sessions.append(
                    {
                        "session_id": refreshed_instance.instance_id,
                        "thread_id": thread_id,
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": lease_row.get("created_at"),
                        "last_active": (chat or {}).get("last_active_at") or lease_row.get("updated_at"),
                        "lease_id": lease_id,
                        "instance_id": refreshed_instance.instance_id,
                        "chat_session_id": (chat or {}).get("session_id"),
                        "source": "lease",
                        "inspect_visible": inspect_visible,
                    }
                )

        if hasattr(self.provider, "list_provider_sessions"):
            try:
                provider_sessions = self.provider.list_provider_sessions() or []
            except Exception:
                provider_sessions = []

            for ps in provider_sessions:
                instance_id = getattr(ps, "session_id", None)
                status = getattr(ps, "status", None) or "unknown"
                if not instance_id or status in {"deleted", "dead", "stopped"} or instance_id in seen_instance_ids:
                    continue

                sessions.append(
                    {
                        "session_id": instance_id,
                        "thread_id": "(orphan)",
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": None,
                        "last_active": None,
                        "lease_id": None,
                        "instance_id": instance_id,
                        "chat_session_id": None,
                        "source": "provider_orphan",
                        "inspect_visible": inspect_visible,
                    }
                )

        return sessions
