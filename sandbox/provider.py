"""
Abstract sandbox provider interface.

All sandbox backends (AgentBay, E2B, Docker, etc.) implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionInfo:
    """Information about a sandbox session."""

    session_id: str
    provider: str
    status: str  # 'running', 'paused', 'deleted', 'unknown'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderExecResult:
    """Result of command execution in a sandbox provider."""

    output: str
    exit_code: int = 0
    error: str | None = None


@dataclass
class Metrics:
    """Resource usage metrics."""

    cpu_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_used_gb: float
    disk_total_gb: float
    network_rx_kbps: float
    network_tx_kbps: float


class SandboxProvider(ABC):
    """
    Abstract interface for sandbox providers.

    Implementations:
    - AgentBayProvider: Alibaba Cloud sandbox
    - E2BProvider: E2B cloud sandbox
    - DockerProvider: Local Docker containers
    """

    name: str  # Provider identifier: 'agentbay', 'e2b', 'docker', 'local'

    # ==================== Session Lifecycle ====================

    @abstractmethod
    def create_session(self, context_id: str | None = None) -> SessionInfo:
        """Create a new sandbox session."""
        pass

    @abstractmethod
    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        """Destroy a session."""
        pass

    @abstractmethod
    def pause_session(self, session_id: str) -> bool:
        """Pause a session (reduce cost, keep state)."""
        pass

    @abstractmethod
    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        pass

    @abstractmethod
    def get_session_status(self, session_id: str) -> str:
        """Get session status: 'running', 'paused', 'deleted', 'unknown'."""
        pass

    # ==================== Execution ====================

    @abstractmethod
    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        """Execute shell command in sandbox."""
        pass

    # ==================== Filesystem ====================

    @abstractmethod
    def read_file(self, session_id: str, path: str) -> str:
        """Read file content from sandbox."""
        pass

    @abstractmethod
    def write_file(self, session_id: str, path: str, content: str) -> str:
        """Write file to sandbox."""
        pass

    @abstractmethod
    def list_dir(self, session_id: str, path: str) -> list[dict]:
        """List directory contents."""
        pass

    # ==================== Inspection ====================

    @abstractmethod
    def get_metrics(self, session_id: str) -> Metrics | None:
        """Get resource usage metrics."""
        pass

    def screenshot(self, session_id: str) -> bytes | None:
        """Take screenshot of sandbox display (optional)."""
        return None

    def list_processes(self, session_id: str) -> list[dict]:
        """List running processes (optional)."""
        return []

    def get_web_url(self, session_id: str) -> str | None:
        """Get web UI URL for the sandbox session (optional)."""
        return None
