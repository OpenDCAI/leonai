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
import uuid
from typing import Any

import httpx
from urllib.parse import urlparse

from sandbox.provider import (
    Metrics,
    ProviderCapability,
    ProviderExecResult,
    SandboxProvider,
    SessionInfo,
)


class DaytonaProvider(SandboxProvider):
    """Daytona cloud sandbox provider."""

    name = "daytona"

    @staticmethod
    def _is_saas_api_url(api_url: str) -> bool:
        parsed = urlparse((api_url or "").strip())
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").rstrip("/")
        # Treat the official SaaS API as the default behavior.
        return host == "app.daytona.io" and path == "/api"

    def get_capability(self) -> ProviderCapability:
        runtime_kind = "daytona_pty" if self._is_saas_api_url(self.api_url) else "remote"
        return ProviderCapability(
            can_pause=True,
            can_resume=True,
            can_destroy=True,
            supports_webhook=True,
            # @@@daytona-runtime-kind - Self-hosted Daytona toolbox forwarding is more reliable via
            # command-per-call execution than the PTY integration. RemoteWrappedRuntime uses provider.execute().
            runtime_kind=runtime_kind,
        )

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

    def _api_base(self) -> str:
        return self.api_url.rstrip("/")

    @staticmethod
    def _flatten_shell_script(command: str) -> str:
        # Toolbox "session exec" behaves best with a single command line.
        # Preserve semantics for our usage by converting newlines to statement separators.
        parts = [line.strip() for line in command.replace("\r", "").split("\n") if line.strip()]
        return "; ".join(parts)

    @staticmethod
    def _sh_single_quote(text: str) -> str:
        # Safe single-quote for POSIX shells: abc'def -> 'abc'"'"'def'
        return "'" + text.replace("'", "'\"'\"'") + "'"

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
        if self._is_saas_api_url(self.api_url):
            sb = self._get_sandbox(session_id)
            try:
                result = sb.process.exec(command, cwd=cwd or self.default_cwd, timeout=timeout_ms // 1000)
                # daytona-sdk historically used both exitCode and exit_code variants across versions.
                exit_code = getattr(result, "exit_code", None)
                if exit_code is None:
                    exit_code = getattr(result, "exitCode", 0)
                output = getattr(result, "result", "") or ""
                return ProviderExecResult(output=output, exit_code=int(exit_code or 0))
            except Exception as e:
                return ProviderExecResult(output="", exit_code=1, error=str(e))

        # Use toolbox session exec directly against the API.
        #
        # Why: daytona-sdk's process.exec path relies on a "toolbox proxy URL" indirection that can be
        # misconfigured in self-hosted setups (runner.proxyUrl), returning HTML/502 instead of JSON.
        # The API-hosted toolbox endpoints forward to the runner internally and accept a standard Bearer API key.
        sess = f"leon-exec-{uuid.uuid4().hex[:12]}"
        base = self._api_base()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        timeout_sec = max(1.0, float(timeout_ms) / 1000.0)

        try:
            with httpx.Client(timeout=timeout_sec) as client:
                # Create session
                create_url = f"{base}/toolbox/{session_id}/toolbox/process/session"
                r = client.post(create_url, headers=headers, json={"sessionId": sess})
                r.raise_for_status()

                # Exec command in session (runs via shell, supports multiline scripts, cd/export, &&, etc.)
                exec_url = f"{base}/toolbox/{session_id}/toolbox/process/session/{sess}/exec"
                flat = self._flatten_shell_script(command)
                # Run in a subshell so `exit` doesn't tear down the underlying session plumbing.
                wrapped = f"sh -c {self._sh_single_quote(flat)}"
                r = client.post(exec_url, headers=headers, json={"command": wrapped})
                r.raise_for_status()
                data = r.json()
                output = str(data.get("output") or "")
                exit_code = int(data.get("exitCode") or 0)

                # Best-effort cleanup: don't mask execution result if delete fails.
                delete_url = f"{base}/toolbox/{session_id}/toolbox/process/session/{sess}"
                try:
                    client.delete(delete_url, headers=headers).raise_for_status()
                except Exception:
                    pass

                return ProviderExecResult(output=output, exit_code=exit_code)
        except httpx.HTTPStatusError as e:
            body = e.response.text or ""
            snippet = body[:5000]
            return ProviderExecResult(output="", exit_code=1, error=f"HTTP {e.response.status_code}: {snippet}")
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

    def get_runtime_sandbox(self, session_id: str):
        """Expose native SDK sandbox for runtime-level persistent terminal handling."""
        return self._get_sandbox(session_id)
