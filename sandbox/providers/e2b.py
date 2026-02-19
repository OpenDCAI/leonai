"""
E2B sandbox provider.

Implements SandboxProvider using E2B's cloud sandbox SDK.

Key differences from AgentBay:
- No persistent storage (context_id ignored) -- pause is the only way to preserve state
- Pause/resume via beta API: beta_pause() / Sandbox.connect()
- Uses beta_create(auto_pause=True) so sandboxes pause on timeout instead of dying
"""

from __future__ import annotations

import os
from typing import Any

from sandbox.provider import (
    Metrics,
    ProviderCapability,
    ProviderExecResult,
    SandboxProvider,
    SessionInfo,
)


class E2BProvider(SandboxProvider):
    """E2B cloud sandbox provider."""

    name = "e2b"
    WORKSPACE_ROOT = "/home/user/workspace"

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            can_pause=True,
            can_resume=True,
            can_destroy=True,
            supports_webhook=False,
            runtime_kind="e2b_pty",
        )

    def __init__(
        self,
        api_key: str,
        template: str = "base",
        default_cwd: str = "/home/user",
        timeout: int = 300,
        provider_name: str | None = None,
    ):
        if provider_name:
            self.name = provider_name
        self.api_key = api_key
        # @@@ E2B SDK methods like beta_pause() read from env, not from instance
        os.environ["E2B_API_KEY"] = api_key
        self.template = template
        self.default_cwd = default_cwd
        self.timeout = timeout
        self._sandboxes: dict[str, Any] = {}

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        from e2b import Sandbox

        sandbox = Sandbox.beta_create(
            template=self.template,
            timeout=self.timeout,
            auto_pause=True,
            api_key=self.api_key,
        )
        self._sandboxes[sandbox.sandbox_id] = sandbox

        return SessionInfo(
            session_id=sandbox.sandbox_id,
            provider=self.name,
            status="running",
        )

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        from e2b import Sandbox

        try:
            sandbox = self._sandboxes.pop(session_id, None)
            if sandbox:
                sandbox.kill()
            else:
                Sandbox.kill(session_id, api_key=self.api_key)
            return True
        except Exception:
            return False

    def pause_session(self, session_id: str) -> bool:
        try:
            sandbox = self._get_sandbox(session_id)
            sandbox.beta_pause()
            self._sandboxes.pop(session_id, None)
            return True
        except Exception:
            return False

    def resume_session(self, session_id: str) -> bool:
        from e2b import Sandbox

        try:
            sandbox = Sandbox.connect(
                session_id,
                timeout=self.timeout,
                api_key=self.api_key,
            )
            self._sandboxes[session_id] = sandbox
            return True
        except Exception:
            return False

    def get_session_status(self, session_id: str) -> str:
        from e2b import Sandbox

        try:
            # @@@ Sandbox.list() returns a paginator, not a list
            paginator = Sandbox.list(api_key=self.api_key)
            items = paginator.next_items()
            for s in items:
                if s.sandbox_id == session_id:
                    return s.state.value
            return "deleted"
        except Exception:
            return "unknown"

    def get_all_session_statuses(self) -> dict[str, str]:
        """Batch status check — one API call for all sessions."""
        from e2b import Sandbox

        try:
            paginator = Sandbox.list(api_key=self.api_key)
            items = paginator.next_items()
            return {s.sandbox_id: s.state.value for s in items}
        except Exception:
            return {}

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        sandbox = self._get_sandbox(session_id)
        try:
            result = sandbox.commands.run(
                command,
                cwd=cwd or self.default_cwd,
                timeout=timeout_ms / 1000,
            )
            output = result.stdout or ""
            if result.stderr:
                output += f"\n{result.stderr}" if output else result.stderr

            return ProviderExecResult(
                output=output,
                exit_code=result.exit_code,
            )
        except Exception as e:
            return ProviderExecResult(output="", error=str(e))

    def read_file(self, session_id: str, path: str) -> str:
        sandbox = self._get_sandbox(session_id)
        return sandbox.files.read(path)

    def write_file(self, session_id: str, path: str, content: str) -> str:
        sandbox = self._get_sandbox(session_id)
        sandbox.files.write(path, content)
        return f"Written: {path}"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        sandbox = self._get_sandbox(session_id)
        try:
            entries = sandbox.files.list(path)
            return [
                {
                    "name": entry.name,
                    "type": "directory" if entry.type and entry.type.value == "dir" else "file",
                    "size": getattr(entry, "size", 0) or 0,
                }
                for entry in entries
            ]
        except Exception:
            return []

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    def snapshot_workspace(self, session_id: str) -> list[dict]:
        """Download all files from /home/user/workspace."""
        sandbox = self._get_sandbox(session_id)
        stack = [self.WORKSPACE_ROOT]
        files = []
        while stack:
            d = stack.pop()
            try:
                entries = sandbox.files.list(d)
            except Exception:
                continue
            for entry in entries:
                p = entry.path if hasattr(entry, "path") else f"{d}/{entry.name}"
                if entry.type and entry.type.value == "dir":
                    stack.append(p)
                    continue
                try:
                    data = sandbox.files.read(p, format="bytes")
                    rel = p.removeprefix(self.WORKSPACE_ROOT + "/")
                    files.append({"file_path": rel, "content": bytes(data)})
                except Exception:
                    continue
        return files

    def restore_workspace(self, session_id: str, files: list[dict]) -> None:
        """Upload files back into /home/user/workspace."""
        sandbox = self._get_sandbox(session_id)
        for f in files:
            abs_path = f"{self.WORKSPACE_ROOT}/{f['file_path']}"
            sandbox.files.write(abs_path, f["content"])

    def _get_sandbox(self, session_id: str):
        """Get sandbox object, reconnecting if not cached."""
        if session_id not in self._sandboxes:
            from e2b import Sandbox

            sandbox = Sandbox.connect(
                session_id,
                timeout=self.timeout,
                api_key=self.api_key,
            )
            self._sandboxes[session_id] = sandbox
        return self._sandboxes[session_id]

    def get_runtime_sandbox(self, session_id: str):
        """Expose native SDK sandbox for runtime-level persistent terminal handling."""
        return self._get_sandbox(session_id)
