"""
Daytona sandbox provider.

Implements SandboxProvider using Daytona's cloud sandbox SDK.

Key differences from E2B:
- Docker containers (not microVMs)
- Stop/start with disk persistence (not pause/resume with memory)
- FUSE volumes backed by S3 for cross-session persistence
- ~5x cheaper than E2B (~$0.067/hour vs ~$0.35/hour)
"""

from __future__ import annotations

import os
from typing import Any

from sandbox.provider import (
    Metrics,
    ProviderExecResult,
    SandboxProvider,
    SessionInfo,
)


class DaytonaProvider(SandboxProvider):
    """Daytona cloud sandbox provider."""

    name = "daytona"

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://app.daytona.io/api",
        target: str = "local",
        default_cwd: str = "/home/daytona",
    ):
        from daytona_sdk import Daytona

        self.api_key = api_key
        self.api_url = api_url
        self.target = target
        self.default_cwd = default_cwd

        os.environ["DAYTONA_API_KEY"] = api_key
        os.environ["DAYTONA_API_URL"] = api_url
        self.client = Daytona()
        self._sandboxes: dict[str, Any] = {}

    # ==================== Session Lifecycle ====================

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        from daytona_sdk import CreateSandboxFromSnapshotParams

        params = CreateSandboxFromSnapshotParams(auto_stop_interval=0)
        sb = self.client.create(params)
        self._sandboxes[sb.id] = sb

        return SessionInfo(
            session_id=sb.id,
            provider=self.name,
            status="running",
        )

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        sb = self._get_sandbox(session_id)
        sb.delete()
        self._sandboxes.pop(session_id, None)
        return True

    def pause_session(self, session_id: str) -> bool:
        sb = self._get_sandbox(session_id)
        sb.stop()
        return True

    def resume_session(self, session_id: str) -> bool:
        sb = self._get_sandbox(session_id)
        sb.start()
        return True

    def get_session_status(self, session_id: str) -> str:
        # @@@status-refresh - Always refetch sandbox before reading state to avoid stale cached status.
        try:
            sb = self.client.find_one(session_id)
            self._sandboxes[session_id] = sb
            state = sb.state.value  # "started", "stopped", etc.
            if state == "started":
                return "running"
            elif state == "stopped":
                return "paused"
            return "unknown"
        except Exception as e:
            if "not found" in str(e).lower():
                return "deleted"
            return "unknown"

    # ==================== Execution ====================

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        sb = self._get_sandbox(session_id)
        try:
            result = sb.process.exec(command, cwd=cwd or self.default_cwd, timeout=timeout_ms // 1000)
            return ProviderExecResult(
                output=result.result or "",
                exit_code=result.exit_code or 0,
            )
        except Exception as e:
            return ProviderExecResult(output="", error=str(e))

    # ==================== Filesystem ====================

    def read_file(self, session_id: str, path: str) -> str:
        sb = self._get_sandbox(session_id)
        # @@@ download_file returns bytes, not str
        content = sb.fs.download_file(path)
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return content or ""

    def write_file(self, session_id: str, path: str, content: str) -> str:
        sb = self._get_sandbox(session_id)
        sb.fs.upload_file(content.encode("utf-8"), path)
        return f"Written: {path}"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        sb = self._get_sandbox(session_id)
        try:
            entries = sb.fs.list_files(path)
            return [
                {
                    "name": e.name,
                    "type": "directory" if e.is_dir else "file",
                    "size": e.size or 0,
                }
                for e in (entries or [])
            ]
        except Exception:
            return []

    # ==================== Batch Status ====================

    def list_provider_sessions(self) -> list[SessionInfo]:
        """List all sandboxes from Daytona API (including orphans not in DB)."""
        try:
            result = self.client.list()
            sessions = []
            for sb in result.items:
                state = sb.state.value
                if state == "started":
                    status = "running"
                elif state == "stopped":
                    status = "paused"
                else:
                    status = "unknown"
                sessions.append(SessionInfo(session_id=sb.id, provider=self.name, status=status))
            return sessions
        except Exception:
            return []

    # ==================== Inspection ====================

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    # ==================== Internal ====================

    def _get_sandbox(self, session_id: str):
        if session_id not in self._sandboxes:
            self._sandboxes[session_id] = self.client.find_one(session_id)
        return self._sandboxes[session_id]
