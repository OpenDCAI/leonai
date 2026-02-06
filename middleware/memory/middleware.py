"""MemoryMiddleware — Context pruning + compaction.

Combines SessionPruner (Layer 1) and ContextCompactor (Layer 2).
All operations happen in awrap_model_call — modifies the request sent to LLM,
does NOT modify LangGraph state. TUI sees full history, agent sees compressed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage

from .compactor import ContextCompactor
from .pruner import SessionPruner


class MemoryMiddleware(AgentMiddleware):
    """Context memory management middleware.

    Layer 1 (Pruning): trim/clear old ToolMessage content
    Layer 2 (Compaction): LLM summarization when context exceeds threshold
    """

    tools = []  # no tools injected

    def __init__(
        self,
        context_limit: int = 100000,
        pruning_config: Any = None,
        compaction_config: Any = None,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self._context_limit = context_limit

        # Layer 1: Pruner
        if pruning_config:
            self.pruner = SessionPruner(
                soft_trim_chars=pruning_config.soft_trim_chars,
                hard_clear_threshold=pruning_config.hard_clear_threshold,
                protect_recent=pruning_config.protect_recent,
            )
        else:
            self.pruner = SessionPruner()

        # Layer 2: Compactor
        if compaction_config:
            self.compactor = ContextCompactor(
                reserve_tokens=compaction_config.reserve_tokens,
                keep_recent_tokens=compaction_config.keep_recent_tokens,
            )
        else:
            self.compactor = ContextCompactor()

        # Injected references (set by agent.py after construction)
        self._model: Any = None
        self._runtime: Any = None

        # Compaction cache
        self._cached_summary: str | None = None
        self._compact_up_to_index: int = 0

        if verbose:
            print("[MemoryMiddleware] Initialized")

    def set_model(self, model: Any) -> None:
        """Inject LLM model reference (called by agent.py)."""
        self._model = model

    def set_runtime(self, runtime: Any) -> None:
        """Inject AgentRuntime reference (called by agent.py)."""
        self._runtime = runtime

    # ========== AgentMiddleware interface ==========

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        messages = list(request.messages)
        original_count = len(messages)

        # Account for system_message in token budget
        sys_tokens = self._estimate_system_tokens(request)

        # Layer 1: Prune old ToolMessage content
        pre_prune_tokens = self._estimate_tokens(messages) + sys_tokens
        messages = self.pruner.prune(messages)
        post_prune_tokens = self._estimate_tokens(messages) + sys_tokens

        if self.verbose:
            pruned_saved = pre_prune_tokens - post_prune_tokens
            if pruned_saved > 0:
                print(f"[Memory] Pruned: {pre_prune_tokens} → {post_prune_tokens} tokens (saved ~{pruned_saved})")
            for i, (orig, pruned) in enumerate(zip(request.messages, messages)):
                if orig is not pruned and orig.__class__.__name__ == "ToolMessage":
                    orig_len = len(getattr(orig, "content", ""))
                    new_len = len(getattr(pruned, "content", ""))
                    action = "hard-clear" if "[Tool output cleared" in pruned.content else "soft-trim"
                    print(f"[Memory]   msg[{i}] ToolMessage: {orig_len} → {new_len} chars ({action})")

        # Layer 2: Compaction
        estimated = self._estimate_tokens(messages) + sys_tokens
        threshold = self._context_limit - self.compactor.reserve_tokens
        if self.verbose:
            print(
                f"[Memory] Context: ~{estimated} tokens "
                f"(sys={sys_tokens}, msgs={estimated - sys_tokens}), "
                f"limit={self._context_limit}, threshold={threshold}, "
                f"compact={'YES' if estimated > threshold else 'no'}"
            )

        if self.compactor.should_compact(estimated, self._context_limit) and self._model:
            messages = await self._do_compact(messages)
        elif self._cached_summary and self._compact_up_to_index > 0:
            # Use cached summary for messages already compacted
            if self._compact_up_to_index <= len(messages):
                summary_msg = SystemMessage(content=f"[Conversation Summary]\n{self._cached_summary}")
                messages = [summary_msg] + messages[self._compact_up_to_index :]
                if self.verbose:
                    print(
                        f"[Memory] Using cached summary: "
                        f"{self._compact_up_to_index} old msgs replaced, "
                        f"{len(messages) - 1} msgs sent to LLM"
                    )

        if self.verbose:
            final_tokens = self._estimate_tokens(messages) + sys_tokens
            print(
                f"[Memory] Final: {len(messages)} msgs (~{final_tokens} tokens) "
                f"sent to LLM (original: {original_count} msgs)"
            )

        # Apply modified messages to request
        request.messages = messages
        return await handler(request)

    async def _do_compact(self, messages: list[Any]) -> list[Any]:
        """Execute compaction: summarize old messages, return compacted list."""
        if self._runtime:
            self._runtime.set_flag("isCompacting", True)
        try:
            to_summarize, to_keep = self.compactor.split_messages(messages)
            if len(to_summarize) < 2:
                return messages  # not enough to summarize

            summary_text = await self.compactor.compact(to_summarize, self._model)
            self._cached_summary = summary_text
            self._compact_up_to_index = len(messages) - len(to_keep)

            summary_msg = SystemMessage(content=f"[Conversation Summary]\n{summary_text}")
            if self.verbose:
                print(f"[Memory] Compacted: {len(to_summarize)} msgs → summary + {len(to_keep)} recent")
            return [summary_msg] + to_keep
        finally:
            if self._runtime:
                self._runtime.set_flag("isCompacting", False)

    async def force_compact(self, messages: list[Any]) -> dict[str, Any] | None:
        """Manual compaction trigger (/compact command). Ignores threshold."""
        if not self._model:
            return None

        pruned = self.pruner.prune(messages)
        to_summarize, to_keep = self.compactor.split_messages(pruned)
        if len(to_summarize) < 2:
            return None

        if self._runtime:
            self._runtime.set_flag("isCompacting", True)
        try:
            summary_text = await self.compactor.compact(to_summarize, self._model)
            self._cached_summary = summary_text
            self._compact_up_to_index = len(messages) - len(to_keep)
        finally:
            if self._runtime:
                self._runtime.set_flag("isCompacting", False)

        return {
            "stats": {
                "summarized": len(to_summarize),
                "kept": len(to_keep),
            }
        }

    def _estimate_tokens(self, messages: list[Any]) -> int:
        """Estimate total tokens for messages (chars // 2)."""
        total = 0
        for msg in messages:
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total += len(block.get("text", ""))
                    elif isinstance(block, str):
                        total += len(block)
        return total // 2

    def _estimate_system_tokens(self, request: Any) -> int:
        """Estimate tokens for system_message (not in messages list)."""
        sys_msg = getattr(request, "system_message", None)
        if sys_msg is None:
            return 0
        content = getattr(sys_msg, "content", "")
        if isinstance(content, str):
            return len(content) // 2
        return 0
