"""
Web Middleware - 模仿 Cascade 的 Web 搜索和内容获取

提供以下工具（纯 Middleware 实现）：
- web_search: 网页搜索（Tavily → Exa → Firecrawl 降级）
- read_url_content: 获取网页内容（Jina → Markdownify 降级）
- view_web_content: 查看指定 chunk 的内容

特点：
- 分块设计（与 read_file 一致）
- 多提供商降级策略
- PascalCase 参数命名
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage

from middleware.web.fetchers.jina import JinaFetcher
from middleware.web.fetchers.markdownify import MarkdownifyFetcher
from middleware.web.searchers.exa import ExaSearcher
from middleware.web.searchers.firecrawl import FirecrawlSearcher
from middleware.web.searchers.tavily import TavilySearcher
from middleware.web.types import FetchLimits, FetchResult, SearchResult


class WebMiddleware(AgentMiddleware):
    """
    Web Middleware - 纯 Middleware 实现 Web 搜索和内容获取

    特点：
    - 所有工具都在 middleware 层实现
    - 分块设计，支持大内容分段读取
    - 多提供商降级策略
    """

    TOOL_WEB_SEARCH = "web_search"
    TOOL_READ_URL = "read_url_content"
    TOOL_VIEW_CHUNK = "view_web_content"

    def __init__(
        self,
        *,
        tavily_api_key: str | None = None,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
        jina_api_key: str | None = None,
        fetch_limits: FetchLimits | None = None,
        max_search_results: int = 5,
        timeout: int = 15,
        enabled_tools: dict[str, bool] | None = None,
    ):
        """
        初始化 Web middleware

        Args:
            tavily_api_key: Tavily API key（搜索主力）
            exa_api_key: Exa API key（搜索备选）
            firecrawl_api_key: Firecrawl API key（搜索兜底）
            jina_api_key: Jina API key（Fetch 主力）
            fetch_limits: Fetch 限制配置
            max_search_results: 最大搜索结果数
            timeout: 请求超时时间
        """
        self.fetch_limits = fetch_limits or FetchLimits()
        self.max_search_results = max_search_results
        self.timeout = timeout
        self.enabled_tools = enabled_tools or {
            'web_search': True, 'read_url_content': True, 'view_web_content': True
        }

        self._searchers: list[tuple[str, Any]] = []
        if tavily_api_key:
            self._searchers.append(("Tavily", TavilySearcher(tavily_api_key, max_search_results, timeout)))
        if exa_api_key:
            self._searchers.append(("Exa", ExaSearcher(exa_api_key, max_search_results, timeout)))
        if firecrawl_api_key:
            self._searchers.append(("Firecrawl", FirecrawlSearcher(firecrawl_api_key, max_search_results, timeout)))

        self._fetchers: list[tuple[str, Any]] = []
        if jina_api_key:
            self._fetchers.append(("Jina", JinaFetcher(jina_api_key, self.fetch_limits, timeout)))
        self._fetchers.append(("Markdownify", MarkdownifyFetcher(self.fetch_limits, timeout)))

        self._content_cache: dict[str, FetchResult] = {}

        print(f"[WebMiddleware] Initialized")
        print(f"[WebMiddleware] Searchers: {[name for name, _ in self._searchers]}")
        print(f"[WebMiddleware] Fetchers: {[name for name, _ in self._fetchers]}")

    async def _web_search_impl(
        self,
        Query: str,
        MaxResults: int | None = None,
        IncludeDomains: list[str] | None = None,
        ExcludeDomains: list[str] | None = None,
    ) -> SearchResult:
        """
        实现 web_search（多提供商降级）

        优先级：Tavily → Exa → Firecrawl
        """
        if not self._searchers:
            return SearchResult(query=Query, error="No search providers configured")

        max_results = MaxResults or self.max_search_results

        for name, searcher in self._searchers:
            try:
                result = await searcher.search(
                    query=Query,
                    max_results=max_results,
                    include_domains=IncludeDomains,
                    exclude_domains=ExcludeDomains,
                )
                if not result.error:
                    return result
                print(f"[WebMiddleware] {name} failed: {result.error}")
            except Exception as e:
                print(f"[WebMiddleware] {name} exception: {e}")

        return SearchResult(query=Query, error="All search providers failed")

    async def _read_url_impl(self, Url: str) -> FetchResult:
        """
        实现 read_url_content（多提供商降级）

        优先级：Jina → Markdownify
        """
        if not self._fetchers:
            return FetchResult(url=Url, error="No fetch providers configured")

        for name, fetcher in self._fetchers:
            try:
                result = await fetcher.fetch(Url)
                if not result.error:
                    self._content_cache[Url] = result
                    return result
                print(f"[WebMiddleware] {name} failed: {result.error}")
            except Exception as e:
                print(f"[WebMiddleware] {name} exception: {e}")

        return FetchResult(url=Url, error="All fetch providers failed")

    def _view_chunk_impl(self, Url: str, position: int) -> str:
        """
        实现 view_web_content（查看指定 chunk）
        """
        if Url not in self._content_cache:
            return f"URL not in cache. Use read_url_content first: {Url}"

        result = self._content_cache[Url]
        chunk_content = result.get_chunk(position)

        if chunk_content is None:
            return f"Chunk position {position} not found. Available: 0-{result.total_chunks - 1}"

        return f"URL: {Url}\nPosition: {position}/{result.total_chunks - 1}\n\n{chunk_content}"

    def _get_tool_definitions(self) -> list[dict]:
        """获取工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_WEB_SEARCH,
                    "description": "Search the web for current information. Returns titles, URLs, and snippets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Query": {
                                "type": "string",
                                "description": "Search query",
                            },
                            "MaxResults": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 5)",
                            },
                            "IncludeDomains": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Only include results from these domains",
                            },
                            "ExcludeDomains": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Exclude results from these domains",
                            },
                        },
                        "required": ["Query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_READ_URL,
                    "description": "Fetch and read content from a URL. Returns chunked content for large pages.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Url": {
                                "type": "string",
                                "description": "URL to fetch content from",
                            },
                        },
                        "required": ["Url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_VIEW_CHUNK,
                    "description": "View a specific chunk of previously fetched URL content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Url": {
                                "type": "string",
                                "description": "URL that was previously fetched",
                            },
                            "position": {
                                "type": "integer",
                                "description": "Chunk position to view (0-indexed)",
                            },
                        },
                        "required": ["Url", "position"],
                    },
                },
            },
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """注入 Web 工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_definitions())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：注入 Web 工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_definitions())
        return await handler(request.override(tools=tools))

    async def _handle_tool_call(self, tool_name: str, args: dict, tool_call_id: str) -> ToolMessage | None:
        """处理工具调用（异步）"""
        if tool_name == self.TOOL_WEB_SEARCH:
            result = await self._web_search_impl(
                Query=args.get("Query", ""),
                MaxResults=args.get("MaxResults"),
                IncludeDomains=args.get("IncludeDomains"),
                ExcludeDomains=args.get("ExcludeDomains"),
            )
            return ToolMessage(content=result.format_output(), tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_READ_URL:
            result = await self._read_url_impl(Url=args.get("Url", ""))
            return ToolMessage(content=result.format_output(), tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_VIEW_CHUNK:
            content = self._view_chunk_impl(
                Url=args.get("Url", ""),
                position=args.get("position", 0),
            )
            return ToolMessage(content=content, tool_call_id=tool_call_id)

        return None

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """异步：拦截并处理 Web 工具调用"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id", "")

        result = await self._handle_tool_call(tool_name, args, tool_call_id)
        if result is not None:
            return result

        return await handler(request)


__all__ = ["WebMiddleware"]
