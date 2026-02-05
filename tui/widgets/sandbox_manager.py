"""
Sandbox Session Manager TUI.

Lists all AgentBay sessions with actions: create, delete, pause, resume, metrics.
Launch with: leonai sandbox
"""

import os
import sys

# Suppress AgentBay SDK logs (imports must come after stderr redirect)
_original_stderr = sys.stderr
sys.stderr = open(os.devnull, "w")

import agentbay._common.logger as sdk_logger  # noqa: E402
from agentbay import AgentBay  # noqa: E402


class _NoOpLogger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: self

    def opt(self, *args, **kwargs):
        return self


sdk_logger.log = _NoOpLogger()

# Restore stderr for Textual
sys.stderr = _original_stderr

from textual import work  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.widgets import Button, DataTable, Footer, Header, Static  # noqa: E402


class SandboxManagerApp(App):
    """TUI for managing AgentBay sandbox sessions."""

    CSS = """
    #main { height: 1fr; }
    #sidebar { width: 20; border: solid green; }
    #content { border: solid blue; padding: 1; }
    #detail { height: 10; border: solid magenta; padding: 1; }
    #status { height: 3; border: solid yellow; padding: 0 1; }
    Button { margin: 0; width: 100%; }
    Button.muted { opacity: 0.5; }
    DataTable { height: 100%; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete_session", "Delete"),
        Binding("n", "new_session", "New"),
        Binding("p", "pause_session", "Pause"),
        Binding("u", "resume_session", "Resume"),
        Binding("m", "show_metrics", "Metrics"),
        Binding("o", "open_url", "Open URL"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, api_key: str):
        super().__init__()
        self.agent_bay = AgentBay(api_key=api_key)
        self.sessions: list[dict] = []
        self._pause_resume_support_by_session: dict[str, bool] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with VerticalScroll(id="sidebar"):
                yield Button("Refresh", id="btn-refresh", variant="primary")
                yield Button("New", id="btn-new", variant="success")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Pause", id="btn-pause", variant="warning")
                yield Button("Resume", id="btn-resume", variant="success")
                yield Button("Metrics", id="btn-metrics", variant="primary")
                yield Button("Open URL", id="btn-url", variant="primary")
            with Vertical(id="content"):
                yield DataTable(id="table")
        yield Static("Select a session to view details", id="detail")
        yield Static("Ready - Press R to refresh", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("Session ID", "Status", "Thread")
        table.cursor_type = "row"
        self.do_refresh()

    def set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def action_refresh(self) -> None:
        self.do_refresh()

    @work(exclusive=True, thread=True)
    def do_refresh(self) -> None:
        self.call_from_thread(self.set_status, "Loading sessions...")
        sessions = []

        for status in ["RUNNING", "PAUSED", "PAUSING", "RESUMING"]:
            try:
                result = self.agent_bay.list(status=status, limit=50)
                for item in result.session_ids:
                    sessions.append({
                        "id": item["sessionId"],
                        "status": item["sessionStatus"],
                        "thread": "",  # Could map from leon.db if needed
                    })
            except Exception as e:
                self.call_from_thread(self.set_status, f"Error: {e}")
                return

        self.call_from_thread(self._update_table, sessions)

    def _update_table(self, sessions: list[dict]) -> None:
        self.sessions = sessions
        table = self.query_one("#table", DataTable)
        table.clear()
        active_ids = set()
        for s in sessions:
            active_ids.add(s["id"])
            table.add_row(s["id"], s["status"], s["thread"])
        if self._pause_resume_support_by_session:
            self._pause_resume_support_by_session = {
                sid: supported
                for sid, supported in self._pause_resume_support_by_session.items()
                if sid in active_ids
            }
        self.set_status(f"Found {len(sessions)} session(s)")
        sid = self._get_selected_session(notify=False)
        if sid:
            self._apply_pause_resume_state(sid)

    def _get_selected_session(self, notify: bool = True) -> str | None:
        table = self.query_one("#table", DataTable)
        if not self.sessions or table.cursor_row is None:
            if notify:
                self.set_status("No session selected")
            return None
        idx = table.cursor_row
        if idx >= len(self.sessions):
            return None
        return self.sessions[idx]["id"]

    def action_delete_session(self) -> None:
        sid = self._get_selected_session()
        if sid:
            self.do_delete(sid)

    @work(exclusive=True, thread=True)
    def do_delete(self, sid: str) -> None:
        self.call_from_thread(self.set_status, f"Deleting {sid[:16]}...")
        try:
            result = self.agent_bay.get(sid)
            if result.success:
                result.session.delete()
                self.call_from_thread(self.set_status, f"Deleted {sid[:16]}")
                self.do_refresh()
            else:
                self.call_from_thread(self.set_status, "Session not found")
        except Exception as e:
            self.call_from_thread(self.set_status, f"Delete failed: {e}")

    def action_new_session(self) -> None:
        self.do_create()

    @work(exclusive=True, thread=True)
    def do_create(self) -> None:
        self.call_from_thread(self.set_status, "Creating new session...")
        try:
            result = self.agent_bay.create()
            sid = result.session.session_id
            self.call_from_thread(self.set_status, f"Created: {sid[:16]}")
            self.do_refresh()
        except Exception as e:
            self.call_from_thread(self.set_status, f"Create failed: {e}")

    @work(exclusive=True, thread=True)
    def do_pause(self, sid: str) -> None:
        self.call_from_thread(self.set_status, f"Pausing {sid[:16]}...")
        try:
            result = self.agent_bay.get(sid)
            if result.success:
                pause_result = self.agent_bay.beta_pause(result.session)
                if pause_result.success:
                    self._pause_resume_support_by_session[sid] = True
                    self.call_from_thread(self.set_status, f"Paused {sid[:16]}")
                elif self._is_pause_resume_not_supported(pause_result):
                    self._pause_resume_support_by_session[sid] = False
                    self.call_from_thread(self._apply_pause_resume_state, sid)
                    self.call_from_thread(self.set_status, "Pause/resume not available (account tier)")
                else:
                    self.call_from_thread(self.set_status, f"Pause failed: {pause_result.error_message}")
                self.do_refresh()
            else:
                self.call_from_thread(self.set_status, "Session not found")
        except Exception as e:
            if self._is_pause_resume_not_supported(e):
                self._pause_resume_support_by_session[sid] = False
                self.call_from_thread(self._apply_pause_resume_state, sid)
                self.call_from_thread(self.set_status, "Pause/resume not available (account tier)")
            else:
                self.call_from_thread(self.set_status, f"Pause failed: {e}")

    @work(exclusive=True, thread=True)
    def do_resume(self, sid: str) -> None:
        self.call_from_thread(self.set_status, f"Resuming {sid[:16]}...")
        try:
            result = self.agent_bay.get(sid)
            if result.success:
                resume_result = self.agent_bay.beta_resume(result.session)
                if resume_result.success:
                    self._pause_resume_support_by_session[sid] = True
                    self.call_from_thread(self.set_status, f"Resumed {sid[:16]}")
                elif self._is_pause_resume_not_supported(resume_result):
                    self._pause_resume_support_by_session[sid] = False
                    self.call_from_thread(self._apply_pause_resume_state, sid)
                    self.call_from_thread(self.set_status, "Pause/resume not available (account tier)")
                else:
                    self.call_from_thread(self.set_status, f"Resume failed: {resume_result.error_message}")
                self.do_refresh()
            else:
                self.call_from_thread(self.set_status, "Session not found")
        except Exception as e:
            if self._is_pause_resume_not_supported(e):
                self._pause_resume_support_by_session[sid] = False
                self.call_from_thread(self._apply_pause_resume_state, sid)
                self.call_from_thread(self.set_status, "Pause/resume not available (account tier)")
            else:
                self.call_from_thread(self.set_status, f"Resume failed: {e}")

    def action_show_metrics(self) -> None:
        sid = self._get_selected_session()
        if sid:
            self.do_get_metrics(sid)

    @work(exclusive=True, thread=True)
    def do_get_metrics(self, sid: str) -> None:
        self.call_from_thread(self.set_status, f"Getting metrics for {sid[:16]}...")
        try:
            result = self.agent_bay.get(sid)
            if not result.success:
                self.call_from_thread(self._update_detail, "Session not found")
                return

            session = result.session
            metrics = session.get_metrics()

            if metrics.success and metrics.metrics:
                m = metrics.metrics
                url = getattr(session, 'resource_url', '')
                detail = (
                    f"Session: {sid}\n"
                    f"CPU: {m.cpu_used_pct:.1f}% ({m.cpu_count} cores)\n"
                    f"Memory: {m.mem_used / 1024 / 1024:.0f}MB / {m.mem_total / 1024 / 1024:.0f}MB\n"
                    f"Disk: {m.disk_used / 1024 / 1024 / 1024:.1f}GB / {m.disk_total / 1024 / 1024 / 1024:.1f}GB\n"
                    f"Network: RX {m.rx_rate_kbyte_per_s:.1f} KB/s | TX {m.tx_rate_kbyte_per_s:.1f} KB/s\n"
                    f"\nWeb URL: {url[:60]}..." if url else ""
                )
                self.call_from_thread(self._update_detail, detail)
                self.call_from_thread(self.set_status, "Metrics loaded")
            else:
                self.call_from_thread(self._update_detail, f"Failed: {metrics.error_message}")
                self.call_from_thread(self.set_status, "Failed to get metrics")
        except Exception as e:
            self.call_from_thread(self._update_detail, f"Error: {e}")
            self.call_from_thread(self.set_status, f"Error: {e}")

    def action_open_url(self) -> None:
        sid = self._get_selected_session()
        if sid:
            self.do_open_url(sid)

    @work(exclusive=True, thread=True)
    def do_open_url(self, sid: str) -> None:
        self.call_from_thread(self.set_status, f"Getting URL for {sid[:16]}...")
        try:
            result = self.agent_bay.get(sid)
            if result.success:
                url = getattr(result.session, 'resource_url', None)
                if url:
                    import webbrowser
                    webbrowser.open(url)
                    self.call_from_thread(self.set_status, "Opened in browser")
                else:
                    self.call_from_thread(self.set_status, "No URL available")
            else:
                self.call_from_thread(self.set_status, "Session not found")
        except Exception as e:
            self.call_from_thread(self.set_status, f"Error: {e}")

    def _update_detail(self, text: str) -> None:
        self.query_one("#detail", Static).update(text)

    def _is_pause_resume_not_supported(self, result_or_error: object) -> bool:
        code = getattr(result_or_error, "code", "") or getattr(result_or_error, "error_code", "")
        if code == "BenefitLevel.NotSupport":
            return True
        message = (
            getattr(result_or_error, "error_message", "")
            or getattr(result_or_error, "message", "")
            or str(result_or_error)
        )
        return "BenefitLevel.NotSupport" in message

    def _mute_pause_resume(self) -> None:
        """Visually mute pause/resume buttons when not supported."""
        pause_btn = self.query_one("#btn-pause", Button)
        resume_btn = self.query_one("#btn-resume", Button)
        pause_btn.add_class("muted")
        resume_btn.add_class("muted")
        pause_btn.label = "Pause (N/A)"
        resume_btn.label = "Resume (N/A)"

    def _unmute_pause_resume(self) -> None:
        pause_btn = self.query_one("#btn-pause", Button)
        resume_btn = self.query_one("#btn-resume", Button)
        pause_btn.remove_class("muted")
        resume_btn.remove_class("muted")
        pause_btn.label = "Pause"
        resume_btn.label = "Resume"

    def _apply_pause_resume_state(self, sid: str) -> None:
        if self._pause_resume_support_by_session.get(sid) is False:
            self._mute_pause_resume()
        else:
            self._unmute_pause_resume()

    def action_pause_session(self) -> None:
        sid = self._get_selected_session()
        if sid:
            if self._pause_resume_support_by_session.get(sid) is False:
                self.set_status("Pause not available (account tier)")
                return
            self.do_pause(sid)

    def action_resume_session(self) -> None:
        sid = self._get_selected_session()
        if sid:
            if self._pause_resume_support_by_session.get(sid) is False:
                self.set_status("Resume not available (account tier)")
                return
            self.do_resume(sid)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn-refresh": self.action_refresh,
            "btn-new": self.action_new_session,
            "btn-delete": self.action_delete_session,
            "btn-pause": self.action_pause_session,
            "btn-resume": self.action_resume_session,
            "btn-metrics": self.action_show_metrics,
            "btn-url": self.action_open_url,
        }
        action = actions.get(event.button.id)
        if action:
            action()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        sid = self._get_selected_session(notify=False)
        if sid:
            self._apply_pause_resume_state(sid)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        sid = self._get_selected_session(notify=False)
        if sid:
            self._apply_pause_resume_state(sid)
