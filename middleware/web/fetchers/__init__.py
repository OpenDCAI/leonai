"""Fetchers subpackage - handles URL content fetching with multiple strategies."""

from middleware.web.fetchers.base import BaseFetcher
from middleware.web.fetchers.jina import JinaFetcher
from middleware.web.fetchers.markdownify import MarkdownifyFetcher

__all__ = ["BaseFetcher", "JinaFetcher", "MarkdownifyFetcher"]
