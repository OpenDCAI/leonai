# Backward compat - deprecated, use core.runtime.middleware.prompt_caching instead
from core.runtime.middleware.prompt_caching import PromptCachingMiddleware  # noqa: F401

__all__ = ["PromptCachingMiddleware"]
