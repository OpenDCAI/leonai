"""Abstract sandbox provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

RESOURCE_CAPABILITY_KEYS = (
    "filesystem",
    "terminal",
    "metrics",
    "screenshot",
    "web",
    "process",
    "hooks",
    "snapshot",
)


def normalize_resource_capabilities(raw: Mapping[str, object]) -> dict[str, bool]:
    missing = [key for key in RESOURCE_CAPABILITY_KEYS if key not in raw]
    extras = [key for key in raw if key not in RESOURCE_CAPABILITY_KEYS]
    if missing or extras:
        raise RuntimeError(f"Invalid resource capabilities; missing={missing}, extras={extras}")
    # @@@capability-shape-contract - monitor/UI rely on fixed capability keys for stable rendering.
    return {key: bool(raw[key]) for key in RESOURCE_CAPABILITY_KEYS}


def build_resource_capabilities(
    *,
    filesystem: bool,
    terminal: bool,
    metrics: bool,
    screenshot: bool,
    web: bool,
    process: bool,
    hooks: bool,
    snapshot: bool,
) -> dict[str, bool]:
    return normalize_resource_capabilities(
        {
            "filesystem": filesystem,
            "terminal": terminal,
            "metrics": metrics,
            "screenshot": screenshot,
            "web": web,
            "process": process,
            "hooks": hooks,
            "snapshot": snapshot,
        }
    )


@dataclass(frozen=True)
class ProviderCapability:
    """Declared lifecycle capability of a provider implementation."""

    can_pause: bool
    can_resume: bool
    can_destroy: bool
    supports_webhook: bool = False
    supports_status_probe: bool = True
    eager_instance_binding: bool = False
    inspect_visible: bool = True
    runtime_kind: str = "remote"
    resource_capabilities: dict[str, bool] = field(default_factory=dict)

    def declared_resource_capabilities(self) -> dict[str, bool]:
        return normalize_resource_capabilities(self.resource_capabilities)


@dataclass
class SessionInfo:
    session_id: str
    provider: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderExecResult:
    output: str
    exit_code: int = 0
    error: str | None = None


@dataclass
class Metrics:
    cpu_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_used_gb: float
    disk_total_gb: float
    network_rx_kbps: float
    network_tx_kbps: float


class SandboxProvider(ABC):
    """Abstract interface for sandbox providers."""

    name: str  # Provider identifier: 'agentbay', 'e2b', 'docker', 'local'

    @abstractmethod
    def get_capability(self) -> ProviderCapability:
        """Return lifecycle capability contract for this provider."""
        pass

    @abstractmethod
    def create_session(self, context_id: str | None = None) -> SessionInfo:
        pass

    @abstractmethod
    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        pass

    @abstractmethod
    def pause_session(self, session_id: str) -> bool:
        pass

    @abstractmethod
    def resume_session(self, session_id: str) -> bool:
        pass

    @abstractmethod
    def get_session_status(self, session_id: str) -> str:
        pass

    @abstractmethod
    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        pass

    @abstractmethod
    def read_file(self, session_id: str, path: str) -> str:
        pass

    @abstractmethod
    def write_file(self, session_id: str, path: str, content: str) -> str:
        pass

    @abstractmethod
    def list_dir(self, session_id: str, path: str) -> list[dict]:
        pass

    @abstractmethod
    def get_metrics(self, session_id: str) -> Metrics | None:
        pass

    def get_metrics_via_commands(self, session_id: str) -> Metrics | None:
        """Fallback: get metrics by executing system commands in the sandbox.

        This provides a universal way to get metrics for any provider that
        supports execute(). Subclasses can override get_metrics() for more
        efficient provider-specific implementations.
        """
        try:
            # CPU usage (percentage)
            cpu_result = self.execute(
                session_id,
                "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'",
                timeout_ms=5000,
            )
            cpu_percent = float(cpu_result.stdout.strip()) if cpu_result.exit_code == 0 and cpu_result.stdout.strip() else None

            # Memory usage (MB)
            mem_result = self.execute(
                session_id,
                "free -m | awk 'NR==2{print $3,$2}'",
                timeout_ms=5000,
            )
            if mem_result.exit_code == 0 and mem_result.stdout.strip():
                parts = mem_result.stdout.strip().split()
                memory_used_mb = float(parts[0]) if len(parts) > 0 else None
                memory_total_mb = float(parts[1]) if len(parts) > 1 else None
            else:
                memory_used_mb = None
                memory_total_mb = None

            # Disk usage (GB)
            disk_result = self.execute(
                session_id,
                "df -BG / | awk 'NR==2{gsub(/G/,\"\"); print $3,$2}'",
                timeout_ms=5000,
            )
            if disk_result.exit_code == 0 and disk_result.stdout.strip():
                parts = disk_result.stdout.strip().split()
                disk_used_gb = float(parts[0]) if len(parts) > 0 else None
                disk_total_gb = float(parts[1]) if len(parts) > 1 else None
            else:
                disk_used_gb = None
                disk_total_gb = None

            # If we got at least one metric, return Metrics object
            if any([cpu_percent, memory_used_mb, disk_used_gb]):
                return Metrics(
                    cpu_percent=cpu_percent or 0.0,
                    memory_used_mb=memory_used_mb or 0.0,
                    memory_total_mb=memory_total_mb or 0.0,
                    disk_used_gb=disk_used_gb or 0.0,
                    disk_total_gb=disk_total_gb or 0.0,
                    network_rx_kbps=0.0,
                    network_tx_kbps=0.0,
                )
            return None
        except Exception:
            return None

    def screenshot(self, session_id: str) -> bytes | str | None:
        return None

    def list_processes(self, session_id: str) -> list[dict]:
        return []

    def get_web_url(self, session_id: str) -> str | None:
        return None
