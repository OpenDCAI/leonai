"""Checkpoint browser widget for time travel"""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from tui.time_travel import CheckpointInfo


class CheckpointItem(Static):
    """A single checkpoint item in the list"""

    DEFAULT_CSS = """
    CheckpointItem {
        height: auto;
        padding: 0 1;
    }

    CheckpointItem .checkpoint-header {
        color: $text;
    }

    CheckpointItem .checkpoint-message {
        color: $text-muted;
        padding-left: 2;
    }

    CheckpointItem .checkpoint-ops {
        color: $warning;
        padding-left: 2;
    }

    CheckpointItem.current .checkpoint-header {
        color: $success;
    }
    """

    def __init__(self, checkpoint: CheckpointInfo, index: int):
        super().__init__()
        self.checkpoint = checkpoint
        self.index = index
        if checkpoint.is_current:
            self.add_class("current")

    def compose(self) -> ComposeResult:
        cp = self.checkpoint
        time_str = self._format_time(cp.timestamp)
        current_marker = " (当前)" if cp.is_current else ""

        yield Static(
            f"#{self.index + 1}{current_marker}  {time_str}",
            classes="checkpoint-header",
        )
        if cp.user_message:
            yield Static(f'"{cp.user_message}"', classes="checkpoint-message")
        if cp.file_operations_count > 0:
            yield Static(
                f"📝 {cp.file_operations_count} 个文件操作",
                classes="checkpoint-ops",
            )

    def _format_time(self, dt: datetime) -> str:
        """Format datetime as relative time"""
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return "刚刚"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} 分钟前"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} 小时前"
        else:
            days = int(seconds / 86400)
            return f"{days} 天前"


class CheckpointBrowser(ModalScreen):
    """Modal screen for browsing checkpoints and time travel"""

    CSS = """
    CheckpointBrowser {
        align: center middle;
    }

    #checkpoint-dialog {
        width: 70;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #checkpoint-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #checkpoint-list {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-1;
        margin-bottom: 1;
        overflow-y: auto;
    }

    #checkpoint-warning {
        width: 100%;
        height: auto;
        color: $warning;
        margin-bottom: 1;
        padding: 0 1;
    }

    #checkpoint-buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
    }

    #checkpoint-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("enter", "select", "确定"),
    ]

    def __init__(self, checkpoints: list[CheckpointInfo], current_checkpoint_id: str):
        super().__init__()
        self.checkpoints = checkpoints
        self.current_checkpoint_id = current_checkpoint_id
        self.selected_index: int | None = None

    def compose(self) -> ComposeResult:
        with Container(id="checkpoint-dialog"):
            yield Label("⏪ 时间旅行 - 回退到历史节点", id="checkpoint-title")
            with ListView(id="checkpoint-list"):
                for i, cp in enumerate(self.checkpoints):
                    yield ListItem(CheckpointItem(cp, i))
            yield Static("", id="checkpoint-warning")
            with Container(id="checkpoint-buttons"):
                yield Button("回退到此处", variant="primary", id="rewind-btn")
                yield Button("取消", id="cancel-btn")

    def on_mount(self) -> None:
        """Select the current checkpoint by default"""
        list_view = self.query_one("#checkpoint-list", ListView)
        # Find current checkpoint index
        for i, cp in enumerate(self.checkpoints):
            if cp.is_current:
                list_view.index = i
                break

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update warning when selection changes"""
        if event.list_view.index is None:
            return

        self.selected_index = event.list_view.index
        selected_cp = self.checkpoints[self.selected_index]

        # Count operations to revert
        ops_to_revert = 0
        checkpoints_to_revert = []
        for i, cp in enumerate(self.checkpoints):
            if i > self.selected_index:
                ops_to_revert += cp.file_operations_count
                checkpoints_to_revert.append(f"#{i + 1}")

        warning = self.query_one("#checkpoint-warning", Static)
        if checkpoints_to_revert:
            warning.update(f"⚠ 回退将撤销 {', '.join(checkpoints_to_revert)} 的 {ops_to_revert} 个文件修改")
        else:
            warning.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rewind-btn":
            self._do_rewind()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        self._do_rewind()

    def _do_rewind(self) -> None:
        """Execute rewind to selected checkpoint"""
        list_view = self.query_one("#checkpoint-list", ListView)
        if list_view.index is not None:
            selected_cp = self.checkpoints[list_view.index]
            if not selected_cp.is_current:
                self.dismiss(selected_cp.checkpoint_id)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle double-click or Enter on list item"""
        self._do_rewind()
