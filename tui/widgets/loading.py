"""Loading/thinking spinner widget - Minimal Modern Style"""

from textual.widgets import Static


class ThinkingSpinner(Static):
    """Animated thinking spinner with tool execution status"""

    DEFAULT_CSS = """
    ThinkingSpinner {
        height: auto;
        color: #6366f1;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__("", id="thinking-spinner")
        self._frame = 0
        self._frames = ["·", "··", "···", "····", "···", "··"]
        self._current_status = "thinking"
        self._tool_name = None

    def on_mount(self) -> None:
        self.set_interval(0.15, self._animate)

    def _animate(self) -> None:
        self._frame = (self._frame + 1) % len(self._frames)
        dots = self._frames[self._frame]
        if self._tool_name:
            self.update(f"  → {self._tool_name} {dots}")
        else:
            self.update(f"  {dots}")

    def set_status(self, status: str) -> None:
        """Update thinking status"""
        self._current_status = status
        self._tool_name = None

    def set_tool_execution(self, tool_name: str) -> None:
        """Update to show tool execution"""
        self._tool_name = tool_name
