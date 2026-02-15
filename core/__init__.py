"""Middleware for Leon Agent."""

from core.command import CommandMiddleware
from core.filesystem import FileSystemMiddleware
from core.prompt_caching import PromptCachingMiddleware
from core.search import SearchMiddleware
from core.task import TaskMiddleware
from core.todo import TodoMiddleware
from core.web import WebMiddleware

__all__ = [
    "CommandMiddleware",
    "FileSystemMiddleware",
    "PromptCachingMiddleware",
    "SearchMiddleware",
    "TaskMiddleware",
    "TodoMiddleware",
    "WebMiddleware",
]
