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
class ExecuteResult:
    """Result of command execution."""
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
    - E2BProvider: E2B cloud sandbox (future)
    - DockerProvider: Local Docker containers (future)
    - LocalProvider: Passthrough, no isolation (future)
    """

    name: str  # Provider identifier: 'agentbay', 'e2b', 'docker', 'local'

    # ==================== Session Lifecycle ====================

    @abstractmethod
    def create_session(self, context_id: str | None = None) -> SessionInfo:
        """
        Create a new sandbox session.

        Args:
            context_id: Optional persistent context to attach (for data persistence)

        Returns:
            SessionInfo with session_id and status
        """
        pass

    @abstractmethod
    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        """
        Destroy a session.

        Args:
            session_id: Session to destroy
            sync: If True, persist data before destruction

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def pause_session(self, session_id: str) -> bool:
        """
        Pause a session (reduce cost, keep state).

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def resume_session(self, session_id: str) -> bool:
        """
        Resume a paused session.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_session_status(self, session_id: str) -> str:
        """
        Get session status.

        Returns:
            One of: 'running', 'paused', 'deleted', 'unknown'
        """
        pass

    # ==================== Execution ====================

    @abstractmethod
    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ExecuteResult:
        """
        Execute shell command in sandbox.

        Args:
            session_id: Target session
            command: Shell command to execute
            timeout_ms: Timeout in milliseconds
            cwd: Working directory

        Returns:
            ExecuteResult with output and exit code
        """
        pass

    # ==================== Filesystem ====================

    @abstractmethod
    def read_file(self, session_id: str, path: str) -> str:
        """
        Read file content from sandbox.

        Args:
            session_id: Target session
            path: Absolute path in sandbox

        Returns:
            File content as string

        Raises:
            IOError: If file cannot be read
        """
        pass

    @abstractmethod
    def write_file(self, session_id: str, path: str, content: str) -> str:
        """
        Write file to sandbox.

        Args:
            session_id: Target session
            path: Absolute path in sandbox
            content: File content

        Returns:
            Success message

        Raises:
            IOError: If file cannot be written
        """
        pass

    @abstractmethod
    def list_dir(self, session_id: str, path: str) -> list[dict]:
        """
        List directory contents.

        Args:
            session_id: Target session
            path: Directory path

        Returns:
            List of dicts with keys: name, type ('file'|'directory'), size
        """
        pass

    # ==================== Inspection ====================

    @abstractmethod
    def get_metrics(self, session_id: str) -> Metrics | None:
        """
        Get resource usage metrics.

        Returns:
            Metrics object or None if unavailable
        """
        pass

    def screenshot(self, session_id: str) -> bytes | None:
        """
        Take screenshot of sandbox display.

        Optional - not all providers support this.

        Returns:
            PNG/JPEG bytes or None
        """
        return None

    def list_processes(self, session_id: str) -> list[dict]:
        """
        List running processes.

        Optional - not all providers support this.

        Returns:
            List of dicts with keys: pid, name, cmd
        """
        return []

    def get_web_url(self, session_id: str) -> str | None:
        """
        Get web UI URL for the sandbox session.

        Optional - not all providers support this.

        Returns:
            URL string or None if unavailable
        """
        return None
