"""Agent 运行时状态聚合"""
from typing import Any
from .token_monitor import TokenMonitor
from .context_monitor import ContextMonitor
from .state_monitor import StateMonitor, AgentState, AgentFlags


class AgentRuntime:
    """聚合所有 Monitor 的数据，提供统一的状态访问接口"""

    def __init__(
        self,
        token_monitor: TokenMonitor,
        context_monitor: ContextMonitor,
        state_monitor: StateMonitor,
    ):
        self.token = token_monitor
        self.context = context_monitor
        self.state = state_monitor

    # ========== 状态代理 ==========

    @property
    def current_state(self) -> AgentState:
        return self.state.state

    @property
    def flags(self) -> AgentFlags:
        return self.state.flags

    def transition(self, new_state: AgentState) -> bool:
        return self.state.transition(new_state)

    def set_flag(self, name: str, value: bool) -> None:
        self.state.set_flag(name, value)

    def can_accept_task(self) -> bool:
        return self.state.can_accept_task()

    def is_running(self) -> bool:
        return self.state.is_running()

    # ========== Token 代理 ==========

    @property
    def total_tokens(self) -> int:
        return self.token.total_tokens

    @property
    def prompt_tokens(self) -> int:
        return self.token.prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self.token.completion_tokens

    # ========== 上下文代理 ==========

    @property
    def message_count(self) -> int:
        return self.context.message_count

    @property
    def estimated_context_tokens(self) -> int:
        return self.context.estimated_tokens

    def is_context_near_limit(self) -> bool:
        return self.context.is_near_limit()

    # ========== 聚合输出 ==========

    def get_status_dict(self) -> dict[str, Any]:
        """返回完整状态字典"""
        return {
            "state": self.state.get_metrics(),
            "tokens": self.token.get_metrics(),
            "context": self.context.get_metrics(),
        }

    def get_status_line(self) -> str:
        """返回单行状态，用于 TUI 状态栏"""
        parts = [f"[{self.current_state.value.upper()}]"]

        # 标志位
        if self.flags.isStreaming:
            parts.append("streaming")
        if self.flags.isWaiting:
            parts.append("waiting")
        if self.flags.isBlocked:
            parts.append("blocked")
        if self.flags.hasError:
            parts.append("error")

        # Token 使用
        if self.total_tokens > 0:
            parts.append(f"tokens:{self.total_tokens}")

        # 上下文
        ctx = self.context.get_metrics()
        if ctx["usage_percent"] > 0:
            parts.append(f"ctx:{ctx['usage_percent']:.0f}%")

        return " | ".join(parts)
