"""Status bar widget"""

from rich.text import Text
from textual.widgets import Static


class StatusBar(Static):
    """Status bar showing thread info and controls"""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, thread_id: str = "default", **kwargs) -> None:
        super().__init__(**kwargs)
        self._thread_id = thread_id
        self._message_count = 0
        self._runtime_status = ""

    def compose(self):
        text = self._build_status_text()
        yield Static(text)

    def _build_status_text(self) -> Text:
        """Build status bar text"""
        text = Text()
        text.append("Leon Agent", style="bold cyan")
        text.append(" | ", style="dim")
        text.append(f"Thread: {self._thread_id}", style="dim")
        text.append(" | ", style="dim")
        text.append(f"消息: {self._message_count}", style="dim")

        # 显示运行时状态
        if self._runtime_status:
            text.append(" | ", style="dim")
            text.append(self._runtime_status, style="yellow")

        text.append(" | ", style="dim")
        text.append("Ctrl+↑/↓: 历史", style="dim")
        text.append(" | ", style="dim")
        text.append("Ctrl+E: 导出", style="dim")
        text.append(" | ", style="dim")
        text.append("Ctrl+Y: 复制", style="dim")
        return text

    def update_thread(self, thread_id: str) -> None:
        """Update thread ID display"""
        self._thread_id = thread_id
        self._message_count = 0
        text = self._build_status_text()
        self.update(text)

    def update_stats(self, message_count: int) -> None:
        """Update message count"""
        self._message_count = message_count
        text = self._build_status_text()
        self.update(text)

    def update_runtime_status(self, status: str) -> None:
        """Update runtime status display"""
        self._runtime_status = status
        text = self._build_status_text()
        self.update(text)
