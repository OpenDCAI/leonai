"""
Bash Hooks Plugin System

这个模块提供了一个基于插件的 bash 命令扩展系统。
添加新功能只需要在 bash_hooks 目录下创建新的 Python 文件。
"""

from .base import BashHook, HookResult
from .loader import load_hooks

__all__ = ["BashHook", "HookResult", "load_hooks"]
