"""Middleware for Leon Agent."""

from middleware.command import CommandMiddleware
from middleware.filesystem import FileSystemMiddleware
from middleware.prompt_caching import PromptCachingMiddleware
from middleware.search import SearchMiddleware
from middleware.task import TaskMiddleware
from middleware.todo import TodoMiddleware
from middleware.web import WebMiddleware

__all__ = [
    "CommandMiddleware",
    "FileSystemMiddleware",
    "PromptCachingMiddleware",
    "SearchMiddleware",
    "TaskMiddleware",
    "TodoMiddleware",
    "WebMiddleware",
]
