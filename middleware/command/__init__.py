"""Command execution middleware with extensible hook system.

Replaces LangChain ShellToolMiddleware with a custom implementation
that matches Cascade's run_command capabilities.
"""

from .hooks import CommandHook, HookResult, load_hooks
from .middleware import CommandMiddleware

__all__ = ["CommandMiddleware", "CommandHook", "HookResult", "load_hooks"]
