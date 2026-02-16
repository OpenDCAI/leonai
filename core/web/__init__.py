"""Web middleware - handles web search and URL fetching with chunked content."""

from core.web.middleware import WebMiddleware
from core.web.types import FetchLimits, FetchResult, SearchResult

__all__ = ["FetchLimits", "FetchResult", "SearchResult", "WebMiddleware"]
