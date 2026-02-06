"""
Leon - AI Coding Agent with Middleware Architecture

Middleware-based tool implementation:
- FileSystemMiddleware: read_file, write_file, edit_file, multi_edit, list_dir
- SearchMiddleware: grep_search, find_by_name
- CommandMiddleware: run_command (with hooks)
- PromptCachingMiddleware: cost optimization

All paths must be absolute. Full security mechanisms and audit logging.
"""

import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
import sqlite3

import aiosqlite
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

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
from middleware.queue import SteeringMiddleware
from middleware.search import SearchMiddleware
from middleware.skills import SkillsMiddleware
from middleware.task import TaskMiddleware
from middleware.todo import TodoMiddleware

# 导入 hooks
from middleware.shell.hooks.dangerous_commands import DangerousCommandsHook
from middleware.shell.hooks.file_access_logger import FileAccessLoggerHook
from middleware.shell.hooks.file_permission import FilePermissionHook
from middleware.shell.hooks.path_security import PathSecurityHook
from middleware.web import WebMiddleware
from middleware.monitor import MonitorMiddleware, AgentState

# Import file operation recorder for time travel
from tui.operations import get_recorder


class LeonAgent:
    """
    Leon Agent - AI Coding Assistant

    Features:
    - Pure Middleware architecture
    - Absolute path enforcement
    - Full security (permission control, command interception, audit logging)

    Tools:
    1. File operations: read_file, write_file, edit_file, multi_edit, list_dir
    2. Search: grep_search, find_by_name
    3. Command execution: run_command (via CommandMiddleware)
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        workspace_root: str | Path | None = None,
        *,
        profile: AgentProfile | str | Path | None = None,
        allowed_file_extensions: list[str] | None = None,
        block_dangerous_commands: bool | None = None,
        block_network_commands: bool | None = None,
        enable_audit_log: bool | None = None,
        enable_web_tools: bool | None = None,
        tavily_api_key: str | None = None,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
        jina_api_key: str | None = None,
        sandbox_context_path: str | None = None,
        sandbox_provider: str | None = None,
        sandbox_docker_image: str | None = None,
        verbose: bool = False,
    ):
        """
        Initialize Leon Agent

        Args:
            model_name: Anthropic 模型名称
            api_key: API key (默认从环境变量读取)
            workspace_root: 工作目录（所有操作限制在此目录内）
            profile: Agent Profile (配置文件路径或对象)
            allowed_file_extensions: 允许的文件扩展名（None 表示全部允许）
            block_dangerous_commands: 是否拦截危险命令
            block_network_commands: 是否拦截网络命令
            enable_audit_log: 是否启用审计日志
            enable_web_tools: 是否启用 Web 搜索和内容获取工具
            tavily_api_key: Tavily API key（Web 搜索）
            exa_api_key: Exa API key（Web 搜索）
            firecrawl_api_key: Firecrawl API key（Web 搜索）
            jina_api_key: Jina API key（URL 内容获取）
            sandbox_context_path: Sandbox context mount path（覆盖 profile）
            sandbox_provider: Sandbox provider（覆盖 profile）
            sandbox_docker_image: Docker image（覆盖 profile）
            verbose: 是否输出详细日志（默认 True）
        """
        self.verbose = verbose

        # 加载 profile
        if isinstance(profile, (str, Path)):
            profile = AgentProfile.from_file(profile)
            if self.verbose:
                print(f"[LeonAgent] Profile: {profile} (from CLI argument)")
        elif profile is None:
            # 默认 profile 路径：~/.leon/profile.yaml
            default_profile = Path.home() / ".leon" / "profile.yaml"
            if default_profile.exists():
                profile = AgentProfile.from_file(default_profile)
                if self.verbose:
                    print(f"[LeonAgent] Profile: {default_profile}")
            else:
                # 首次运行，创建默认配置文件
                profile = self._create_default_profile(default_profile)
                if self.verbose:
                    print(f"[LeonAgent] Profile: {default_profile} (created)")

        # CLI 参数覆盖 profile
        if model_name is not None:
            profile.agent.model = model_name
        if workspace_root is not None:
            profile.agent.workspace_root = str(workspace_root)
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
        if sandbox_context_path is not None:
            profile.sandbox.agentbay.context_path = sandbox_context_path
        if sandbox_provider is not None:
            profile.sandbox.provider = sandbox_provider
        if sandbox_docker_image is not None:
            profile.sandbox.docker.image = sandbox_docker_image

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
        self.allowed_file_extensions = profile.agent.allowed_extensions
        self.block_dangerous_commands = profile.agent.block_dangerous_commands
        self.block_network_commands = profile.agent.block_network_commands
        self.enable_audit_log = profile.agent.enable_audit_log
        self.enable_web_tools = profile.tool.web.enabled
        self.queue_mode = profile.agent.queue_mode
        self._session_pool: dict[str, Any] = {}
        self.db_path = Path.home() / ".leon" / "leon.db"

        # 初始化模型
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            # 有 OPENAI_BASE_URL 时，强制使用 ChatOpenAI（OpenAI 兼容代理）
            from langchain_openai import ChatOpenAI
            self.model = ChatOpenAI(
                model=self.model_name,
                api_key=self.api_key,
                base_url=base_url,
            )
        else:
            # 无代理时，让 init_chat_model 根据模型名自动选择
            self.model = init_chat_model(self.model_name, api_key=self.api_key)

        # 构建 middleware 栈
        middleware = self._build_middleware_stack()

        # 加载 MCP 工具
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mcp_tools = loop.run_until_complete(self._init_mcp_tools())
            # 初始化异步 checkpointer
            self._aiosqlite_conn = loop.run_until_complete(self._init_checkpointer())
        finally:
            loop.close()

        # Set parent middleware and checkpointer for TaskMiddleware
        if hasattr(self, '_task_middleware'):
            self._task_middleware.set_parent_middleware(middleware)
            self._task_middleware.set_checkpointer(self.checkpointer)

        # Check if any middleware has self.tools (BaseTool instances).
        # langchain's create_agent creates ToolNode only when:
        #   available_tools = middleware_tools + regular_tools is non-empty
        # where middleware_tools = [t for m in middleware for t in getattr(m, "tools", [])]
        #
        # Most Leon middleware inject tools via wrap_model_call (dict schema),
        # only CommandMiddleware has self.tools (BaseTool instances).
        # If command is disabled and no MCP tools, we need a placeholder.
        middleware_has_tools = any(getattr(m, "tools", None) for m in middleware)
        if not mcp_tools and not middleware_has_tools:
            @tool
            def _placeholder() -> str:
                """Internal placeholder - ensures ToolNode is created for middleware tools."""
                return ""
            mcp_tools = [_placeholder]

        # System prompt
        # 内置 prompt 始终存在，用户配置的追加在后面
        self.system_prompt = self._build_system_prompt()
        if profile.system_prompt:
            self.system_prompt += f"\n\n**Custom Instructions:**\n{profile.system_prompt}"

        self.agent = create_agent(
            model=self.model,
            tools=mcp_tools,
            system_prompt=self.system_prompt,
            middleware=middleware,
            checkpointer=self.checkpointer,
        )

        # 从 MonitorMiddleware 获取 runtime
        self.runtime = self._monitor_middleware.runtime

        if self.verbose:
            print("[LeonAgent] Initialized successfully")
            print(f"[LeonAgent] Workspace: {self.workspace_root}")
            print(f"[LeonAgent] Audit log: {self.enable_audit_log}")

        # 初始化完成，转移到 READY 状态
        self._monitor_middleware.mark_ready()

    def close(self):
        """Clean up resources"""
        # Pause sandbox sessions on exit
        if hasattr(self, '_sandbox_manager') and self._sandbox_manager:
            try:
                on_exit = self.profile.sandbox.on_exit
                if on_exit == "pause":
                    count = self._sandbox_manager.pause_all_sessions()
                    if count > 0:
                        print(f"[LeonAgent] Paused {count} sandbox session(s)")
                elif on_exit == "destroy":
                    for session in self._sandbox_manager.list_sessions():
                        self._sandbox_manager.destroy_session(session["thread_id"])
                    print("[LeonAgent] Destroyed all sandbox sessions")
            except Exception as e:
                print(f"[LeonAgent] Sandbox cleanup error: {e}")

        # Close SQLite connection
        import asyncio

        # 状态转移：→ TERMINATED
        if hasattr(self, '_monitor_middleware'):
            self._monitor_middleware.mark_terminated()

        # Close MCP client (kills subprocess)
        if hasattr(self, '_mcp_client') and self._mcp_client:
            try:
                # Try graceful close first
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._mcp_client.close())
                finally:
                    loop.close()
            except Exception:
                pass
            self._mcp_client = None

        # Close sqlite connection
        if hasattr(self, '_aiosqlite_conn') and self._aiosqlite_conn:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._aiosqlite_conn.close())
                finally:
                    loop.close()
            except Exception:
                pass
            self._aiosqlite_conn = None

    def __del__(self):
        self.close()

    def _create_default_profile(self, path: Path) -> AgentProfile:
        """首次运行时创建默认配置文件"""
        path.parent.mkdir(parents=True, exist_ok=True)

        default_content = """\
# Leon AI Profile
# 配置文档: https://github.com/Ju-Yi-AI-Lab/leonai

agent:
  model: claude-sonnet-4-5-20250929
  enable_audit_log: true
  block_dangerous_commands: true
  # Queue mode: Agent 运行时输入消息的处理方式
  # - steer: 注入当前运行，改变执行方向（默认）
  # - followup: 等当前运行结束后处理
  # - collect: 收集多条消息，合并后处理
  # - steer_backlog: 注入 + 保留为 followup
  # - interrupt: 中断当前运行
  queue_mode: steer

tool:
  filesystem:
    enabled: true
  search:
    enabled: true
  web:
    enabled: true
  command:
    enabled: true

# MCP 服务器配置
# mcp:
#   enabled: true
#   servers:
#     example:
#       command: npx
#       args: ["-y", "@anthropic/mcp-server-example"]

# Skills 配置
# skills:
#   enabled: true
#   paths:
#     - ~/.leon/skills
"""
        path.write_text(default_content)
        return AgentProfile.from_file(path)

    def _build_middleware_stack(self) -> list:
        """构建 middleware 栈"""
        middleware = []
        sandbox_enabled = self.profile.sandbox.enabled
        if sandbox_enabled and self.profile.sandbox.provider == "agentbay":
            api_key = (
                self.profile.sandbox.agentbay.api_key
                or os.getenv("AGENTBAY_API_KEY")
            )
            if not api_key:
                print("[LeonAgent] Warning: Sandbox enabled but AGENTBAY_API_KEY not set")
                sandbox_enabled = False

        # 0. Steering (highest priority - checks for steer messages before model calls)
        middleware.append(SteeringMiddleware())

        # 1. Prompt Caching（架构级，固定启用）
        middleware.append(PromptCachingMiddleware(ttl="5m", min_messages_to_cache=0))

        # 2. FileSystem
        # @@@ Skip if sandbox is enabled (sandbox always replaces local tools)
        if self.profile.tool.filesystem.enabled and not sandbox_enabled:
            file_hooks = []
            if self.enable_audit_log:
                file_hooks.append(FileAccessLoggerHook(workspace_root=self.workspace_root, log_file="file_access.log"))
            file_hooks.append(FilePermissionHook(
                workspace_root=self.workspace_root,
                allowed_extensions=self.allowed_file_extensions,
            ))
            fs_tools = {
                'read_file': self.profile.tool.filesystem.tools.read_file.enabled,
                'write_file': self.profile.tool.filesystem.tools.write_file,
                'edit_file': self.profile.tool.filesystem.tools.edit_file,
                'multi_edit': self.profile.tool.filesystem.tools.multi_edit,
                'list_dir': self.profile.tool.filesystem.tools.list_dir,
            }
            middleware.append(FileSystemMiddleware(
                workspace_root=self.workspace_root,
                max_file_size=self.profile.tool.filesystem.tools.read_file.max_file_size,
                allowed_extensions=self.allowed_file_extensions,
                hooks=file_hooks,
                enabled_tools=fs_tools,
                operation_recorder=get_recorder(),
                verbose=self.verbose,
            ))

        # 3. Search
        if self.profile.tool.search.enabled:
            search_tools = {
                'grep_search': self.profile.tool.search.tools.grep_search.enabled,
                'find_by_name': self.profile.tool.search.tools.find_by_name,
            }
            middleware.append(SearchMiddleware(
                workspace_root=self.workspace_root,
                max_results=self.profile.tool.search.max_results,
                max_file_size=self.profile.tool.search.tools.grep_search.max_file_size,
                prefer_system_tools=True,
                enabled_tools=search_tools,
                verbose=self.verbose,
            ))

        # 4. Web
        if self.profile.tool.web.enabled:
            web_tools = {
                'web_search': self.profile.tool.web.tools.web_search.enabled,
                'read_url_content': self.profile.tool.web.tools.read_url_content.enabled,
                'view_web_content': self.profile.tool.web.tools.view_web_content,
            }
            middleware.append(WebMiddleware(
                tavily_api_key=self.profile.tool.web.tools.web_search.tavily_api_key or os.getenv("TAVILY_API_KEY"),
                exa_api_key=self.profile.tool.web.tools.web_search.exa_api_key or os.getenv("EXA_API_KEY"),
                firecrawl_api_key=self.profile.tool.web.tools.web_search.firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY"),
                jina_api_key=self.profile.tool.web.tools.read_url_content.jina_api_key or os.getenv("JINA_AI_API_KEY"),
                max_search_results=self.profile.tool.web.tools.web_search.max_results,
                timeout=self.profile.tool.web.timeout,
                enabled_tools=web_tools,
                verbose=self.verbose,
            ))

        # 5. Command
        # @@@ Skip if sandbox is enabled (sandbox always replaces local tools)
        if self.profile.tool.command.enabled and not sandbox_enabled:
            command_hooks = []
            if self.block_dangerous_commands:
                command_hooks.append(DangerousCommandsHook(
                    workspace_root=self.workspace_root,
                    block_network=self.block_network_commands,
                    verbose=self.verbose,
                ))
            command_hooks.append(PathSecurityHook(workspace_root=self.workspace_root))
            command_tools = {
                'run_command': self.profile.tool.command.tools.run_command.enabled,
                'command_status': self.profile.tool.command.tools.command_status,
            }
            middleware.append(CommandMiddleware(
                workspace_root=self.workspace_root,
                default_timeout=self.profile.tool.command.tools.run_command.default_timeout,
                hooks=command_hooks,
                enabled_tools=command_tools,
                verbose=self.verbose,
            ))

        # 6. Skills
        if self.profile.skills.enabled and self.profile.skills.paths:
            middleware.append(SkillsMiddleware(
                skill_paths=self.profile.skills.paths,
                enabled_skills=self.profile.skills.skills,
                verbose=self.verbose,
            ))

        # 7. Todo (task management and progress tracking)
        self._todo_middleware = TodoMiddleware(verbose=self.verbose)
        middleware.append(self._todo_middleware)

        # 8. Subagent (sub-agent orchestration)
        # TaskMiddleware needs parent middleware for tool inheritance
        # We'll set it after building the stack
        self._task_middleware = TaskMiddleware(
            workspace_root=self.workspace_root,
            parent_model=self.model_name,
            api_key=self.api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            verbose=self.verbose,
        )
        middleware.append(self._task_middleware)

        # 9. Sandbox (isolated execution environment)
        # @@@ Sandbox replaces local tools when enabled - must be last to override
        self._sandbox_manager = None
        if sandbox_enabled:
            from middleware.sandbox import SandboxManager, SandboxMiddleware
            from middleware.sandbox.providers.agentbay import AgentBayProvider

            # Initialize provider based on config
            if self.profile.sandbox.provider == "agentbay":
                provider = AgentBayProvider(
                    api_key=api_key,
                    region_id=self.profile.sandbox.agentbay.region_id,
                    default_context_path=self.profile.sandbox.agentbay.context_path,
                    image_id=self.profile.sandbox.agentbay.image_id,
                )
            elif self.profile.sandbox.provider == "docker":
                from middleware.sandbox.providers.docker import DockerProvider

                provider = DockerProvider(
                    image=self.profile.sandbox.docker.image,
                    mount_path=self.profile.sandbox.docker.mount_path,
                )
            else:
                provider = None

            if provider:
                self._sandbox_manager = SandboxManager(
                    provider=provider,
                    db_path=self.db_path,
                    default_context_id=self.profile.sandbox.context_id,
                )
                sandbox_tools = {
                    'read_file': self.profile.sandbox.tools.read_file,
                    'write_file': self.profile.sandbox.tools.write_file,
                    'edit_file': self.profile.sandbox.tools.edit_file,
                    'list_dir': self.profile.sandbox.tools.list_dir,
                    'run_command': self.profile.sandbox.tools.run_command,
                    'sandbox_upload': self.profile.sandbox.tools.sandbox_upload,
                    'sandbox_download': self.profile.sandbox.tools.sandbox_download,
                }
                middleware.append(SandboxMiddleware(
                    manager=self._sandbox_manager,
                    workspace_root=self.workspace_root,
                    enabled_tools=sandbox_tools,
                ))
                print(f"[LeonAgent] Sandbox enabled: {self.profile.sandbox.provider}")

        # 10. Monitor (状态监控，放在最后以捕获所有请求/响应)
        self._monitor_middleware = MonitorMiddleware(
            context_limit=100000,
            verbose=self.verbose,
        )
        middleware.append(self._monitor_middleware)

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
            self._mcp_client = client  # Save reference for cleanup
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

            if self.verbose:
                print(f"[LeonAgent] Loaded {len(tools)} MCP tools from {len(configs)} servers")
            return tools
        except Exception as e:
            if self.verbose:
                print(f"[LeonAgent] MCP initialization failed: {e}")
            return []

    async def _init_checkpointer(self):
        """Initialize async checkpointer for conversation persistence"""
        db_path = Path.home() / ".leon" / "leon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(db_path))
        self.checkpointer = AsyncSqliteSaver(conn)
        await self.checkpointer.setup()
        return conn

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

        # @@@ Different prompt for sandbox vs local mode
        if self.profile.sandbox.enabled:
            provider = self.profile.sandbox.provider
            if provider == "docker":
                env_label = "Local Docker sandbox (Ubuntu)"
                mode_label = "Sandbox (isolated local container)"
                working_dir = self.profile.sandbox.docker.mount_path
                location_rule = "All file and command operations run in a local Docker container, NOT on the user's host filesystem."
            else:
                env_label = "Remote Linux sandbox (Ubuntu)"
                mode_label = "Sandbox (isolated cloud environment)"
                working_dir = self.profile.sandbox.agentbay.context_path
                location_rule = "All file and command operations run in a remote sandbox, NOT on the user's local machine."

            prompt = f"""You are a highly capable AI assistant with access to a sandbox environment.

**Context:**
- Environment: {env_label}
- Working Directory: {working_dir}
- Mode: {mode_label}

**Important Rules:**

1. **Sandbox Environment**: {location_rule} The sandbox is an isolated Linux environment.

2. **Absolute Paths**: All file paths must be absolute paths.
   - ✅ Correct: `{working_dir}/project/test.py` or `/tmp/output.txt`
   - ❌ Wrong: `test.py` or `./test.py`

3. **Available Tools**: You have tools for file operations (read_file, write_file, edit_file, list_dir), command execution (run_command), and file transfer (sandbox_upload, sandbox_download).

4. **File Transfer**: Use sandbox_upload to copy files from user's local machine to sandbox, and sandbox_download to copy files from sandbox to local.

5. **Security**: The sandbox is isolated. You can install packages, run any commands, and modify files freely within the sandbox.
"""
        else:
            prompt = f"""You are a highly capable AI assistant with access to file and system tools.

**Context:**
- Workspace: `{self.workspace_root}`
- OS: {os_name}
- Shell: {shell_name}

**Important Rules:**

1. **Use Available Tools**: You have access to tools for file operations, search, web access, and command execution. Always use these tools when the user requests file or system operations.

2. **Absolute Paths**: All file paths must be absolute paths starting from root (/).
   - ✅ Correct: `/home/user/workspace/test.py`
   - ❌ Wrong: `test.py` or `./test.py`

3. **Workspace**: File operations are restricted to: {self.workspace_root}

4. **Security**: Dangerous commands are blocked. All operations are logged.

5. **Tool Priority**: Tools starting with `mcp__` are external MCP integrations. When a built-in tool and an MCP tool have the same functionality, use the built-in tool.
"""

        # Common sections for both modes
        prompt += """
**Task Tool (Sub-agent Orchestration):**

Use the Task tool to launch specialized sub-agents for complex tasks:
- `explore`: Read-only codebase exploration. Use for: finding files, searching code, understanding implementations.
- `plan`: Design implementation plans. Use for: architecture decisions, multi-step planning.
- `bash`: Execute shell commands. Use for: git operations, running tests, system commands.
- `general`: Full tool access. Use for: independent multi-step tasks requiring file modifications.

When to use Task:
- Open-ended searches that may require multiple rounds of exploration
- Tasks that can run independently while you continue other work
- Complex operations that benefit from specialized focus

When NOT to use Task:
- Simple file reads (use read_file directly)
- Specific searches with known patterns (use grep_search directly)
- Quick operations that don't need isolation

**Todo Tools (Task Management):**

Use Todo tools to track progress on complex, multi-step tasks:
- `TaskCreate`: Create a new task with subject, description, and activeForm (present continuous for spinner)
- `TaskList`: View all tasks and their status
- `TaskGet`: Get full details of a specific task
- `TaskUpdate`: Update task status (pending → in_progress → completed) or details

When to use Todo:
- Complex tasks with 3+ distinct steps
- When the user provides multiple tasks to complete
- To show progress on non-trivial work

When NOT to use Todo:
- Single, straightforward tasks
- Trivial operations that don't need tracking
"""

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
        # 状态由 MonitorMiddleware 自动管理
        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": thread_id}},
            )
            return result

        except Exception as e:
            # 标记错误状态
            self._monitor_middleware.mark_error(e)
            raise

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
    sandbox_context_path: str | None = None,
    sandbox_provider: str | None = None,
    sandbox_docker_image: str | None = None,
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
        model_name=model_name,
        api_key=api_key,
        workspace_root=workspace_root,
        sandbox_context_path=sandbox_context_path,
        sandbox_provider=sandbox_provider,
        sandbox_docker_image=sandbox_docker_image,
        **kwargs,
    )



if __name__ == "__main__":
    # 示例用法
    leon_agent = create_leon_agent()

    try:
        print("=== Example 1: File Operations ===")
        response = leon_agent.get_response(
            f"Create a Python file at {leon_agent.workspace_root}/hello.py that prints 'Hello, Leon!'",
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
