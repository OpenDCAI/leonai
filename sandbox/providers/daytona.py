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
    WORKSPACE_ROOT = "/workspace"

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://app.daytona.io/api",
        target: str = "local",
        default_cwd: str = "/workspace",
    ):
        import os
        from daytona_sdk import Daytona

        self.api_key = api_key
        self.api_url = api_url
        self.target = target
        self.default_cwd = default_cwd

        os.environ["DAYTONA_API_KEY"] = api_key
        os.environ["DAYTONA_API_URL"] = api_url
        self.client = Daytona()
        self._workspaces: dict[str, Any] = {}

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        from daytona_sdk import CreateSandboxFromSnapshotParams

        params = CreateSandboxFromSnapshotParams()
        sandbox = self.client.create(params)
        sandbox_id = sandbox.id
        self._workspaces[sandbox_id] = sandbox

        return SessionInfo(
            session_id=sandbox_id,
            provider=self.name,
            status="running",
        )

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        try:
            workspace = self._get_workspace(session_id)
            workspace.delete()
            self._workspaces.pop(session_id, None)
            return True
        except Exception:
            return False

    def pause_session(self, session_id: str) -> bool:
        try:
            workspace = self._get_workspace(session_id)
            workspace.stop()
            return True
        except Exception:
            return False

    def resume_session(self, session_id: str) -> bool:
        try:
            workspace = self._get_workspace(session_id)
            workspace.start()
            return True
        except Exception:
            return False

    def get_session_status(self, session_id: str) -> str:
        try:
            workspace = self._get_workspace(session_id)
            info = workspace.info()
            if info and hasattr(info, 'workspace_instance'):
                state = info.workspace_instance.state
                if state == 'WORKSPACE_INSTANCE_STATE_STARTED':
                    return "running"
                elif state == 'WORKSPACE_INSTANCE_STATE_STOPPED':
                    return "paused"
            return "unknown"
        except Exception as e:
            if "not found" in str(e).lower():
                return "deleted"
            return "unknown"

    def get_all_session_statuses(self) -> dict[str, str]:
        try:
            workspaces = self.client.list()
            result = {}
            for ws in workspaces:
                info = ws.info()
                if info and hasattr(info, 'workspace_instance'):
                    state = info.workspace_instance.state
                    if state == 'WORKSPACE_INSTANCE_STATE_STARTED':
                        result[ws.id] = "running"
                    elif state == 'WORKSPACE_INSTANCE_STATE_STOPPED':
                        result[ws.id] = "paused"
                    else:
                        result[ws.id] = "unknown"
            return result
        except Exception:
            return {}

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        workspace = self._get_workspace(session_id)
        try:
            result = workspace.process.exec(command, cwd=cwd or self.default_cwd)
            return ProviderExecResult(
                output=result.result or "",
                exit_code=result.exit_code or 0,
            )
        except Exception as e:
            return ProviderExecResult(output="", error=str(e))

    def read_file(self, session_id: str, path: str) -> str:
        workspace = self._get_workspace(session_id)
        try:
            content = workspace.fs.download_file(path)
            return content or ""
        except Exception as e:
            raise OSError(str(e))

    def write_file(self, session_id: str, path: str, content: str) -> str:
        workspace = self._get_workspace(session_id)
        try:
            workspace.fs.upload_file(content.encode(), path)
            return f"Written: {path}"
        except Exception as e:
            raise OSError(str(e))

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        workspace = self._get_workspace(session_id)
        try:
            entries = workspace.fs.list_files(path)
            items = []
            for entry in entries or []:
                items.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir else "file",
                        "size": entry.size or 0,
                    }
                )
            return items
        except Exception:
            return []

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    def _get_workspace(self, session_id: str):
        if session_id not in self._workspaces:
            workspace = self.client.find_one(session_id)
            self._workspaces[session_id] = workspace
        return self._workspaces[session_id]
