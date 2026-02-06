"""Chat input widget based on deepagents-cli"""

import time
from typing import Any, ClassVar

from textual import events
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Static, TextArea


class ChatTextArea(TextArea):
    """TextArea with custom key handling"""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding(
            "shift+enter,ctrl+j",
            "insert_newline",
            "换行",
            show=False,
            priority=True,
        ),
    ]

    class Submitted(Message):
        """Message sent when text is submitted"""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def action_insert_newline(self) -> None:
        """Insert newline"""
        self.insert("\n")

    async def _on_key(self, event: events.Key) -> None:
        """Handle key events"""
        # Shift+Enter or Ctrl+J inserts newline
        if event.key in ("shift+enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return

        # Plain Enter submits
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            value = self.text.strip()
            if value:
                self.post_message(self.Submitted(value))
            return

        await super()._on_key(event)

    def clear_text(self) -> None:
        """Clear text"""
        self.text = ""
        self.move_cursor((0, 0))


class ChatInput(Vertical):
    """Chat input with prompt indicator"""

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 0;
        background: $surface;
        border: solid $primary;
    }

    ChatInput .input-row {
        height: auto;
        width: 100%;
    }

    ChatInput .input-prompt {
        width: 3;
        height: 1;
        padding: 0 1;
        color: $primary;
        text-style: bold;
    }

    ChatInput ChatTextArea {
        width: 1fr;
        height: auto;
        min-height: 1;
        max-height: 8;
        border: none;
        background: transparent;
        padding: 0;
    }

    ChatInput ChatTextArea:focus {
        border: none;
    }

    ChatInput .input-hint {
        height: 1;
        width: 100%;
        padding: 0 1;
        color: $text-muted;
        text-align: right;
    }
    """

    class Submitted(Message):
        """Message sent when input is submitted"""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._text_area: ChatTextArea | None = None
        self._history: list[str] = []
        self._history_index: int = -1
        self._current_draft: str = ""
        self._last_esc_time: float = 0
        self._esc_double_click_threshold: float = 0.5

    def compose(self):
        """Compose layout"""
        with Horizontal(classes="input-row"):
            yield Static(">", classes="input-prompt")
            yield ChatTextArea(id="chat-input")
        yield Static("Enter 发送 | Shift+Enter 换行 | /help 帮助", classes="input-hint")

    def on_mount(self) -> None:
        """Initialize after mount"""
        self._text_area = self.query_one("#chat-input", ChatTextArea)
        self._text_area.focus()

    def on_chat_text_area_submitted(self, event: ChatTextArea.Submitted) -> None:
        """Handle submission"""
        value = event.value
        if value:
            self._history.append(value)
            self._history_index = -1
            self._current_draft = ""
            self.post_message(self.Submitted(value))
            if self._text_area:
                self._text_area.clear_text()

    def focus_input(self) -> None:
        """Focus the input"""
        if self._text_area:
            self._text_area.focus()

    def navigate_history(self, direction: str) -> None:
        """Navigate through input history

        Args:
            direction: 'up' or 'down'
        """
        if not self._text_area or not self._history:
            return

        if direction == "up":
            if self._history_index == -1:
                self._current_draft = self._text_area.text
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1

            if 0 <= self._history_index < len(self._history):
                self._text_area.text = self._history[self._history_index]
                self._text_area.move_cursor_relative(rows=1000, columns=1000)

        elif direction == "down":
            if self._history_index == -1:
                return

            self._history_index += 1

            if self._history_index >= len(self._history):
                self._text_area.text = self._current_draft
                self._history_index = -1
            else:
                self._text_area.text = self._history[self._history_index]
                self._text_area.move_cursor_relative(rows=1000, columns=1000)

    def get_history(self) -> list[str]:
        """Get input history"""
        return self._history

    def set_text(self, text: str) -> None:
        """Set input text programmatically"""
        if self._text_area:
            self._text_area.text = text
            self._text_area.move_cursor_relative(rows=1000, columns=1000)

    def check_double_esc(self) -> bool:
        """Check if ESC was pressed twice within threshold

        Returns:
            True if double-ESC detected
        """
        current_time = time.time()
        if current_time - self._last_esc_time < self._esc_double_click_threshold:
            self._last_esc_time = 0
            return True
        else:
            self._last_esc_time = current_time
            return False
