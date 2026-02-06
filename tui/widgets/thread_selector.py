"""Thread selector widget for switching conversations"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class ThreadItem(Static):
    """A single thread item in the list"""

    DEFAULT_CSS = """
    ThreadItem {
        height: auto;
        padding: 0 1;
    }

    ThreadItem .thread-id {
        color: $text;
    }

    ThreadItem .thread-info {
        color: $text-muted;
        padding-left: 2;
    }

    ThreadItem.current .thread-id {
        color: $success;
    }
    """

    def __init__(self, thread_id: str, is_current: bool = False, info: dict | None = None):
        super().__init__()
        self.thread_id = thread_id
        self.is_current = is_current
        self.info = info or {}
        if is_current:
            self.add_class("current")

    def compose(self) -> ComposeResult:
        current_marker = " (当前)" if self.is_current else ""
        yield Static(f"{self.thread_id}{current_marker}", classes="thread-id")

        # Show additional info if available
        info_parts = []
        if self.info.get("checkpoint_count"):
            info_parts.append(f"{self.info['checkpoint_count']} 条消息")
        if self.info.get("files_modified"):
            info_parts.append(f"{self.info['files_modified']} 个文件修改")

        if info_parts:
            yield Static(" · ".join(info_parts), classes="thread-info")


class ThreadSelector(ModalScreen):
    """Modal screen for selecting/switching threads"""

    CSS = """
    ThreadSelector {
        align: center middle;
    }

    #thread-dialog {
        width: 65;
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

    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("enter", "select", "确定"),
    ]

    def __init__(
        self,
        threads: list[str],
        current_thread: str,
        thread_info: dict[str, dict] | None = None,
    ):
        super().__init__()
        self.threads = threads
        self.current_thread = current_thread
        self.thread_info = thread_info or {}
        self.selected_thread: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="thread-dialog"):
            yield Label("📂 切换对话", id="thread-title")
            with ListView(id="thread-list"):
                for thread_id in self.threads:
                    is_current = thread_id == self.current_thread
                    info = self.thread_info.get(thread_id, {})
                    yield ListItem(ThreadItem(thread_id, is_current, info))
            with Container(id="thread-buttons"):
                yield Button("切换", variant="primary", id="select-btn")
                yield Button("取消", id="cancel-btn")

    def on_mount(self) -> None:
        """Select current thread by default"""
        list_view = self.query_one("#thread-list", ListView)
        for i, thread_id in enumerate(self.threads):
            if thread_id == self.current_thread:
                list_view.index = i
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-btn":
            self._do_select()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        self._do_select()

    def _do_select(self) -> None:
        """Select the highlighted thread"""
        list_view = self.query_one("#thread-list", ListView)
        if list_view.index is not None:
            self.selected_thread = self.threads[list_view.index]
            self.dismiss(self.selected_thread)
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle double-click or Enter on list item"""
        self._do_select()
