"""Searchers subpackage - handles web search with multiple providers."""

from middleware.web.searchers.base import BaseSearcher
from middleware.web.searchers.exa import ExaSearcher
from middleware.web.searchers.firecrawl import FirecrawlSearcher
from middleware.web.searchers.tavily import TavilySearcher

__all__ = ["BaseSearcher", "ExaSearcher", "FirecrawlSearcher", "TavilySearcher"]
