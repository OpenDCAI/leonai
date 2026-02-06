"""
Docker sandbox provider.

Implements SandboxProvider using local Docker containers.
"""

from __future__ import annotations

import shlex
import subprocess
import uuid

from middleware.sandbox.provider import ExecuteResult, Metrics, SandboxProvider, SessionInfo


class DockerProvider(SandboxProvider):
    """
    Local Docker sandbox provider.

    Notes:
    - Requires Docker CLI available on host.
    - Uses one container per session.
    - If context_id is provided, uses a named Docker volume for persistence.
    """

    name = "docker"

    def __init__(self, image: str, mount_path: str = "/workspace"):
        self.image = image
        self.mount_path = mount_path
        self._sessions: dict[str, str] = {}  # session_id -> container_id

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        session_id = f"leon-{uuid.uuid4().hex[:12]}"
        container_name = session_id

        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--label",
            f"leon.session_id={session_id}",
        ]

        if context_id:
            volume = f"leon-context-{context_id}"
            cmd.extend(["-v", f"{volume}:{self.mount_path}"])

        cmd.extend(["-w", self.mount_path, self.image, "sleep", "infinity"])

        result = self._run(cmd)
        container_id = result.stdout.strip()
        if not container_id:
            raise RuntimeError("Failed to create docker container session")

        self._sessions[session_id] = container_id
        return SessionInfo(session_id=session_id, provider=self.name, status="running")

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        container_id = self._get_container_id(session_id)
        result = self._run(["docker", "rm", "-f", container_id], check=False)
        if result.returncode == 0:
            self._sessions.pop(session_id, None)
            return True
        return False

    def pause_session(self, session_id: str) -> bool:
        container_id = self._get_container_id(session_id)
        result = self._run(["docker", "pause", container_id], check=False)
        return result.returncode == 0

    def resume_session(self, session_id: str) -> bool:
        container_id = self._get_container_id(session_id)
        result = self._run(["docker", "unpause", container_id], check=False)
        return result.returncode == 0

    def get_session_status(self, session_id: str) -> str:
        container_id = self._get_container_id(session_id, allow_missing=True)
        if not container_id:
            return "deleted"
        result = self._run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_id],
            check=False,
        )
        status = result.stdout.strip().lower()
        if status in {"running", "paused", "exited", "dead"}:
            return "paused" if status == "paused" else "running" if status == "running" else "deleted"
        return "unknown"

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ExecuteResult:
        container_id = self._get_container_id(session_id)
        workdir = cwd or self.mount_path
        shell_cmd = f"cd {shlex.quote(workdir)} && {command}"
        result = self._run(
            ["docker", "exec", container_id, "/bin/sh", "-lc", shell_cmd],
            timeout=timeout_ms / 1000,
            check=False,
        )
        return ExecuteResult(
            output=result.stdout,
            exit_code=result.returncode,
            error=result.stderr or None,
        )

    def read_file(self, session_id: str, path: str) -> str:
        container_id = self._get_container_id(session_id)
        result = self._run(
            ["docker", "exec", container_id, "cat", path],
            check=False,
        )
        if result.returncode != 0:
            raise IOError(result.stderr.strip() or "Failed to read file")
        return result.stdout

    def write_file(self, session_id: str, path: str, content: str) -> str:
        container_id = self._get_container_id(session_id)
        cmd = ["docker", "exec", "-i", container_id, "/bin/sh", "-lc", f"cat > {shlex.quote(path)}"]
        result = self._run(cmd, input_text=content, check=False)
        if result.returncode != 0:
            raise IOError(result.stderr.strip() or "Failed to write file")
        return f"Written: {path}"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        container_id = self._get_container_id(session_id)
        script = (
            f"cd {shlex.quote(path)} 2>/dev/null || exit 1; "
            "for f in $(ls -A 2>/dev/null); do "
            "if [ -d \"$f\" ]; then t=directory; else t=file; fi; "
            "s=$(stat -c %s \"$f\" 2>/dev/null || wc -c <\"$f\" 2>/dev/null || echo 0); "
            "printf \"%s\\t%s\\t%s\\n\" \"$t\" \"$s\" \"$f\"; "
            "done"
        )
        result = self._run(
            ["docker", "exec", container_id, "/bin/sh", "-lc", script],
            check=False,
        )
        if result.returncode != 0:
            return []
        items: list[dict] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            item_type, size_str, name = parts
            try:
                size = int(size_str)
            except ValueError:
                size = 0
            items.append({"name": name, "type": item_type, "size": size})
        return items

    def upload(self, session_id: str, local_path: str, remote_path: str) -> str:
        container_id = self._get_container_id(session_id)
        result = self._run(["docker", "cp", local_path, f"{container_id}:{remote_path}"], check=False)
        if result.returncode != 0:
            raise IOError(result.stderr.strip() or "Failed to upload file")
        return f"Uploaded: {local_path} -> {remote_path}"

    def download(self, session_id: str, remote_path: str, local_path: str) -> str:
        container_id = self._get_container_id(session_id)
        result = self._run(["docker", "cp", f"{container_id}:{remote_path}", local_path], check=False)
        if result.returncode != 0:
            raise IOError(result.stderr.strip() or "Failed to download file")
        return f"Downloaded: {remote_path} -> {local_path}"

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    def _get_container_id(self, session_id: str, allow_missing: bool = False) -> str | None:
        container_id = self._sessions.get(session_id)
        if container_id:
            return container_id
        result = self._run(
            ["docker", "ps", "-aq", "--filter", f"label=leon.session_id={session_id}"],
            check=False,
        )
        container_id = result.stdout.strip()
        if container_id:
            self._sessions[session_id] = container_id
            return container_id
        if allow_missing:
            return None
        raise RuntimeError(f"Docker session not found: {session_id}")

    def _run(
        self,
        cmd: list[str],
        *,
        timeout: float | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        if check and result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Docker command failed")
        return result
