"""E2BSandbox — cloud sandbox via E2B."""

from __future__ import annotations

import os
from pathlib import Path

from sandbox.config import SandboxConfig
from sandbox.providers.e2b import E2BProvider
from sandbox.remote import RemoteSandbox


class E2BSandbox(RemoteSandbox):
    """Cloud sandbox backed by E2B."""

    def __init__(
        self,
        config: SandboxConfig,
        db_path: Path | None = None,
    ) -> None:
        e2b = config.e2b
        api_key = e2b.api_key or os.getenv("E2B_API_KEY")
        if not api_key:
            raise ValueError("E2B sandbox requires E2B_API_KEY")

        provider = E2BProvider(
            api_key=api_key,
            template=e2b.template,
            default_cwd=e2b.cwd,
            timeout=e2b.timeout,
            provider_name=config.name,
        )
        super().__init__(
            provider=provider,
            config=config,
            default_cwd=e2b.cwd,
            db_path=db_path,
        )
        print(f"[E2BSandbox] Initialized (template={e2b.template})")

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def working_dir(self) -> str:
        return self._config.e2b.cwd

    @property
    def env_label(self) -> str:
        return "Remote Linux sandbox (E2B)"
