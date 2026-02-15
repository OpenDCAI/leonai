"""Command Hooks Plugin System."""

from middleware.command.hooks.base import BashHook as CommandHook
from middleware.command.hooks.base import HookResult
from middleware.command.hooks.loader import load_hooks

__all__ = ["CommandHook", "HookResult", "load_hooks"]
