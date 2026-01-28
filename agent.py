"""
Leon - 完全模仿 Windsurf Cascade 的 Agent 实现

使用纯 Middleware 架构实现所有工具：
- FileSystemMiddleware: read_file, write_file, edit_file, multi_edit, list_dir
- SearchMiddleware: grep_search, find_by_name
- CommandMiddleware: run_command (with hooks)
- PromptCachingMiddleware: 成本优化

所有路径必须使用绝对路径，完整的安全机制和审计日志。
"""

import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

# Load .env file
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from agent_profile import AgentProfile
from middleware.command import CommandMiddleware
from middleware.filesystem import FileSystemMiddleware
from middleware.prompt_caching import PromptCachingMiddleware
from middleware.search import SearchMiddleware

# 导入 hooks
from middleware.shell.hooks.dangerous_commands import DangerousCommandsHook
from middleware.shell.hooks.file_access_logger import FileAccessLoggerHook
from middleware.shell.hooks.file_permission import FilePermissionHook
from middleware.shell.hooks.path_security import PathSecurityHook
from middleware.web import WebMiddleware


class LeonAgent:
    """
    Leon Agent - 完全模仿 Windsurf Cascade

    特点：
    - 纯 Middleware 架构（无独立 Tool）
    - 强制绝对路径
    - 完整安全机制（权限控制、命令拦截、审计日志）
    - 支持所有 Cascade 核心工具

    工具列表：
    1. 文件操作：read_file, write_file, edit_file, multi_edit, list_dir
    2. 搜索：grep_search, find_by_name
    3. 命令执行：run_command (通过 CommandMiddleware)
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        workspace_root: str | Path | None = None,
        *,
        profile: AgentProfile | str | Path | None = None,
        read_only: bool | None = None,
        allowed_file_extensions: list[str] | None = None,
        block_dangerous_commands: bool | None = None,
        block_network_commands: bool | None = None,
        enable_audit_log: bool | None = None,
        enable_web_tools: bool | None = None,
        tavily_api_key: str | None = None,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
        jina_api_key: str | None = None,
    ):
        """
        初始化 Cascade-Like Agent

        Args:
            model_name: Anthropic 模型名称
            api_key: API key (默认从环境变量读取)
            workspace_root: 工作目录（所有操作限制在此目录内）
            profile: Agent Profile (配置文件路径或对象)
            read_only: 只读模式（禁止写入和编辑）
            allowed_file_extensions: 允许的文件扩展名（None 表示全部允许）
            block_dangerous_commands: 是否拦截危险命令
            block_network_commands: 是否拦截网络命令
            enable_audit_log: 是否启用审计日志
            enable_web_tools: 是否启用 Web 搜索和内容获取工具
            tavily_api_key: Tavily API key（Web 搜索）
            exa_api_key: Exa API key（Web 搜索）
            firecrawl_api_key: Firecrawl API key（Web 搜索）
            jina_api_key: Jina API key（URL 内容获取）
        """
        # 加载 profile
        if isinstance(profile, (str, Path)):
            profile = AgentProfile.from_file(profile)
        elif profile is None:
            profile = AgentProfile.default()

        # CLI 参数覆盖 profile
        if model_name is not None:
            profile.agent.model = model_name
        if workspace_root is not None:
            profile.agent.workspace_root = str(workspace_root)
        if read_only is not None:
            profile.agent.read_only = read_only
            profile.tools.filesystem.read_only = read_only
        if allowed_file_extensions is not None:
            profile.tools.filesystem.allowed_extensions = allowed_file_extensions
        if block_dangerous_commands is not None:
            profile.tools.command.block_dangerous_commands = block_dangerous_commands
        if block_network_commands is not None:
            profile.tools.command.block_network_commands = block_network_commands
        if enable_audit_log is not None:
            profile.agent.enable_audit_log = enable_audit_log
        if enable_web_tools is not None:
            profile.tools.web.enabled = enable_web_tools

        self.profile = profile
        self.model_name = profile.agent.model

        # API key 处理
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be set via:\n"
                "  - OPENAI_API_KEY environment variable (recommended for proxy)\n"
                "  - ANTHROPIC_API_KEY environment variable\n"
                "  - api_key parameter"
            )

        # Workspace 设置
        if profile.agent.workspace_root:
            self.workspace_root = Path(profile.agent.workspace_root).expanduser().resolve()
        else:
            self.workspace_root = Path.cwd()

        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # 配置参数
        self.read_only = profile.agent.read_only
        self.allowed_file_extensions = profile.tools.filesystem.allowed_extensions
        self.block_dangerous_commands = profile.tools.command.block_dangerous_commands
        self.block_network_commands = profile.tools.command.block_network_commands
        self.enable_audit_log = profile.agent.enable_audit_log
        self.enable_web_tools = profile.tools.web.enabled
        self._session_pool: dict[str, Any] = {}

        # 初始化模型
        model_kwargs = {"api_key": self.api_key}
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            model_kwargs["base_url"] = base_url

        self.model = init_chat_model(self.model_name, **model_kwargs)

        # 构建 middleware 栈
        middleware = self._build_middleware_stack()

        # 加载 MCP 工具
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mcp_tools = loop.run_until_complete(self._init_mcp_tools())
        finally:
            loop.close()

        # System prompt
        self.system_prompt = profile.system_prompt or self._build_system_prompt()

        # 创建 agent（带 checkpointer 支持对话历史和 session 状态）
        self.agent = create_agent(
            model=self.model,
            tools=mcp_tools,
            system_prompt=self.system_prompt,
            middleware=middleware,
            checkpointer=MemorySaver(),
        )

        print("[LeonAgent] Initialized successfully")
        print(f"[LeonAgent] Workspace: {self.workspace_root}")
        print(f"[LeonAgent] Read-only: {self.read_only}")
        print(f"[LeonAgent] Audit log: {self.enable_audit_log}")

    def _build_middleware_stack(self) -> list:
        """构建 middleware 栈"""
        middleware = []

        # 1. Prompt Caching
        if self.profile.tools.prompt_caching.enabled:
            middleware.append(PromptCachingMiddleware(
                ttl=self.profile.tools.prompt_caching.ttl,
                min_messages_to_cache=self.profile.tools.prompt_caching.min_messages_to_cache
            ))

        # 2. FileSystem
        if self.profile.tools.filesystem.enabled:
            file_hooks = []
            if self.enable_audit_log:
                file_hooks.append(FileAccessLoggerHook(workspace_root=self.workspace_root, log_file="file_access.log"))
            file_hooks.append(FilePermissionHook(
                workspace_root=self.workspace_root,
                read_only=self.read_only,
                allowed_extensions=self.allowed_file_extensions,
            ))
            fs_tools = {
                'read_file': self.profile.tools.filesystem.read_file,
                'write_file': self.profile.tools.filesystem.write_file,
                'edit_file': self.profile.tools.filesystem.edit_file,
                'multi_edit': self.profile.tools.filesystem.multi_edit,
                'list_dir': self.profile.tools.filesystem.list_dir,
            }
            middleware.append(FileSystemMiddleware(
                workspace_root=self.workspace_root,
                read_only=self.read_only,
                max_file_size=self.profile.tools.filesystem.max_file_size,
                allowed_extensions=self.allowed_file_extensions,
                hooks=file_hooks,
                enabled_tools=fs_tools,
            ))

        # 3. Search
        if self.profile.tools.search.enabled:
            search_tools = {
                'grep_search': self.profile.tools.search.grep_search,
                'find_by_name': self.profile.tools.search.find_by_name,
            }
            middleware.append(SearchMiddleware(
                workspace_root=self.workspace_root,
                max_results=self.profile.tools.search.max_results,
                max_file_size=self.profile.tools.search.max_file_size,
                prefer_system_tools=self.profile.tools.search.prefer_system_tools,
                enabled_tools=search_tools,
            ))

        # 4. Web
        if self.profile.tools.web.enabled:
            web_tools = {
                'web_search': self.profile.tools.web.web_search,
                'read_url_content': self.profile.tools.web.read_url_content,
                'view_web_content': self.profile.tools.web.view_web_content,
            }
            middleware.append(WebMiddleware(
                tavily_api_key=self.profile.tools.web.tavily_api_key or os.getenv("TAVILY_API_KEY"),
                exa_api_key=self.profile.tools.web.exa_api_key or os.getenv("EXA_API_KEY"),
                firecrawl_api_key=self.profile.tools.web.firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY"),
                jina_api_key=self.profile.tools.web.jina_api_key or os.getenv("JINA_AI_API_KEY"),
                max_search_results=self.profile.tools.web.max_search_results,
                timeout=self.profile.tools.web.timeout,
                enabled_tools=web_tools,
            ))

        # 5. Command
        if self.profile.tools.command.enabled:
            command_hooks = []
            if self.block_dangerous_commands:
                command_hooks.append(DangerousCommandsHook(
                    workspace_root=self.workspace_root,
                    block_network=self.block_network_commands,
                ))
            command_hooks.append(PathSecurityHook(workspace_root=self.workspace_root))
            command_tools = {
                'run_command': self.profile.tools.command.run_command,
                'command_status': self.profile.tools.command.command_status,
            }
            middleware.append(CommandMiddleware(
                workspace_root=self.workspace_root,
                default_timeout=self.profile.tools.command.default_timeout,
                hooks=command_hooks,
                enabled_tools=command_tools,
            ))

        return middleware

    async def _init_mcp_tools(self) -> list:
        if not self.profile.mcp.enabled or not self.profile.mcp.servers:
            return []

        from langchain_mcp_adapters.client import MultiServerMCPClient

        configs = {}
        for name, cfg in self.profile.mcp.servers.items():
            if cfg.url:
                config = {"transport": "streamable_http", "url": cfg.url}
            else:
                config = {"transport": "stdio", "command": cfg.command, "args": cfg.args}
            if cfg.env:
                config["env"] = cfg.env
            configs[name] = config

        try:
            client = MultiServerMCPClient(configs, tool_name_prefix=False)
            tools = await client.get_tools()

            # Apply mcp__ prefix to match Claude Code naming convention
            for tool in tools:
                # Extract server name from tool metadata or connection
                server_name = None
                for name in configs.keys():
                    if hasattr(tool, 'metadata') and tool.metadata:
                        server_name = name
                        break
                if server_name:
                    tool.name = f"mcp__{server_name}__{tool.name}"

            if any(cfg.allowed_tools for cfg in self.profile.mcp.servers.values()):
                tools = [t for t in tools if self._is_tool_allowed(t)]

            print(f"[LeonAgent] Loaded {len(tools)} MCP tools from {len(configs)} servers")
            return tools
        except Exception as e:
            print(f"[LeonAgent] MCP initialization failed: {e}")
            return []

    def _is_tool_allowed(self, tool) -> bool:
        # Extract original tool name without mcp__ prefix
        tool_name = tool.name
        if tool_name.startswith('mcp__'):
            parts = tool_name.split('__', 2)
            if len(parts) == 3:
                tool_name = parts[2]

        for cfg in self.profile.mcp.servers.values():
            if cfg.allowed_tools:
                return tool_name in cfg.allowed_tools
        return True

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        import os
        import platform

        os_name = platform.system()
        shell_name = os.environ.get('SHELL', '/bin/bash').split('/')[-1]

        prompt = f"""You are a highly capable AI assistant with access to file and system tools.

**Context:**
- Workspace: `{self.workspace_root}`
- OS: {os_name}
- Shell: {shell_name}
- Read-Only: {'Yes' if self.read_only else 'No'}

**Important Rules:**

1. **Use Available Tools**: You have access to tools for file operations, search, web access, and command execution. Always use these tools when the user requests file or system operations.

2. **Absolute Paths**: All file paths must be absolute paths starting from root (/).
   - ✅ Correct: `/Users/apple/workspace/test.py`
   - ❌ Wrong: `test.py` or `./test.py`

3. **Workspace**: File operations are restricted to: {self.workspace_root}

4. **Security**: Dangerous commands are blocked. All operations are logged.
"""

        if self.read_only:
            prompt += "\n5. **READ-ONLY MODE**: Write and edit operations are disabled.\n"

        if self.allowed_file_extensions:
            prompt += f"\n6. **File Type Restriction**: Only these extensions allowed: {', '.join(self.allowed_file_extensions)}\n"

        return prompt

    def invoke(
        self,
        message: str,
        thread_id: str = "default",
    ) -> dict:
        """
        调用 agent

        Args:
            message: 用户消息
            thread_id: 线程 ID

        Returns:
            Agent 响应（包含消息和状态）
        """
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        return result

    def get_response(self, message: str, thread_id: str = "default", **kwargs) -> str:
        """
        获取 agent 的文本响应

        Args:
            message: 用户消息
            thread_id: 线程 ID
            **kwargs: 额外的状态参数

        Returns:
            Agent 的文本响应
        """
        result = self.invoke(message, thread_id, **kwargs)
        return result["messages"][-1].content

    def cleanup(self):
        """清理临时工作目录"""
        if self.workspace_root.exists() and "tmp" in str(self.workspace_root):
            import shutil

            shutil.rmtree(self.workspace_root, ignore_errors=True)


def create_leon_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
    api_key: str | None = None,
    workspace_root: str | Path | None = None,
    **kwargs,
) -> LeonAgent:
    """
    工厂函数：创建 Leon Agent

    Args:
        model_name: Anthropic 模型名称
        api_key: API key
        workspace_root: 工作目录
        **kwargs: 其他配置参数

    Returns:
        配置好的 LeonAgent 实例

    Examples:
        # 基本用法
        agent = create_leon_agent()

        # 只读模式
        agent = create_leon_agent(read_only=True)

        # 限制文件类型
        agent = create_leon_agent(
            allowed_file_extensions=["py", "txt", "md"]
        )

        # 自定义工作目录
        agent = create_leon_agent(
            workspace_root="/path/to/workspace"
        )
    """
    return LeonAgent(
        model_name=model_name, api_key=api_key, workspace_root=workspace_root, **kwargs
    )


# Export compiled graph for LangGraph CLI (without checkpointer)
def _create_agent_for_langgraph():
    """Create agent without checkpointer for LangGraph CLI"""
    leon = create_leon_agent()
    middleware = leon._build_middleware_stack()

    # Load MCP tools
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        mcp_tools = loop.run_until_complete(leon._init_mcp_tools())
    finally:
        loop.close()

    # Create agent WITHOUT checkpointer
    return create_agent(
        model=leon.model,
        tools=mcp_tools,
        middleware=middleware,
        checkpointer=None,
    )

agent = _create_agent_for_langgraph()


if __name__ == "__main__":
    # 示例用法
    leon_agent = create_leon_agent()

    try:
        print("=== Example 1: File Operations ===")
        response = leon_agent.get_response(
            f"Create a Python file at {leon_agent.workspace_root}/hello.py that prints 'Hello, Cascade!'",
            thread_id="demo",
        )
        print(response)
        print()

        print("=== Example 2: Read File ===")
        response = leon_agent.get_response(
            f"Read the file {leon_agent.workspace_root}/hello.py", thread_id="demo"
        )
        print(response)
        print()

        print("=== Example 3: Search ===")
        response = leon_agent.get_response(
            f"Search for 'Hello' in {leon_agent.workspace_root}", thread_id="demo"
        )
        print(response)

    finally:
        leon_agent.cleanup()
