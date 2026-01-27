"""Command Hooks Plugin System.

Reuses the hook system from middleware/shell/hooks.
"""

from middleware.shell.hooks.base import BashHook as CommandHook
from middleware.shell.hooks.base import HookResult
from middleware.shell.hooks.loader import load_hooks

__all__ = ["CommandHook", "HookResult", "load_hooks"]
