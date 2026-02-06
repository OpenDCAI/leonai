"""Monitor Middleware - 监控容器"""
from typing import Any, Callable, Awaitable
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ModelCallResult,
)
from .base import BaseMonitor
from .token_monitor import TokenMonitor
from .context_monitor import ContextMonitor
from .state_monitor import StateMonitor, AgentState
from .runtime import AgentRuntime


class MonitorMiddleware(AgentMiddleware):
    """监控中间件

    作为容器组合多个 Monitor，在 LLM 调用前后统一调度。
    提供 AgentRuntime 聚合所有监控数据。
    """

    tools = []  # 不注入工具

    def __init__(self, context_limit: int = 100000, verbose: bool = False):
        self.verbose = verbose

        # 内置 monitors
        self._token_monitor = TokenMonitor()
        self._context_monitor = ContextMonitor(context_limit=context_limit)
        self._state_monitor = StateMonitor()

        # 可扩展的 monitors 列表
        self._monitors: list[BaseMonitor] = [
            self._token_monitor,
            self._context_monitor,
            self._state_monitor,
        ]

        # 聚合运行时
        self.runtime = AgentRuntime(
            token_monitor=self._token_monitor,
            context_monitor=self._context_monitor,
            state_monitor=self._state_monitor,
        )

        if verbose:
            print("[MonitorMiddleware] Initialized")

    def add_monitor(self, monitor: BaseMonitor) -> None:
        """添加自定义 Monitor"""
        self._monitors.append(monitor)

    def mark_ready(self) -> None:
        """标记 Agent 就绪（初始化完成后调用）"""
        self._state_monitor.mark_ready()

    def mark_terminated(self) -> None:
        """标记 Agent 终止"""
        self._state_monitor.mark_terminated()

    def mark_error(self, error: Exception | None = None) -> None:
        """标记错误状态"""
        self._state_monitor.mark_error(error)

    # ========== AgentMiddleware 接口 ==========

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """异步包装 LLM 调用，在前后调度所有 monitors"""
        # 构造请求字典供 monitors 使用
        req_dict = {"messages": request.messages}

        # 请求前
        for monitor in self._monitors:
            try:
                monitor.on_request(req_dict)
            except Exception as e:
                if self.verbose:
                    print(f"[MonitorMiddleware] on_request error: {e}")

        # 调用 LLM
        try:
            response = await handler(request)
        except Exception as e:
            self._state_monitor.mark_error(e)
            raise

        # 构造响应字典供 monitors 使用
        # ModelResponse.result 是消息列表
        messages = []
        if hasattr(response, "result"):
            messages = response.result
        elif hasattr(response, "response_metadata"):
            # 直接是 AIMessage
            messages = [response]

        resp_dict = {"messages": messages}

        # 响应后
        for monitor in self._monitors:
            try:
                monitor.on_response(req_dict, resp_dict)
            except Exception as e:
                if self.verbose:
                    print(f"[MonitorMiddleware] on_response error: {e}")

        return response

    def wrap_tool_call(self, request, handler):
        """包装工具调用（透传，不做处理）"""
        return handler(request)

    async def awrap_tool_call(self, request, handler):
        """异步包装工具调用（透传，不做处理）"""
        return await handler(request)

    # ========== 指标访问 ==========

    def get_all_metrics(self) -> dict[str, Any]:
        """获取所有 monitors 的指标"""
        metrics = {}
        for monitor in self._monitors:
            name = monitor.__class__.__name__
            metrics[name] = monitor.get_metrics()
        return metrics

    def reset_all(self) -> None:
        """重置所有 monitors"""
        for monitor in self._monitors:
            monitor.reset()
