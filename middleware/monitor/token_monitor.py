"""Token 使用量监控"""
from typing import Any
from .base import BaseMonitor


class TokenMonitor(BaseMonitor):
    """追踪 Token 使用量

    从 AIMessage 的 response_metadata 中提取 token 统计，
    兼容 OpenAI 和 Anthropic 两种格式。
    """

    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.call_count = 0

    def on_request(self, request: dict[str, Any]) -> None:
        """请求前：计数"""
        self.call_count += 1

    def on_response(self, request: dict[str, Any], response: dict[str, Any]) -> None:
        """响应后：从 response_metadata 提取 token 统计"""
        messages = response.get("messages", [])
        if not isinstance(messages, list):
            messages = [messages]

        # 从最后一条 AIMessage 提取
        for msg in reversed(messages):
            if not hasattr(msg, "response_metadata"):
                continue

            metadata = msg.response_metadata
            if not metadata:
                continue

            # OpenAI 格式: token_usage
            usage = metadata.get("token_usage", {})

            # Anthropic 格式: usage
            if not usage:
                usage = metadata.get("usage", {})

            if usage:
                # OpenAI: prompt_tokens, completion_tokens
                # Anthropic: input_tokens, output_tokens
                prompt = usage.get("prompt_tokens") or usage.get("input_tokens", 0)
                completion = usage.get("completion_tokens") or usage.get("output_tokens", 0)
                total = usage.get("total_tokens", prompt + completion)

                self.prompt_tokens += prompt
                self.completion_tokens += completion
                self.total_tokens += total
                break

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "call_count": self.call_count,
        }

    def reset(self) -> None:
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.call_count = 0
