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
        from daytona_sdk import Daytona

        self.api_key = api_key
        self.api_url = api_url
        self.target = target
        self.default_cwd = default_cwd
        self.client = Daytona(api_key=api_key, server_url=api_url)
        self._workspaces: dict[str, Any] = {}

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        from daytona_sdk.models import CreateWorkspaceDTO

        workspace_name = context_id or f"leon-{os.urandom(6).hex()}"

        create_dto = CreateWorkspaceDTO(
            name=workspace_name,
            target=self.target,
        )

        workspace = self.client.workspace.create_workspace(create_dto)
        workspace_id = workspace.id
        self._workspaces[workspace_id] = workspace

        self.client.workspace.start_workspace(workspace_id)

        return SessionInfo(
            session_id=workspace_id,
            provider=self.name,
            status="running",
        )

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        try:
            self.client.workspace.remove_workspace(session_id)
            self._workspaces.pop(session_id, None)
            return True
        except Exception:
            return False

    def pause_session(self, session_id: str) -> bool:
        try:
            self.client.workspace.stop_workspace(session_id)
            return True
        except Exception:
            return False

    def resume_session(self, session_id: str) -> bool:
        try:
            self.client.workspace.start_workspace(session_id)
            return True
        except Exception:
            return False

    def get_session_status(self, session_id: str) -> str:
        try:
            workspace = self.client.workspace.get_workspace(session_id)
            if workspace.info and workspace.info.projects:
                state = workspace.info.projects[0].state
                if state and hasattr(state, 'uptime'):
                    return "running" if state.uptime else "paused"
            return "unknown"
        except Exception as e:
            if "not found" in str(e).lower():
                return "deleted"
            return "unknown"

    def get_all_session_statuses(self) -> dict[str, str]:
        try:
            workspaces = self.client.workspace.list_workspaces()
            result = {}
            for ws in workspaces:
                if ws.info and ws.info.projects:
                    state = ws.info.projects[0].state
                    if state and hasattr(state, 'uptime'):
                        result[ws.id] = "running" if state.uptime else "paused"
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
        if not workspace.info or not workspace.info.projects:
            return ProviderExecResult(output="", error="Workspace not ready")

        project = workspace.info.projects[0]
        try:
            result = self.client.workspace.execute_command(
                workspace_id=session_id,
                project_name=project.name,
                command=command,
            )

            return ProviderExecResult(
                output=result or "",
                exit_code=0,
            )
        except Exception as e:
            return ProviderExecResult(output="", error=str(e))

    def read_file(self, session_id: str, path: str) -> str:
        workspace = self._get_workspace(session_id)
        if not workspace.info or not workspace.info.projects:
            raise OSError("Workspace not ready")

        project = workspace.info.projects[0]
        try:
            content = self.client.workspace.get_file_content(
                workspace_id=session_id,
                project_name=project.name,
                path=path,
            )
            return content or ""
        except Exception as e:
            raise OSError(str(e))

    def write_file(self, session_id: str, path: str, content: str) -> str:
        workspace = self._get_workspace(session_id)
        if not workspace.info or not workspace.info.projects:
            raise OSError("Workspace not ready")

        project = workspace.info.projects[0]
        try:
            self.client.workspace.set_file_content(
                workspace_id=session_id,
                project_name=project.name,
                path=path,
                content=content,
            )
            return f"Written: {path}"
        except Exception as e:
            raise OSError(str(e))

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        workspace = self._get_workspace(session_id)
        if not workspace.info or not workspace.info.projects:
            return []

        project = workspace.info.projects[0]
        try:
            entries = self.client.workspace.list_files(
                workspace_id=session_id,
                project_name=project.name,
                path=path,
            )
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
            workspace = self.client.workspace.get_workspace(session_id)
            self._workspaces[session_id] = workspace
        return self._workspaces[session_id]
