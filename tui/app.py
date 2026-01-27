"""Main Textual App for Leon CLI"""

import asyncio
import os
import queue
import threading
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Static

from tui.widgets.chat_input import ChatInput
from tui.widgets.history_browser import HistoryBrowser
from tui.widgets.loading import ThinkingSpinner
from tui.widgets.messages import AssistantMessage, SystemMessage, ToolCallMessage, ToolResultMessage, UserMessage
from tui.widgets.status import StatusBar


class WelcomeBanner(Static):
    """Welcome banner widget"""

    DEFAULT_CSS = """
    WelcomeBanner {
        height: auto;
        margin-bottom: 1;
        color: $accent;
    }
    """

    def compose(self):
        banner = """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                  ┃
┃       ██╗     ███████╗ ██████╗ ███╗   ██╗                       ┃
┃       ██║     ██╔════╝██╔═══██╗████╗  ██║                       ┃
┃       ██║     █████╗  ██║   ██║██╔██╗ ██║                       ┃
┃       ██║     ██╔══╝  ██║   ██║██║╚██╗██║                       ┃
┃       ███████╗███████╗╚██████╔╝██║ ╚████║                       ┃
┃       ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝                       ┃
┃                                                                  ┃
┃              Proactive AI Partner                                ┃
┃              人机协同 · 主动智能                                   ┃
┃                                                                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
        yield Static(banner, id="welcome-text")


class LeonApp(App):
    """Leon Agent Textual Application"""

    CSS = """
    Screen {
        layout: vertical;
    }

    #chat-container {
        height: 1fr;
        padding: 1 2;
        background: $background;
        scrollbar-gutter: stable;
        scrollbar-size: 1 1;
    }
    
    #chat-container:focus {
        border: none;
    }
    
    /* Disable scrollbar dragging - only allow wheel scroll */
    #chat-container > ScrollBar {
        background: $surface-darken-1;
    }

    #messages {
        height: auto;
    }

    #input-container {
        height: auto;
        min-height: 3;
        max-height: 10;
        padding: 0 2 1 2;
        background: $surface;
    }

    ChatInput {
        height: 100%;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit_or_interrupt", "中断/退出", show=False),
        Binding("ctrl+d", "quit", "退出", show=False),
        Binding("ctrl+l", "clear_history", "清空历史", show=False),
        Binding("ctrl+up", "history_up", "历史上一条", show=False),
        Binding("ctrl+down", "history_down", "历史下一条", show=False),
        Binding("ctrl+e", "export_conversation", "导出对话", show=False),
        Binding("ctrl+y", "copy_last_message", "复制最后消息", show=False),
    ]

    def __init__(self, agent, workspace_root: Path, thread_id: str = "default"):
        super().__init__()
        self.agent = agent
        self.workspace_root = workspace_root
        self.thread_id = thread_id
        self._current_assistant_msg = None
        self._shown_tool_calls = set()
        self._shown_tool_results = set()
        self._message_count = 0
        self._last_assistant_message = ""
        # Agent interruption support
        self._agent_running = False
        self._agent_worker = None
        self._quit_pending = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="chat-container"):
            yield WelcomeBanner()
            yield Container(id="messages")
        with Container(id="input-container"):
            yield ChatInput(id="chat-input")
        yield StatusBar(thread_id=self.thread_id, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Focus input on mount"""
        chat_input = self.query_one("#chat-input", ChatInput)
        chat_input.focus_input()
        
        # Ensure scroll container can receive focus for scrolling
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.can_focus = True
    
    def on_key(self, event) -> None:
        """Handle global key events for double-ESC detection"""
        if event.key == "escape":
            chat_input = self.query_one("#chat-input", ChatInput)
            if chat_input.check_double_esc():
                event.prevent_default()
                event.stop()
                self.action_show_history()

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle message submission"""
        content = event.value

        # Handle special commands
        if content.lower() == "/help":
            self._show_help()
            return

        if content.lower() == "/clear":
            self.action_clear_history()
            return

        if content.lower() in ["/exit", "/quit"]:
            self.exit()
            return
        
        if content.lower() == "/history":
            self.action_show_history()
            return
        
        # Handle /rollback N command
        if content.lower().startswith("/rollback ") or content.lower().startswith("/回退 "):
            try:
                parts = content.split()
                if len(parts) == 2:
                    steps = int(parts[1])
                    self._rollback_history(steps)
                    return
            except ValueError:
                self.notify("⚠ 用法: /rollback <数字> 或 /回退 <数字>", severity="warning")
                return

        # Run async handler with worker tracking for interruption
        self._agent_running = True
        self._quit_pending = False
        self._agent_worker = self.run_worker(self._handle_submission(content), exclusive=False)
    
    async def _handle_submission(self, content: str) -> None:
        """Handle message submission asynchronously to ensure proper rendering"""
        import time
        t0 = time.perf_counter()
        
        messages_container = self.query_one("#messages", Container)
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_input = self.query_one("#chat-input", ChatInput)
        
        # CRITICAL: Use await mount() to ensure user message renders BEFORE agent starts
        user_msg = UserMessage(content)
        await messages_container.mount(user_msg)
        t_mount = (time.perf_counter() - t0) * 1000
        
        # Show thinking spinner
        thinking = ThinkingSpinner()
        await messages_container.mount(thinking)
        
        # Single scroll after mounting both widgets
        chat_container.scroll_end(animate=False)
        
        # FORCE screen update to make message visible NOW
        self.refresh()
        await asyncio.sleep(0.05)  # Give UI time to actually render
        
        # Log timing
        print(f"\n[LATENCY] User message rendered in {t_mount:.2f}ms")
        
        # NOW process with agent (user message is already visible)
        t_agent_start = time.perf_counter()
        await self._process_message(content, thinking)
        t_agent_total = (time.perf_counter() - t_agent_start) * 1000
        print(f"[LATENCY] Agent processing took {t_agent_total:.2f}ms\n")

    
    async def _process_message(self, message: str, thinking_spinner: ThinkingSpinner | None = None) -> None:
        """Process message with agent using async astream"""
        import time
        
        messages_container = self.query_one("#messages", Container)
        chat_container = self.query_one("#chat-container", VerticalScroll)

        # Reset tracking
        self._current_assistant_msg = None
        self._shown_tool_calls = set()
        self._shown_tool_results = set()
        self._tool_call_widgets = {}
        
        last_content = ""
        last_update_time = 0
        update_interval = 0.05

        config = {"configurable": {"thread_id": self.thread_id}}
        
        try:
            async for chunk in self.agent.agent.astream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode="updates",
            ):
                if not chunk:
                    continue
                
                # Process chunk
                for node_name, node_update in chunk.items():
                    if not isinstance(node_update, dict) or "messages" not in node_update:
                        continue
                    
                    new_messages = node_update["messages"]
                    if not new_messages:
                        continue
                    
                    if not isinstance(new_messages, (list, tuple)):
                        new_messages = [new_messages]
                    
                    for msg in new_messages:
                        msg_class = msg.__class__.__name__
                        
                        if msg_class == "HumanMessage":
                            continue

                        if msg_class == "AIMessage":
                            raw_content = getattr(msg, "content", "")
                            
                            if isinstance(raw_content, str):
                                content = raw_content
                            elif isinstance(raw_content, list):
                                text_parts = []
                                for block in raw_content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                content = "".join(text_parts)
                            else:
                                content = str(raw_content)
                            
                            if content and content != last_content:
                                if thinking_spinner and thinking_spinner.is_mounted:
                                    await thinking_spinner.remove()
                                    thinking_spinner = None
                                
                                if not self._current_assistant_msg:
                                    self._current_assistant_msg = AssistantMessage()
                                    await messages_container.mount(self._current_assistant_msg)

                                current_time = time.time()
                                if current_time - last_update_time >= update_interval:
                                    self._current_assistant_msg.update_content(content)
                                    last_update_time = current_time
                                else:
                                    self._current_assistant_msg.update_content(content)
                                
                                last_content = content
                                self._last_assistant_message = content
                            
                            tool_calls = getattr(msg, "tool_calls", [])
                            if tool_calls:
                                self._current_assistant_msg = None
                                
                                for tool_call in tool_calls:
                                    tool_id = tool_call.get("id", "")
                                    tool_name = tool_call.get("name", "unknown")
                                    
                                    if tool_id and tool_id not in self._shown_tool_calls:
                                        if thinking_spinner and thinking_spinner.is_mounted:
                                            thinking_spinner.set_tool_execution(tool_name)
                                        
                                        tool_widget = ToolCallMessage(
                                            tool_name,
                                            tool_call.get("args", {}),
                                        )
                                        await messages_container.mount(tool_widget)
                                        
                                        self._tool_call_widgets[tool_id] = tool_widget
                                        self._shown_tool_calls.add(tool_id)

                        elif msg_class == "ToolMessage":
                            tool_call_id = getattr(msg, "tool_call_id", None)
                            if tool_call_id and tool_call_id not in self._shown_tool_results:
                                if tool_call_id in self._tool_call_widgets:
                                    self._tool_call_widgets[tool_call_id].mark_completed()
                                
                                await messages_container.mount(ToolResultMessage(msg.content))
                                self._shown_tool_results.add(tool_call_id)

        except asyncio.CancelledError:
            # Agent was interrupted by user
            interrupt_msg = SystemMessage("⚠ 已中断")
            await messages_container.mount(interrupt_msg)
        except Exception as e:
            error_msg = AssistantMessage(f"❌ 错误: {str(e)}")
            await messages_container.mount(error_msg)
        finally:
            # Reset agent state
            self._agent_running = False
            self._agent_worker = None
            
            if thinking_spinner and thinking_spinner.is_mounted:
                await thinking_spinner.remove()
            
            if self._current_assistant_msg and last_content:
                self._current_assistant_msg.update_content(last_content)
            
            self._message_count += 1
            self._update_status_bar()
            
            chat_container.scroll_end(animate=False)
            
            chat_input = self.query_one("#chat-input", ChatInput)
            self.call_after_refresh(chat_input.focus_input)

    def action_history_up(self) -> None:
        """Navigate to previous input in history"""
        chat_input = self.query_one("#chat-input", ChatInput)
        chat_input.navigate_history("up")
    
    def action_history_down(self) -> None:
        """Navigate to next input in history"""
        chat_input = self.query_one("#chat-input", ChatInput)
        chat_input.navigate_history("down")
    
    def action_show_history(self) -> None:
        """Show history browser (double-ESC or /history)"""
        chat_input = self.query_one("#chat-input", ChatInput)
        history = chat_input.get_history()
        
        if not history:
            self.notify("暂无历史记录", severity="information")
            return
        
        def handle_history_selection(selected_index: int | None) -> None:
            """Handle history selection from browser"""
            if selected_index is not None:
                chat_input.set_text(history[selected_index])
                self.notify(f"✓ 已加载历史记录 #{selected_index + 1}")
        
        self.push_screen(HistoryBrowser(history), handle_history_selection)
    
    def _rollback_history(self, steps: int) -> None:
        """Rollback to N steps ago in history"""
        chat_input = self.query_one("#chat-input", ChatInput)
        history = chat_input.get_history()
        
        if not history:
            self.notify("暂无历史记录", severity="warning")
            return
        
        if steps < 1 or steps > len(history):
            self.notify(f"⚠ 回退步数必须在 1-{len(history)} 之间", severity="warning")
            return
        
        # 回退到倒数第N条
        target_index = len(history) - steps
        chat_input.set_text(history[target_index])
        self.notify(f"✓ 已回退到 {steps} 步前的输入")
    
    def action_copy_last_message(self) -> None:
        """Copy last assistant message to clipboard"""
        if self._last_assistant_message:
            import pyperclip
            try:
                pyperclip.copy(self._last_assistant_message)
                self.notify("✓ 已复制最后一条消息")
            except Exception:
                self.notify("⚠ 复制失败（需要安装 pyperclip）", severity="warning")
        else:
            self.notify("⚠ 没有可复制的消息", severity="warning")
    
    def action_export_conversation(self) -> None:
        """Export conversation to markdown file"""
        import datetime
        from pathlib import Path
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = self.workspace_root / f"conversation_{timestamp}.md"
        
        messages_container = self.query_one("#messages", Container)
        
        content = f"# Leon Agent 对话记录\n\n"
        content += f"**导出时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"**Thread ID**: {self.thread_id}\n\n"
        content += "---\n\n"
        
        for widget in messages_container.children:
            widget_class = widget.__class__.__name__
            
            if widget_class == "UserMessage":
                content += f"## 👤 用户\n\n{widget._content}\n\n"
            elif widget_class == "AssistantMessage":
                content += f"## 🤖 Leon\n\n{widget._content}\n\n"
            elif widget_class == "ToolCallMessage":
                content += f"### 🔧 工具调用: {widget._tool_name}\n\n"
                if widget._tool_args:
                    content += "**参数**:\n\n"
                    for k, v in widget._tool_args.items():
                        content += f"- `{k}`: {v}\n"
                content += "\n"
            elif widget_class == "ToolResultMessage":
                content += f"### 📤 工具返回\n\n```\n{widget._result}\n```\n\n"
        
        try:
            export_path.write_text(content, encoding="utf-8")
            self.notify(f"✓ 对话已导出到: {export_path.name}")
        except Exception as e:
            self.notify(f"⚠ 导出失败: {str(e)}", severity="error")
    
    def _show_help(self) -> None:
        """Show help information as system message"""
        help_text = """Leon 帮助信息

快捷键:
  • Enter: 发送消息
  • Shift+Enter: 换行
  • ESC ESC: 浏览历史输入（弹窗选择）
  • Ctrl+C: 中断当前执行 / 再按一次退出
  • Ctrl+D: 直接退出
  • Ctrl+Y: 复制最后一条消息
  • Ctrl+E: 导出对话为 Markdown
  • Ctrl+L: 清空对话历史

命令:
  • /help: 显示此帮助信息
  • /history: 查看历史输入
  • /rollback N 或 /回退 N: 回退到N步前的输入
  • /clear: 清空对话历史
  • /exit 或 /quit: 退出程序
"""
        messages_container = self.query_one("#messages")
        chat_container = self.query_one("#chat-container", VerticalScroll)
        
        help_msg = SystemMessage(help_text)
        messages_container.mount(help_msg)
        # Scroll after help message is mounted
        self.call_after_refresh(lambda: chat_container.scroll_end(animate=False))
    
    def _update_status_bar(self) -> None:
        """Update status bar with message count"""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_stats(self._message_count)
    
    def action_quit_or_interrupt(self) -> None:
        """Handle Ctrl+C - interrupt agent or quit on double press.
        
        Priority:
        1. If agent is running, interrupt it
        2. If double press (quit_pending), quit
        3. Otherwise show quit hint
        """
        # If agent is running, interrupt it
        if self._agent_running and self._agent_worker:
            self._agent_worker.cancel()
            self._quit_pending = False
            self.notify("⚠ 正在中断...", timeout=2)
            return
        
        # Double Ctrl+C to quit
        if self._quit_pending:
            self.exit()
        else:
            self._quit_pending = True
            self.notify("再按一次 Ctrl+C 退出，或按 Ctrl+D 直接退出", timeout=3)
    
    def action_clear_history(self) -> None:
        """Clear chat history"""
        import uuid

        # Generate new thread ID
        self.thread_id = f"chat-{uuid.uuid4().hex[:8]}"

        # Clear messages
        messages_container = self.query_one("#messages", Container)
        messages_container.remove_children()

        # Re-add welcome banner
        messages_container.mount(WelcomeBanner())

        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_thread(self.thread_id)

        # Reset counters
        self._message_count = 0
        self._last_assistant_message = ""
        
        # Show notification
        self.notify("✓ 对话历史已清空")


def run_tui(agent, workspace_root: Path, thread_id: str = "default") -> None:
    """Run the Textual TUI"""
    app = LeonApp(agent, workspace_root, thread_id)
    app.run()
