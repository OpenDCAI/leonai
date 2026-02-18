"""Fetchers subpackage - handles URL content fetching with multiple strategies."""

from core.web.fetchers.base import BaseFetcher
from core.web.fetchers.jina import JinaFetcher
from core.web.fetchers.markdownify import MarkdownifyFetcher

__all__ = ["BaseFetcher", "JinaFetcher", "MarkdownifyFetcher"]
