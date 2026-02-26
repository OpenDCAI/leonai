"""
Daytona sandbox provider.

Uses Daytona's Python SDK for sandbox lifecycle, filesystem, and process execution.

Important: runtime semantics remain PTY-backed (`daytona_pty`) for both SaaS and self-hosted.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

from sandbox.provider import Metrics, ProviderCapability, ProviderExecResult, SandboxProvider, SessionInfo


class DaytonaProvider(SandboxProvider):
    """Daytona cloud sandbox provider."""

    name = "daytona"

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            can_pause=True,
            can_resume=True,
            can_destroy=True,
            supports_webhook=True,
            runtime_kind="daytona_pty",
        )

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://app.daytona.io/api",
        target: str = "local",
        default_cwd: str = "/home/daytona",
        bind_mounts: list[dict[str, Any]] | None = None,
        provider_name: str | None = None,
    ):
        from daytona_sdk import Daytona

        if provider_name:
            self.name = provider_name
        self.api_key = api_key
        self.api_url = api_url
        self.target = target
        self.default_cwd = default_cwd
        self.bind_mounts = bind_mounts or []

        os.environ["DAYTONA_API_KEY"] = api_key
        os.environ["DAYTONA_API_URL"] = api_url
        self.client = Daytona()
        self._sandboxes: dict[str, Any] = {}

    # ==================== Session Lifecycle ====================

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        from daytona_sdk import CreateSandboxFromSnapshotParams

        if self.bind_mounts:
            # @@@daytona-bindmount-http-create - SDK currently lacks bind_mounts field, so self-host bind mounts use direct API create.
            sandbox_id = self._create_via_http(bind_mounts=self.bind_mounts)
            self._wait_until_started(sandbox_id)
            sb = self.client.find_one(sandbox_id)
        else:
            params = CreateSandboxFromSnapshotParams(auto_stop_interval=0)
            sb = self.client.create(params)
        self._sandboxes[sb.id] = sb
        return SessionInfo(session_id=sb.id, provider=self.name, status="running")

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
        sb = self.client.find_one(session_id)
        self._sandboxes[session_id] = sb
        state = sb.state.value
        if state == "started":
            return "running"
        if state == "stopped":
            return "paused"
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
            return ProviderExecResult(output=result.result or "", exit_code=int(result.exit_code or 0))
        except Exception as e:
            return ProviderExecResult(output="", exit_code=1, error=str(e))

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
        entries = sb.fs.list_files(path)
        return [
            {"name": e.name, "type": "directory" if e.is_dir else "file", "size": e.size or 0} for e in (entries or [])
        ]

    # ==================== Batch Status ====================

    def list_provider_sessions(self) -> list[SessionInfo]:
        result = self.client.list()
        sessions: list[SessionInfo] = []
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

    # ==================== Inspection ====================

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    # ==================== Internal ====================

    def _get_sandbox(self, session_id: str):
        if session_id not in self._sandboxes:
            self._sandboxes[session_id] = self.client.find_one(session_id)
        return self._sandboxes[session_id]

    def get_runtime_sandbox(self, session_id: str):
        """Expose native SDK sandbox for runtime-level persistent terminal handling."""
        return self._get_sandbox(session_id)

    def _api_auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _create_via_http(self, bind_mounts: list[dict[str, Any]]) -> str:
        payload = {
            "name": f"leon-{uuid.uuid4().hex[:12]}",
            "autoStopInterval": 0,
            "bindMounts": [
                {
                    "hostPath": str(mount["host_path"]),
                    "mountPath": str(mount["mount_path"]),
                    "readOnly": bool(mount.get("read_only", False)),
                }
                for mount in bind_mounts
            ],
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.api_url.rstrip('/')}/sandbox", headers=self._api_auth_headers(), json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Daytona create sandbox failed ({response.status_code}): {response.text}")
        sandbox_id = response.json().get("id")
        if not sandbox_id:
            raise RuntimeError(f"Daytona create sandbox response missing id: {response.text}")
        return str(sandbox_id)

    def _wait_until_started(self, sandbox_id: str, timeout_seconds: int = 120) -> None:
        deadline = time.time() + timeout_seconds
        with httpx.Client(timeout=15.0) as client:
            while time.time() < deadline:
                response = client.get(f"{self.api_url.rstrip('/')}/sandbox/{sandbox_id}", headers=self._api_auth_headers())
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Daytona get sandbox failed while waiting for started ({response.status_code}): {response.text}"
                    )
                body = response.json()
                state = str(body.get("state") or "")
                if state == "started":
                    return
                if state in {"destroyed", "destroying", "error", "failed"}:
                    raise RuntimeError(f"Daytona sandbox entered bad state '{state}': {response.text}")
                time.sleep(2)
        raise RuntimeError(f"Timed out waiting for Daytona sandbox {sandbox_id} to reach started state")
