"""Main Textual App for Leon CLI"""

import asyncio
import uuid
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Static

from tui.operations import current_checkpoint_id, current_thread_id
from tui.widgets.chat_input import ChatInput
from tui.widgets.checkpoint_browser import CheckpointBrowser
from tui.widgets.history_browser import HistoryBrowser
from tui.widgets.loading import ThinkingSpinner
from tui.widgets.messages import AssistantMessage, SystemMessage, ToolCallMessage, ToolResultMessage, UserMessage
from tui.widgets.status import StatusBar
from tui.widgets.thread_selector import ThreadSelector

# Import sandbox thread_id setter
try:
    from sandbox.thread_context import set_current_thread_id as set_sandbox_thread_id
except ImportError:
    set_sandbox_thread_id = None
from middleware.monitor import AgentState
from middleware.queue import QueueMode, get_queue_manager


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
        # 注意：不绑定 ctrl+c，让终端处理复制。用 ctrl+d 或 escape 退出
        Binding("ctrl+d", "quit", "退出", show=False),
        Binding("ctrl+l", "clear_history", "清空历史", show=False),
        Binding("ctrl+up", "history_up", "历史上一条", show=False),
        Binding("ctrl+down", "history_down", "历史下一条", show=False),
        Binding("ctrl+e", "export_conversation", "导出对话", show=False),
        Binding("ctrl+y", "copy_last_message", "复制最后消息", show=False),
        Binding("escape", "interrupt_agent", "中断", show=False),
    ]

    def __init__(self, agent, workspace_root: Path, thread_id: str = "default", session_mgr=None):
        super().__init__()
        self.agent = agent
        self.workspace_root = workspace_root
        self.thread_id = thread_id
        self.session_mgr = session_mgr
        self._current_assistant_msg = None
        self._shown_tool_calls = set()
        self._shown_tool_results = set()
        self._message_count = 0
        self._last_assistant_message = ""
        # Agent interruption support
        self._agent_worker = None
        self._quit_pending = False
        # Queue mode from agent config
        self._queue_mode = self._parse_queue_mode(getattr(agent, "queue_mode", "steer"))
        get_queue_manager().set_mode(self._queue_mode)

        # 注册状态变化回调：IDLE 时自动处理 followup
        if hasattr(agent, "runtime"):
            agent.runtime.state.on_state_changed(self._on_state_changed)

    @property
    def _is_agent_active(self) -> bool:
        """Agent 是否正在执行（基于 AgentState 状态机）"""
        if hasattr(self.agent, "runtime"):
            return self.agent.runtime.is_running()
        return False

    def _on_state_changed(self, old_state: AgentState, new_state: AgentState) -> None:
        """状态变化回调：状态驱动的队列处理"""
        if new_state == AgentState.IDLE:
            # IDLE 时自动处理 followup 队列
            self.call_after_refresh(self._state_driven_followup)

    QUEUE_MODE_MAP = {
        "steer": QueueMode.STEER,
        "followup": QueueMode.FOLLOWUP,
        "collect": QueueMode.COLLECT,
        "steer_backlog": QueueMode.STEER_BACKLOG,
        "steer-backlog": QueueMode.STEER_BACKLOG,
        "interrupt": QueueMode.INTERRUPT,
    }

    def _parse_queue_mode(self, mode_str: str) -> QueueMode:
        """Parse queue mode string to enum"""
        return self.QUEUE_MODE_MAP.get(mode_str.lower(), QueueMode.STEER)

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

        # 加载历史 messages
        self.run_worker(self._load_history(), exclusive=False)

    def on_click(self, event) -> None:
        """Refocus input after any click"""
        # 延迟执行，让其他点击事件先处理
        self.call_after_refresh(self._refocus_input)

    def _refocus_input(self) -> None:
        """Refocus input if no modal is open"""
        if self.query("HistoryBrowser, CheckpointBrowser, ThreadSelector"):
            return
        self.query_one("#chat-input", ChatInput).focus_input()

    def on_key(self, event) -> None:
        """Handle global key events for double-ESC detection"""
        if event.key == "escape":
            chat_input = self.query_one("#chat-input", ChatInput)
            if chat_input.check_double_esc():
                event.prevent_default()
                event.stop()
                self.action_time_travel()

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle message submission"""
        content = event.value

        # Handle special commands
        if self._handle_special_command(content):
            return

        # Queue mode routing: if agent is active, queue the message
        if self._is_agent_active:
            self._handle_active_agent_message(content)
            return

        # Resume from SUSPENDED/ERROR or start new run
        self._start_agent_run(content)

    def _handle_special_command(self, content: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        cmd = content.lower()

        if cmd == "/help":
            self._show_help()
            return True

        if cmd == "/clear":
            self.action_clear_history()
            return True

        if cmd in ["/exit", "/quit"]:
            self.exit()
            return True

        if cmd == "/history":
            self.action_show_history()
            return True

        if cmd == "/resume":
            self._show_resume_dialog()
            return True

        if cmd.startswith("/rollback ") or cmd.startswith("/回退 "):
            self._handle_rollback_command(content)
            return True

        if cmd.startswith("/mode "):
            self._handle_mode_command(content)
            return True

        if cmd == "/compact":
            self._trigger_compact()
            return True

        return False

    def _handle_rollback_command(self, content: str) -> None:
        """Handle /rollback N command"""
        try:
            parts = content.split()
            if len(parts) == 2:
                steps = int(parts[1])
                self._rollback_history(steps)
        except ValueError:
            self.notify("⚠ 用法: /rollback <数字> 或 /回退 <数字>", severity="warning")

    def _handle_mode_command(self, content: str) -> None:
        """Handle /mode command to switch queue mode"""
        mode_name = content[6:].strip().lower()
        if mode_name in self.QUEUE_MODE_MAP:
            self._queue_mode = self.QUEUE_MODE_MAP[mode_name]
            get_queue_manager().set_mode(self._queue_mode)
            self.notify(f"✓ 队列模式: {mode_name}")
        else:
            self.notify(
                f"⚠ 未知模式: {mode_name}。可用: steer, followup, collect, steer-backlog, interrupt",
                severity="warning",
            )

    def _handle_active_agent_message(self, content: str) -> None:
        """Handle message when agent is active (queue or interrupt)"""
        queue_manager = get_queue_manager()

        if self._queue_mode == QueueMode.INTERRUPT:
            if self._agent_worker:
                self._agent_worker.cancel()
                self.notify("⚠ 已中断")
        else:
            queue_manager.enqueue(content, self._queue_mode)
            mode_labels = {
                QueueMode.STEER: "转向",
                QueueMode.FOLLOWUP: "排队",
                QueueMode.COLLECT: "收集",
                QueueMode.STEER_BACKLOG: "转向+排队",
            }
            label = mode_labels.get(self._queue_mode, "排队")
            self.notify(f"✓ 消息已{label}")

    def _start_agent_run(self, content: str) -> None:
        """Start agent run, handling state transitions"""
        current = self.agent.runtime.current_state

        if current == AgentState.SUSPENDED:
            self.agent.runtime.transition(AgentState.ACTIVE)
        elif current == AgentState.ERROR:
            self.agent.runtime.transition(AgentState.RECOVERING)
            self.agent.runtime.transition(AgentState.READY)
            self.agent.runtime.set_flag("hasError", False)
            self.agent.runtime.transition(AgentState.ACTIVE)
        else:
            self.agent.runtime.transition(AgentState.ACTIVE)

        self._quit_pending = False
        self._agent_worker = self.run_worker(self._handle_submission(content), exclusive=False)

    def _extract_text_content(self, msg) -> str:
        """Extract text content from AIMessage"""
        raw_content = getattr(msg, "content", "")

        if isinstance(raw_content, str):
            return raw_content

        if isinstance(raw_content, list):
            text_parts = []
            for block in raw_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            return "".join(text_parts)

        return str(raw_content)

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

        # Set context variables for file operation recording
        current_thread_id.set(self.thread_id)
        # Set sandbox thread_id if sandbox middleware is available
        if set_sandbox_thread_id:
            set_sandbox_thread_id(self.thread_id)
        # Eagerly create sandbox session before invoke (avoids sync SQLite during async tool calls)
        if hasattr(self.agent, "_sandbox"):
            self.agent._sandbox.ensure_session(self.thread_id)
        # Generate a checkpoint ID for this interaction
        checkpoint_id = f"{self.thread_id}-{uuid.uuid4().hex[:8]}"
        current_checkpoint_id.set(checkpoint_id)

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
                            content = self._extract_text_content(msg)

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
            # 中断 → SUSPENDED
            self.agent.runtime.transition(AgentState.SUSPENDED)
        except Exception as e:
            error_msg = AssistantMessage(f"❌ 错误: {str(e)}")
            await messages_container.mount(error_msg)
            # 错误 → ERROR
            self.agent.runtime.state.mark_error(e)
        finally:
            # ACTIVE → IDLE（仅在正常完成时，中断/错误已在 except 中处理）
            if self.agent.runtime.current_state == AgentState.ACTIVE:
                self.agent.runtime.transition(AgentState.IDLE)
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

            # followup 由 _on_state_changed 回调在 IDLE 时自动触发

    def _state_driven_followup(self) -> None:
        """状态驱动的 followup 处理（由 IDLE 状态回调触发）"""
        queue_manager = get_queue_manager()

        # flush collected messages
        collected = queue_manager.flush_collect()
        if collected:
            queue_manager.enqueue(collected, QueueMode.FOLLOWUP)

        # process followup queue
        followup_content = queue_manager.get_followup()
        if followup_content:
            self.agent.runtime.transition(AgentState.ACTIVE)
            self._quit_pending = False
            self._agent_worker = self.run_worker(self._handle_submission(followup_content), exclusive=False)

    def _trigger_compact(self) -> None:
        """Handle /compact command — manual context compaction"""
        if not hasattr(self.agent, "_memory_middleware"):
            self.notify("⚠ Memory 中间件未启用", severity="warning")
            return
        self.run_worker(self._do_compact(), exclusive=False)

    async def _do_compact(self) -> None:
        """Execute manual compaction asynchronously"""
        config = {"configurable": {"thread_id": self.thread_id}}
        try:
            state = await self.agent.agent.aget_state(config)
            if not state or not state.values.get("messages"):
                self.notify("⚠ 没有消息可压缩", severity="warning")
                return

            messages = state.values["messages"]
            result = await self.agent._memory_middleware.force_compact(messages)
            if result:
                stats = result["stats"]
                self.notify(f"✓ 压缩完成: {stats['summarized']} 条消息已摘要，保留 {stats['kept']} 条近期消息")
            else:
                self.notify("⚠ 消息不足，无需压缩", severity="information")
        except Exception as e:
            self.notify(f"⚠ 压缩失败: {e}", severity="error")

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
            # Always refocus input after dialog closes
            self.call_after_refresh(chat_input.focus_input)

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

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = self.workspace_root / f"conversation_{timestamp}.md"

        messages_container = self.query_one("#messages", Container)

        content = "# Leon Agent 对话记录\n\n"
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
  • ESC ESC: 时间旅行（回退到历史节点）
  • Ctrl+C: 中断当前执行 / 再按一次退出
  • Ctrl+D: 直接退出
  • Ctrl+Y: 复制最后一条消息
  • Ctrl+E: 导出对话为 Markdown
  • Ctrl+L: 清空对话历史

命令:
  • /help: 显示此帮助信息
  • /history: 查看历史输入
  • /resume: 切换到其他对话
  • /rollback N 或 /回退 N: 回退到N步前的输入
  • /mode <模式>: 切换队列模式
  • /compact: 手动压缩上下文（生成摘要，释放 token 空间）
  • /clear: 清空对话历史
  • /exit 或 /quit: 退出程序

队列模式 (Agent 运行时输入消息的处理方式):
  • steer: 注入当前运行，改变执行方向（默认）
  • followup: 等当前运行结束后处理
  • collect: 收集多条消息，合并后处理
  • steer-backlog: 注入 + 保留为 followup
  • interrupt: 中断当前运行
"""
        messages_container = self.query_one("#messages")
        chat_container = self.query_one("#chat-container", VerticalScroll)

        help_msg = SystemMessage(help_text)
        messages_container.mount(help_msg)
        # Scroll after help message is mounted
        self.call_after_refresh(lambda: chat_container.scroll_end(animate=False))

    def _update_status_bar(self) -> None:
        """Update status bar with message count and runtime status"""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_stats(self._message_count)

        # 更新运行时状态
        if hasattr(self.agent, "runtime"):
            runtime_status = self.agent.runtime.get_status_line()
            status_bar.update_runtime_status(runtime_status)

    def action_interrupt_agent(self) -> None:
        """Handle ESC - interrupt running agent"""
        if self._is_agent_active and self._agent_worker:
            self._agent_worker.cancel()
            self.notify("⚠ 正在中断...", timeout=2)

    def action_quit_or_interrupt(self) -> None:
        """Handle Ctrl+C - interrupt agent or quit on double press"""
        if self._is_agent_active and self._agent_worker:
            self._agent_worker.cancel()
            self._quit_pending = False
            self.notify("⚠ 正在中断...", timeout=2)
            return

        if self._quit_pending:
            self.exit()
        else:
            self._quit_pending = True
            self.notify("再按一次 Ctrl+C 退出，或按 Ctrl+D 直接退出", timeout=3)

    def action_clear_history(self) -> None:
        """Clear chat history"""
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

        # Save new thread
        if self.session_mgr:
            self.session_mgr.save_session(self.thread_id)

        # Show notification
        self.notify("✓ 对话历史已清空")

    def action_time_travel(self) -> None:
        """Time travel - rewind to a previous checkpoint (ESC ESC)"""
        if not hasattr(self.agent, "checkpointer"):
            self.notify("⚠ 时间旅行功能不可用", severity="warning")
            return

        from tui.time_travel import TimeTravelManager

        time_travel_mgr = TimeTravelManager()
        checkpoints = time_travel_mgr.get_checkpoints(self.thread_id, user_turns_only=True)

        if not checkpoints:
            self.notify("暂无历史节点", severity="information")
            return

        current_checkpoint_id_val = checkpoints[-1].checkpoint_id if checkpoints else ""

        def handle_rewind(target_checkpoint_id: str | None) -> None:
            # Always refocus input after dialog closes
            chat_input = self.query_one("#chat-input", ChatInput)
            self.call_after_refresh(chat_input.focus_input)

            if not target_checkpoint_id:
                return

            # Execute rewind
            result = time_travel_mgr.rewind_to(self.thread_id, target_checkpoint_id)

            if result.success:
                # Reload the conversation from the target checkpoint
                messages_container = self.query_one("#messages", Container)
                messages_container.remove_children()
                messages_container.mount(WelcomeBanner())

                # Reset counters
                self._message_count = 0
                self._last_assistant_message = ""

                # Reload history
                self.run_worker(self._load_history(), exclusive=False)

                self.notify(f"✓ {result.message}")
            else:
                self.notify(f"⚠ {result.message}", severity="warning")

        self.push_screen(CheckpointBrowser(checkpoints, current_checkpoint_id_val), handle_rewind)

    def _show_resume_dialog(self) -> None:
        """Show dialog to switch to another conversation (/resume command)"""
        if not self.session_mgr:
            self.notify("⚠ Session 管理器未初始化", severity="warning")
            return

        threads = self.session_mgr.get_threads()
        if not threads:
            self.notify("暂无历史对话", severity="information")
            return

        # Get thread info for display
        thread_info = {}
        if hasattr(self.agent, "checkpointer"):
            from tui.time_travel import TimeTravelManager

            time_travel_mgr = TimeTravelManager()
            for tid in threads:
                try:
                    info = time_travel_mgr.get_thread_summary(tid)
                    thread_info[tid] = info
                except Exception:
                    pass

        def handle_thread_selection(selected_thread: str | None) -> None:
            if selected_thread and selected_thread != self.thread_id:
                self.thread_id = selected_thread
                self.session_mgr.save_session(self.thread_id)

                # 清空当前消息
                messages_container = self.query_one("#messages", Container)
                messages_container.remove_children()
                messages_container.mount(WelcomeBanner())

                # 更新状态栏
                status_bar = self.query_one("#status-bar", StatusBar)
                status_bar.update_thread(self.thread_id)

                # 重置计数器
                self._message_count = 0
                self._last_assistant_message = ""

                # 加载历史
                self.run_worker(self._load_history(), exclusive=False)
                self.notify(f"✓ 已切换到对话: {self.thread_id}")

        self.push_screen(ThreadSelector(threads, self.thread_id, thread_info), handle_thread_selection)

    async def _load_history(self) -> None:
        """加载历史 messages"""
        try:
            config = {"configurable": {"thread_id": self.thread_id}}
            state = await self.agent.agent.aget_state(config)

            if not state or not state.values.get("messages"):
                return

            messages = state.values["messages"]
            if not messages:
                return

            messages_container = self.query_one("#messages", Container)
            chat_container = self.query_one("#chat-container", VerticalScroll)

            # 移除 welcome banner
            try:
                welcome = messages_container.query_one(WelcomeBanner)
                await welcome.remove()
            except Exception:
                pass

            # 渲染历史消息
            for msg in messages:
                await self._render_history_message(msg, messages_container)

            # 更新状态栏
            self._update_status_bar()

            # 滚动到底部
            chat_container.scroll_end(animate=False)

            if self._message_count > 0:
                self.notify(f"✓ 已加载 {self._message_count} 条历史消息")
        except Exception as e:
            self.notify(f"⚠ 加载历史失败: {str(e)}", severity="warning")

    async def _render_history_message(self, msg, messages_container: Container) -> None:
        """Render a single history message"""
        msg_class = msg.__class__.__name__

        if msg_class == "HumanMessage":
            await messages_container.mount(UserMessage(msg.content))
            self._message_count += 1

        elif msg_class == "AIMessage":
            content = self._extract_text_content(msg)
            if content:
                await messages_container.mount(AssistantMessage(content))
                self._last_assistant_message = content

            # 显示 tool calls
            tool_calls = getattr(msg, "tool_calls", [])
            for tool_call in tool_calls:
                await messages_container.mount(
                    ToolCallMessage(tool_call.get("name", "unknown"), tool_call.get("args", {}))
                )

        elif msg_class == "ToolMessage":
            await messages_container.mount(ToolResultMessage(msg.content))


def run_tui(agent, workspace_root: Path, thread_id: str = "default", session_mgr=None) -> None:
    """Run the Textual TUI"""
    app = LeonApp(agent, workspace_root, thread_id, session_mgr)
    app.run()
