"""
Sandbox inspector TUI screen.

Modal screen for inspecting sandbox sessions: metrics, files, processes.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
)
from textual import work

from middleware.sandbox.manager import SandboxManager


class SandboxInspector(ModalScreen):
    """
    Modal screen for sandbox inspection.

    Features:
    - Metrics tab: CPU, memory, disk, network
    - Files tab: Browse sandbox filesystem
    - Processes tab: List running processes
    - Actions: Pause, Resume, Destroy
    """

    CSS = """
    SandboxInspector {
        align: center middle;
    }

    #inspector-container {
        width: 90%;
        height: 85%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }

    #session-header {
        height: 3;
        padding: 0 1;
        background: $primary-darken-2;
    }

    #metrics-panel {
        height: 100%;
        padding: 1;
    }

    #files-panel {
        height: 100%;
    }

    #processes-panel {
        height: 100%;
    }

    #actions-bar {
        height: 3;
        padding: 0 1;
        align: center middle;
    }

    #actions-bar Button {
        margin: 0 1;
    }

    .metric-row {
        height: 1;
        padding: 0 1;
    }

    .metric-label {
        width: 15;
    }

    .metric-value {
        width: 30;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "pause", "Pause"),
        Binding("d", "destroy", "Destroy"),
    ]

    def __init__(
        self,
        sandbox_manager: SandboxManager,
        thread_id: str,
        name: str | None = None,
    ):
        super().__init__(name=name)
        self.sandbox_manager = sandbox_manager
        self.thread_id = thread_id
        self.session_info = None

    def compose(self) -> ComposeResult:
        with Vertical(id="inspector-container"):
            yield Header()
            yield Static(f"Sandbox: {self.thread_id}", id="session-header")

            with TabbedContent():
                with TabPane("Metrics", id="tab-metrics"):
                    with Vertical(id="metrics-panel"):
                        yield Static("Loading...", id="metrics-content")

                with TabPane("Files", id="tab-files"):
                    with Vertical(id="files-panel"):
                        yield DataTable(id="files-table")

                with TabPane("Processes", id="tab-processes"):
                    with Vertical(id="processes-panel"):
                        yield DataTable(id="processes-table")

            with Horizontal(id="actions-bar"):
                yield Button("Refresh [R]", id="btn-refresh", variant="primary")
                yield Button("Pause [P]", id="btn-pause", variant="warning")
                yield Button("Destroy [D]", id="btn-destroy", variant="error")
                yield Button("Close [ESC]", id="btn-close")

            yield Footer()

    def on_mount(self) -> None:
        # Setup tables
        files_table = self.query_one("#files-table", DataTable)
        files_table.add_columns("Name", "Type", "Size")
        files_table.cursor_type = "row"

        processes_table = self.query_one("#processes-table", DataTable)
        processes_table.add_columns("PID", "Name", "Command")
        processes_table.cursor_type = "row"

        # Load initial data
        self.load_session_info()

    def action_close(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.load_session_info()

    def action_pause(self) -> None:
        self.do_pause()

    def action_destroy(self) -> None:
        self.do_destroy()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.load_session_info()
        elif event.button.id == "btn-pause":
            self.do_pause()
        elif event.button.id == "btn-destroy":
            self.do_destroy()
        elif event.button.id == "btn-close":
            self.dismiss(None)

    @work(exclusive=True, thread=True)
    def load_session_info(self) -> None:
        """Load session info and metrics."""
        self.call_from_thread(self._set_status, "Loading...")

        try:
            # Get session info
            self.session_info = self.sandbox_manager.get_session(self.thread_id)

            if not self.session_info:
                self.call_from_thread(self._set_status, "No sandbox session for this thread")
                return

            session_id = self.session_info.session_id
            provider = self.sandbox_manager.provider

            # Load metrics
            metrics = provider.get_metrics(session_id)
            if metrics:
                metrics_text = (
                    f"CPU:     {metrics.cpu_percent:.1f}%\n"
                    f"Memory:  {metrics.memory_used_mb:.0f} MB / {metrics.memory_total_mb:.0f} MB\n"
                    f"Disk:    {metrics.disk_used_gb:.1f} GB / {metrics.disk_total_gb:.1f} GB\n"
                    f"Network: RX {metrics.network_rx_kbps:.1f} KB/s | TX {metrics.network_tx_kbps:.1f} KB/s\n"
                    f"\nSession ID: {session_id}\n"
                    f"Status: {self.session_info.status}"
                )
            else:
                metrics_text = f"Session ID: {session_id}\nStatus: {self.session_info.status}\n\nMetrics unavailable"

            self.call_from_thread(self._update_metrics, metrics_text)

            # Load files
            try:
                files = provider.list_dir(session_id, "/workspace")
                self.call_from_thread(self._update_files, files)
            except Exception:
                self.call_from_thread(self._update_files, [])

            # Load processes
            try:
                processes = provider.list_processes(session_id)
                self.call_from_thread(self._update_processes, processes)
            except Exception:
                self.call_from_thread(self._update_processes, [])

            self.call_from_thread(self._set_status, "Loaded")

        except Exception as e:
            self.call_from_thread(self._set_status, f"Error: {e}")

    @work(exclusive=True, thread=True)
    def do_pause(self) -> None:
        """Pause the sandbox session."""
        self.call_from_thread(self._set_status, "Pausing...")
        try:
            if self.sandbox_manager.pause_session(self.thread_id):
                self.call_from_thread(self._set_status, "Session paused")
                self.load_session_info()
            else:
                self.call_from_thread(self._set_status, "Failed to pause")
        except Exception as e:
            self.call_from_thread(self._set_status, f"Error: {e}")

    @work(exclusive=True, thread=True)
    def do_destroy(self) -> None:
        """Destroy the sandbox session."""
        self.call_from_thread(self._set_status, "Destroying...")
        try:
            if self.sandbox_manager.destroy_session(self.thread_id):
                self.call_from_thread(self._set_status, "Session destroyed")
                self.call_from_thread(self.dismiss, None)
            else:
                self.call_from_thread(self._set_status, "Failed to destroy")
        except Exception as e:
            self.call_from_thread(self._set_status, f"Error: {e}")

    def _set_status(self, msg: str) -> None:
        header = self.query_one("#session-header", Static)
        header.update(f"Sandbox: {self.thread_id} | {msg}")

    def _update_metrics(self, text: str) -> None:
        content = self.query_one("#metrics-content", Static)
        content.update(text)

    def _update_files(self, files: list[dict]) -> None:
        table = self.query_one("#files-table", DataTable)
        table.clear()
        for f in files:
            table.add_row(
                f.get("name", "?"),
                f.get("type", "file"),
                str(f.get("size", 0)),
            )

    def _update_processes(self, processes: list[dict]) -> None:
        table = self.query_one("#processes-table", DataTable)
        table.clear()
        for p in processes:
            table.add_row(
                str(p.get("pid", "?")),
                p.get("name", "?"),
                p.get("cmd", "")[:50],
            )
