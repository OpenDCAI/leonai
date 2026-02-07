"""DockerSandbox — local Docker container sandbox."""

from __future__ import annotations

from pathlib import Path

from sandbox.config import SandboxConfig
from sandbox.providers.docker import DockerProvider
from sandbox.remote import RemoteSandbox


class DockerSandbox(RemoteSandbox):
    """Local Docker container sandbox."""

    def __init__(
        self,
        config: SandboxConfig,
        db_path: Path | None = None,
    ) -> None:
        dc = config.docker
        provider = DockerProvider(
            image=dc.image,
            mount_path=dc.mount_path,
        )
        super().__init__(
            provider=provider,
            config=config,
            default_cwd=dc.mount_path,
            db_path=db_path,
        )
        print(f"[DockerSandbox] Initialized (image={dc.image})")

    @property
    def name(self) -> str:
        return "docker"

    @property
    def working_dir(self) -> str:
        return self._config.docker.mount_path

    @property
    def env_label(self) -> str:
        return "Local Docker sandbox (Ubuntu)"
