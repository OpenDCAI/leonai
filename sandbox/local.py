"""LocalSandbox with ChatSession-managed persistent terminal runtime."""

from __future__ import annotations

import platform
import shlex
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.base import Sandbox
from sandbox.manager import SandboxManager
from sandbox.provider import (
    Metrics,
    ProviderCapability,
    ProviderExecResult,
    SandboxProvider,
    SessionInfo,
    build_resource_capabilities,
)
from sandbox.thread_context import get_current_thread_id, set_current_thread_id

if TYPE_CHECKING:
    from sandbox.capability import SandboxCapability
    from sandbox.interfaces.executor import BaseExecutor
    from sandbox.interfaces.filesystem import FileSystemBackend


@dataclass
class LocalSessionProvider(SandboxProvider):
    name: str = "local"
    CAPABILITY = ProviderCapability(
        can_pause=True,
        can_resume=True,
        can_destroy=True,
        supports_webhook=False,
        supports_status_probe=False,
        eager_instance_binding=True,
        inspect_visible=False,
        runtime_kind="local",
        resource_capabilities=build_resource_capabilities(
            filesystem=True,
            terminal=True,
            metrics=True,
            screenshot=False,
            web=False,
            process=False,
            hooks=False,
            snapshot=False,
        ),
    )
    default_cwd: str | None = None
    _session_states: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _state_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def get_capability(self) -> ProviderCapability:
        return self.CAPABILITY

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        session_id = context_id or f"local-{uuid.uuid4().hex[:12]}"
        with self._state_lock:
            self._session_states[session_id] = "running"
        return SessionInfo(session_id=session_id, provider="local", status="running")

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        with self._state_lock:
            state = self._session_states.get(session_id)
            if state == "detached":
                return True
            self._session_states[session_id] = "detached"
        return True

    def pause_session(self, session_id: str) -> bool:
        with self._state_lock:
            # @@@local-provider-process-boundary - LocalSessionProvider state is in-memory only; in multi-worker
            # web backends the pause/resume request can land on a different process than the one that created
            # the session. For lease-bound local sessions (context_id like "leon-<lease_id>" or "local-..."),
            # treat missing in-memory state as "running" so pause/resume stays idempotent across processes.
            state = self._session_states.get(session_id)
            if state is None:
                if session_id.startswith(("leon-", "local-")):
                    state = "running"
                else:
                    return False
            if state == "detached":
                return False
            if state != "paused":
                self._session_states[session_id] = "paused"
        return True

    def resume_session(self, session_id: str) -> bool:
        with self._state_lock:
            state = self._session_states.get(session_id)
            if state is None:
                if session_id.startswith(("leon-", "local-")):
                    state = "running"
                else:
                    return False
            if state == "detached":
                return False
            if state != "running":
                self._session_states[session_id] = "running"
        return True

    def get_session_status(self, session_id: str) -> str:
        with self._state_lock:
            state = self._session_states.get(session_id)
            if state is None and session_id.startswith(("leon-", "local-")):
                return "running"
            return state or "detached"

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        workdir = cwd or self.default_cwd or str(Path.cwd())
        shell_cmd = f"cd {shlex.quote(workdir)} && {command}"
        result = subprocess.run(
            ["/bin/bash", "-lc", shell_cmd],
            capture_output=True,
            text=True,
            timeout=max(timeout_ms / 1000, 0.1),
            check=False,
        )
        output = result.stdout or ""
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr
        return ProviderExecResult(output=output, exit_code=result.returncode)

    def read_file(self, session_id: str, path: str) -> str:
        return Path(path).read_text()

    def write_file(self, session_id: str, path: str, content: str) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Written: {path}"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        target = Path(path)
        if not target.exists() or not target.is_dir():
            return []
        items: list[dict] = []
        for child in target.iterdir():
            item_type = "directory" if child.is_dir() else "file"
            size = child.stat().st_size if child.exists() else 0
            items.append({"name": child.name, "type": item_type, "size": int(size)})
        return items

    def get_metrics(self, session_id: str) -> Metrics | None:
        if platform.system() != "Darwin":
            return self.get_metrics_via_commands(session_id)

        # @@@local-metrics-macos - use fast macOS-native commands; avoid 'top' which requires sampling delay.
        try:
            # CPU: sum per-process %cpu and normalize by core count
            r = self.execute(
                session_id,
                "sysctl -n hw.ncpu; ps -A -o %cpu | awk 'NR>1{s+=$1} END{printf \"%g\", s}'",
                timeout_ms=5000,
            )
            cpu_percent = None
            if r.exit_code == 0:
                lines = r.output.strip().splitlines()
                ncpu = int(lines[0]) if lines else 1
                if len(lines) > 1 and lines[1]:
                    cpu_percent = float(lines[1]) / max(ncpu, 1)

            # Memory: total from hw.memsize, used = (active + wired + compressor) * page_size
            r = self.execute(session_id, "pagesize; sysctl -n hw.memsize; vm_stat", timeout_ms=5000)
            memory_used_mb, memory_total_mb = None, None
            if r.exit_code == 0:
                lines = r.output.strip().splitlines()
                page_size = int(lines[0]) if lines else 4096
                memory_total_mb = int(lines[1]) / 1024 / 1024 if len(lines) > 1 else None
                active = wired = compressor = 0
                for line in lines[2:]:
                    if "Pages active:" in line:
                        active = int(line.split()[-1].rstrip("."))
                    elif "Pages wired down:" in line:
                        wired = int(line.split()[-1].rstrip("."))
                    elif "Pages occupied by compressor:" in line:
                        compressor = int(line.split()[-1].rstrip("."))
                if memory_total_mb is not None:
                    memory_used_mb = (active + wired + compressor) * page_size / 1024 / 1024

            # Disk: df -g for 1G-blocks on macOS. APFS volumes share one container, so
            # "Used" column shows only this volume's data; use total - available for real aggregate.
            r = self.execute(session_id, "df -g / | awk 'NR==2{print $2 - $4, $2}'", timeout_ms=5000)
            disk_used_gb, disk_total_gb = None, None
            if r.exit_code == 0 and r.output.strip():
                parts = r.output.strip().split()
                disk_used_gb = float(parts[0]) if parts else None
                disk_total_gb = float(parts[1]) if len(parts) > 1 else None

            return Metrics(
                cpu_percent=cpu_percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
            )
        except Exception:
            return None


class LocalSandbox(Sandbox):
    def __init__(self, workspace_root: str, db_path: Path | None = None) -> None:
        self._workspace_root = workspace_root
        target_db = db_path or (Path.home() / ".leon" / "sandbox.db")
        self._provider = LocalSessionProvider(default_cwd=workspace_root)
        self._manager = SandboxManager(provider=self._provider, db_path=target_db)
        self._capability_cache: dict[str, SandboxCapability] = {}

    @property
    def name(self) -> str:
        return "local"

    @property
    def working_dir(self) -> str:
        return self._workspace_root

    @property
    def env_label(self) -> str:
        return "Local host"

    @property
    def manager(self) -> SandboxManager:
        return self._manager

    def _get_capability(self) -> SandboxCapability:
        thread_id = get_current_thread_id()
        if not thread_id:
            raise RuntimeError("No thread_id set. Call set_current_thread_id first.")
        if thread_id not in self._capability_cache:
            self._capability_cache[thread_id] = self._manager.get_sandbox(thread_id)
        return self._capability_cache[thread_id]

    def ensure_session(self, thread_id: str) -> None:
        set_current_thread_id(thread_id)
        self._capability_cache.pop(thread_id, None)
        self._get_capability()

    def pause_thread(self, thread_id: str) -> bool:
        self._capability_cache.pop(thread_id, None)
        return self._manager.pause_session(thread_id)

    def resume_thread(self, thread_id: str) -> bool:
        self._capability_cache.pop(thread_id, None)
        return self._manager.resume_session(thread_id)

    def fs(self) -> FileSystemBackend | None:
        return None

    def shell(self) -> BaseExecutor:
        class LazyLocalExecutor:
            def __init__(self, sandbox: LocalSandbox):
                self._sandbox = sandbox
                self.is_remote = False
                self.runtime_owns_cwd = True
                self.shell_name = "local-session"

            def __getattr__(self, name: str):
                return getattr(self._sandbox._get_capability().command, name)

        return LazyLocalExecutor(self)  # type: ignore[return-value]

    def close(self) -> None:
        for session in self._manager.list_sessions():
            self._manager.destroy_session(session["thread_id"])
