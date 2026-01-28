"""Thread browser widget for switching conversations"""
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class ThreadBrowser(ModalScreen):
    """Modal screen for browsing and selecting threads"""

    CSS = """
    ThreadBrowser {
        align: center middle;
    }

    #thread-dialog {
        width: 60;
        height: 25;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #thread-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #thread-list {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-1;
        margin-bottom: 1;
    }

    #thread-buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
    }

    #thread-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, threads: list[str], current_thread: str):
        super().__init__()
        self.threads = threads
        self.current_thread = current_thread
        self.selected_thread = None

    def compose(self) -> ComposeResult:
        with Container(id="thread-dialog"):
            yield Label("选择对话 Thread", id="thread-title")
            with ListView(id="thread-list"):
                for thread in self.threads:
                    marker = " (当前)" if thread == self.current_thread else ""
                    yield ListItem(Label(f"{thread}{marker}"))
            with Container(id="thread-buttons"):
                yield Button("确定", variant="primary", id="select-btn")
                yield Button("取消", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-btn":
            list_view = self.query_one("#thread-list", ListView)
            if list_view.index is not None:
                self.selected_thread = self.threads[list_view.index]
            self.dismiss(self.selected_thread)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle double-click or Enter on list item"""
        self.selected_thread = self.threads[event.list_view.index]
        self.dismiss(self.selected_thread)
