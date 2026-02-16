"""Web middleware - handles web search and URL fetching with chunked content."""

from middleware.web.middleware import WebMiddleware
from middleware.web.types import FetchLimits, FetchResult, SearchResult

__all__ = ["FetchLimits", "FetchResult", "SearchResult", "WebMiddleware"]
