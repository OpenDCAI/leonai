"""History browser widget - shows conversation history with arrow key navigation"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


class HistoryBrowser(ModalScreen):
    """Modal screen for browsing input history

    Usage:
    - Press ESC twice to open
    - Arrow keys to navigate
    - Enter to select
    - ESC to cancel
    """

    CSS = """
    HistoryBrowser {
        align: center middle;
    }
    
    #history-dialog {
        width: 80;
        height: 20;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #history-title {
        width: 100%;
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #history-list {
        height: 1fr;
        border: solid $primary-darken-1;
    }
    
    #history-hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    
    ListView > ListItem {
        padding: 0 1;
    }
    
    ListView > ListItem.--highlight {
        background: $primary;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_browser", "关闭"),
        ("enter", "select_history", "选择"),
    ]

    def __init__(self, history: list[str], **kwargs):
        super().__init__(**kwargs)
        self.history = history
        self.selected_index = -1

    def compose(self) -> ComposeResult:
        with Container(id="history-dialog"):
            yield Label("📜 历史输入记录", id="history-title")

            if self.history:
                with ListView(id="history-list"):
                    # 倒序显示（最新的在上面）
                    for i, msg in enumerate(reversed(self.history)):
                        # 限制显示长度
                        display_text = msg[:70] + "..." if len(msg) > 70 else msg
                        yield ListItem(Label(f"{len(self.history) - i}. {display_text}"))
            else:
                yield Label("暂无历史记录", id="history-list")

            yield Label("↑/↓: 选择  Enter: 确认  ESC: 取消", id="history-hint")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection from ListView"""
        # 计算实际的历史索引（因为是倒序显示）
        self.selected_index = len(self.history) - 1 - event.list_view.index
        self.dismiss(self.selected_index)

    def action_select_history(self) -> None:
        """Select current highlighted item"""
        list_view = self.query_one("#history-list", ListView)
        if list_view.index is not None:
            self.selected_index = len(self.history) - 1 - list_view.index
            self.dismiss(self.selected_index)

    def action_dismiss_browser(self) -> None:
        """Close without selection"""
        self.dismiss(None)
