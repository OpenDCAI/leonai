"""DaytonaSandbox — cloud sandbox via Daytona."""

from __future__ import annotations

import os
from pathlib import Path

from sandbox.config import SandboxConfig
from sandbox.providers.daytona import DaytonaProvider
from sandbox.remote import RemoteSandbox


class DaytonaSandbox(RemoteSandbox):
    """Cloud sandbox backed by Daytona."""

    def __init__(
        self,
        config: SandboxConfig,
        db_path: Path | None = None,
    ) -> None:
        dt = config.daytona
        api_key = dt.api_key or os.getenv("DAYTONA_API_KEY")
        if not api_key:
            raise ValueError("Daytona sandbox requires DAYTONA_API_KEY")

        provider = DaytonaProvider(
            api_key=api_key,
            api_url=dt.api_url,
            target=dt.target,
            default_cwd=dt.cwd,
        )
        super().__init__(
            provider=provider,
            config=config,
            default_cwd=dt.cwd,
            db_path=db_path,
        )
        print(f"[DaytonaSandbox] Initialized (target={dt.target})")

    @property
    def name(self) -> str:
        return "daytona"

    @property
    def working_dir(self) -> str:
        return self._config.daytona.cwd

    @property
    def env_label(self) -> str:
        return "Remote Linux sandbox (Daytona)"
