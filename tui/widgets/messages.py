"""Message widgets for chat display"""

from typing import Any

from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Markdown, Static


class UserMessage(Static):
    """User message widget"""

    DEFAULT_CSS = """
    UserMessage {
        height: auto;
        padding: 0 1;
        margin: 1 0;
        background: $surface;
        border-left: thick $primary;
    }
    """

    def __init__(self, content: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._content = content

    def compose(self):
        text = Text()
        text.append("👤 你: ", style="bold #10b981")
        text.append(self._content)
        yield Static(text)


class SystemMessage(Static):
    """System message widget for help and notifications"""

    DEFAULT_CSS = """
    SystemMessage {
        height: auto;
        padding: 1 2;
        margin: 1 0;
        background: $panel;
        border: solid $accent;
    }
    """

    def __init__(self, content: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._content = content

    def compose(self):
        text = Text()
        text.append("ℹ️  ", style="bold cyan")
        text.append(self._content, style="cyan")
        yield Static(text)


class AssistantMessage(Vertical):
    """Assistant message widget with markdown support"""

    DEFAULT_CSS = """
    AssistantMessage {
        height: auto;
        padding: 0 1;
        margin: 1 0;
    }

    AssistantMessage Markdown {
        padding: 0;
        margin: 0;
    }
    """

    def __init__(self, content: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._content = content
        self._markdown = None

    def compose(self):
        yield Markdown("", id="assistant-content")

    def on_mount(self) -> None:
        self._markdown = self.query_one("#assistant-content", Markdown)
        if self._content:
            self.update_content(self._content)

    def update_content(self, content: str) -> None:
        """Update message content - for streaming"""
        # Ensure content is string
        if isinstance(content, list):
            # Extract text from multimodal content
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)
        
        self._content = content
        if self._markdown:
            prefix = "🤖 **Leon**: "
            # Force update to trigger re-render
            self._markdown.update(prefix + content)
            # Refresh to ensure immediate display
            self._markdown.refresh()

    def append_content(self, text: str) -> None:
        """Append to message content (for streaming)"""
        self._content += text
        self.update_content(self._content)


class ToolCallMessage(Vertical):
    """Tool call message widget with streaming status support"""

    DEFAULT_CSS = """
    ToolCallMessage {
        height: auto;
        padding: 0 1;
        margin: 1 0;
        background: $surface-darken-1;
        border-left: thick $warning;
    }
    
    ToolCallMessage .tool-status {
        color: $warning;
        text-style: italic;
    }
    """

    def __init__(self, tool_name: str, tool_args: dict, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._tool_args = tool_args
        self._status = "执行中..."
        self._status_widget = None

    def compose(self):
        text = Text()
        text.append("🔧 ", style="bold yellow")
        text.append(f"调用工具: ", style="yellow")
        text.append(self._tool_name, style="bold yellow")
        text.append("\n")

        if self._tool_args:
            text.append("　　　参数:\n", style="yellow")
            for key, value in self._tool_args.items():
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                text.append(f"　　　　　{key}: ", style="yellow")
                text.append(f"{value_str}\n", style="dim")

        yield Static(text)
        yield Static(f"⚡ {self._status}", classes="tool-status", id="tool-status")
    
    def on_mount(self) -> None:
        """Cache status widget reference"""
        self._status_widget = self.query_one("#tool-status", Static)
    
    def update_status(self, status: str) -> None:
        """Update tool execution status"""
        self._status = status
        if self._status_widget:
            self._status_widget.update(f"⚡ {status}")
    
    def mark_completed(self) -> None:
        """Mark tool execution as completed"""
        self.update_status("✅ 完成")
        if self._status_widget:
            self._status_widget.styles.color = "green"


class ToolResultMessage(Static):
    """Tool result message widget"""

    DEFAULT_CSS = """
    ToolResultMessage {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        background: $surface-darken-1;
        border-left: thick $success;
    }
    """

    def __init__(self, result: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._result = result

    def compose(self):
        text = Text()
        text.append("📤 ", style="bold cyan")
        text.append("工具返回:\n", style="cyan")

        result_str = str(self._result)
        if len(result_str) > 500:
            result_str = result_str[:500] + f"... (共 {len(result_str)} 字符)"

        for line in result_str.splitlines():
            text.append(f"   {line}\n", style="dim")

        yield Static(text)
