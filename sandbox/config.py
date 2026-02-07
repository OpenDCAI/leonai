"""Sandbox configuration — independent of AgentProfile.

Priority: --sandbox <name> > LEON_SANDBOX env > "local" (default)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


class AgentBayConfig(BaseModel):
    api_key: str | None = None
    region_id: str = "ap-southeast-1"
    context_path: str = "/home/wuying"
    image_id: str | None = None


class DockerConfig(BaseModel):
    image: str = "python:3.12-slim"
    mount_path: str = "/workspace"


class E2BConfig(BaseModel):
    api_key: str | None = None
    template: str = "base"
    cwd: str = "/home/user"
    timeout: int = 300  # seconds


class SandboxConfig(BaseModel):
    """Execution environment configuration.

    Stored in ~/.leon/sandboxes/<name>.json.
    "local" is the implicit default and needs no config file.
    """

    provider: str = "local"  # "local" | "agentbay" | "docker" | "e2b"
    agentbay: AgentBayConfig = Field(default_factory=AgentBayConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    e2b: E2BConfig = Field(default_factory=E2BConfig)
    on_exit: str = "pause"  # "pause" | "destroy"

    @classmethod
    def load(cls, name: str) -> SandboxConfig:
        """Load config from ~/.leon/sandboxes/<name>.json.

        Returns default (local) config if file doesn't exist.
        """
        if name == "local":
            return cls()

        path = Path.home() / ".leon" / "sandboxes" / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Sandbox config not found: {path}")

        data = json.loads(path.read_text())
        return cls(**data)

    def save(self, name: str) -> Path:
        """Save config to ~/.leon/sandboxes/<name>.json.

        Only serializes the active provider's config, not all three.
        """
        path = Path.home() / ".leon" / "sandboxes" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"provider": self.provider, "on_exit": self.on_exit}
        # Only include the active provider's config
        if self.provider in ("agentbay", "docker", "e2b"):
            data[self.provider] = getattr(self, self.provider).model_dump()
        path.write_text(json.dumps(data, indent=2))
        return path


def resolve_sandbox_name(cli_arg: str | None) -> str:
    """Resolve sandbox name: CLI > env > 'local'."""
    if cli_arg:
        return cli_arg
    return os.getenv("LEON_SANDBOX", "local")
