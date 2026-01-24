"""Loading/thinking spinner widget"""

from textual.widgets import Static


class ThinkingSpinner(Static):
    """Animated thinking spinner with tool execution status"""

    DEFAULT_CSS = """
    ThinkingSpinner {
        height: auto;
        color: $accent;
        text-style: dim;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__("🤔 思考中...", id="thinking-spinner")
        self._frame = 0
        self._frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._current_status = "思考中"
        self._tool_name = None

    def on_mount(self) -> None:
        self.set_interval(0.1, self._animate)

    def _animate(self) -> None:
        self._frame = (self._frame + 1) % len(self._frames)
        if self._tool_name:
            self.update(f"{self._frames[self._frame]} 执行工具: {self._tool_name}")
        else:
            self.update(f"{self._frames[self._frame]} {self._current_status}")
    
    def set_status(self, status: str) -> None:
        """Update thinking status"""
        self._current_status = status
        self._tool_name = None
    
    def set_tool_execution(self, tool_name: str) -> None:
        """Update to show tool execution"""
        self._tool_name = tool_name
