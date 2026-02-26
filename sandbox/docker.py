"""DockerSandbox — local Docker container sandbox."""

from __future__ import annotations

from pathlib import Path

from sandbox.config import SandboxConfig
from sandbox.providers.docker import DockerProvider
from sandbox.remote import RemoteSandbox


class DockerSandbox(RemoteSandbox):
    def __init__(self, config: SandboxConfig, db_path: Path | None = None) -> None:
        dc = config.docker
        default_cwd = dc.cwd or dc.mount_path
        provider = DockerProvider(
            image=dc.image,
            mount_path=dc.mount_path,
            default_cwd=default_cwd,
            bind_mounts=[mount.model_dump() for mount in dc.bind_mounts],
            provider_name=config.name,
        )
        super().__init__(
            provider=provider,
            config=config,
            default_cwd=default_cwd,
            db_path=db_path,
        )
        print(f"[DockerSandbox] Initialized (image={dc.image})")

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def working_dir(self) -> str:
        return self._config.docker.cwd or self._config.docker.mount_path

    @property
    def env_label(self) -> str:
        return "Local Docker sandbox (Ubuntu)"
