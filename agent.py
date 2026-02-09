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

import aiosqlite
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
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

# 导入 hooks
from middleware.command.hooks.dangerous_commands import DangerousCommandsHook
from middleware.command.hooks.file_access_logger import FileAccessLoggerHook
from middleware.command.hooks.file_permission import FilePermissionHook
from middleware.command.hooks.path_security import PathSecurityHook
from middleware.filesystem import FileSystemMiddleware
from middleware.memory import MemoryMiddleware
from middleware.monitor import MonitorMiddleware
from middleware.prompt_caching import PromptCachingMiddleware
from middleware.queue import SteeringMiddleware
from middleware.search import SearchMiddleware
from middleware.skills import SkillsMiddleware
from middleware.task import TaskMiddleware
from middleware.todo import TodoMiddleware
from middleware.web import WebMiddleware

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
        sandbox: Any = None,
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
            sandbox: Sandbox instance, name string, or None for local
            verbose: 是否输出详细日志（默认 True）
        """
        self.verbose = verbose

        # Load profile
        self.profile = self._load_profile(profile)

        # Apply CLI parameter overrides
        self._apply_cli_overrides(
            model_name=model_name,
            workspace_root=workspace_root,
            allowed_file_extensions=allowed_file_extensions,
            block_dangerous_commands=block_dangerous_commands,
            block_network_commands=block_network_commands,
            enable_audit_log=enable_audit_log,
            enable_web_tools=enable_web_tools,
        )
        self.model_name = self.profile.agent.model

        # Resolve API key
        self.api_key = api_key or self.profile.agent.api_key or self._resolve_env_api_key()
        if not self.api_key:
            raise ValueError(
                "API key must be set via:\n"
                "  - OPENAI_API_KEY environment variable (recommended for proxy)\n"
                "  - ANTHROPIC_API_KEY environment variable\n"
                "  - api_key parameter\n"
                "  - profile agent.api_key field"
            )

        # Initialize workspace and configuration
        self.workspace_root = self._resolve_workspace_root()
        self._init_config_attributes()
        self._sandbox = self._init_sandbox(sandbox)

        # Override workspace_root for sandbox mode
        if self._sandbox.name != "local":
            self.workspace_root = Path(self._sandbox.working_dir)
        else:
            self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Initialize model
        self.model = self._create_model()

        # Initialize checkpointer and MCP tools
        self._aiosqlite_conn, mcp_tools = self._init_async_components()

        # Build middleware stack
        middleware = self._build_middleware_stack()

        # Configure TaskMiddleware with parent context
        if hasattr(self, "_task_middleware"):
            self._task_middleware.set_parent_middleware(middleware)
            self._task_middleware.set_checkpointer(self.checkpointer)

        # Ensure ToolNode is created (middleware tools need at least one BaseTool)
        if not mcp_tools and not self._has_middleware_tools(middleware):
            mcp_tools = [self._create_placeholder_tool()]

        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        if self.profile.system_prompt:
            self.system_prompt += f"\n\n**Custom Instructions:**\n{self.profile.system_prompt}"

        # Create agent
        self.agent = create_agent(
            model=self.model,
            tools=mcp_tools,
            system_prompt=self.system_prompt,
            middleware=middleware,
            checkpointer=self.checkpointer,
        )

        # Get runtime from MonitorMiddleware
        self.runtime = self._monitor_middleware.runtime

        # Inject runtime/model into MemoryMiddleware
        if hasattr(self, "_memory_middleware"):
            self._memory_middleware.set_runtime(self.runtime)
            self._memory_middleware.set_model(self.model)

        if self.verbose:
            print("[LeonAgent] Initialized successfully")
            print(f"[LeonAgent] Workspace: {self.workspace_root}")
            print(f"[LeonAgent] Audit log: {self.enable_audit_log}")

        # Mark agent as ready
        self._monitor_middleware.mark_ready()

    def _init_async_components(self) -> tuple[Any, list]:
        """Initialize async components (checkpointer and MCP tools)."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            conn = loop.run_until_complete(self._init_checkpointer())
            mcp_tools = loop.run_until_complete(self._init_mcp_tools())
            return conn, mcp_tools
        finally:
            loop.close()

    def _has_middleware_tools(self, middleware: list) -> bool:
        """Check if any middleware has BaseTool instances."""
        return any(getattr(m, "tools", None) for m in middleware)

    def _create_placeholder_tool(self):
        """Create placeholder tool to ensure ToolNode is created."""
        from langchain_core.tools import tool

        @tool
        def _placeholder() -> str:
            """Internal placeholder - ensures ToolNode is created for middleware tools."""
            return ""

        return _placeholder

    def _load_profile(self, profile: AgentProfile | str | Path | None) -> AgentProfile:
        """Load agent profile from file or create default."""
        if isinstance(profile, (str, Path)):
            profile = AgentProfile.from_file(profile)
            if self.verbose:
                print(f"[LeonAgent] Profile: {profile} (from CLI argument)")
            return profile

        if profile is not None:
            return profile

        # Load or create default profile
        default_profile = Path.home() / ".leon" / "profile.yaml"
        if default_profile.exists():
            profile = AgentProfile.from_file(default_profile)
            if self.verbose:
                print(f"[LeonAgent] Profile: {default_profile}")
        else:
            profile = self._create_default_profile(default_profile)
            if self.verbose:
                print(f"[LeonAgent] Profile: {default_profile} (created)")
        return profile

    def _apply_cli_overrides(
        self,
        model_name: str | None,
        workspace_root: str | Path | None,
        allowed_file_extensions: list[str] | None,
        block_dangerous_commands: bool | None,
        block_network_commands: bool | None,
        enable_audit_log: bool | None,
        enable_web_tools: bool | None,
    ) -> None:
        """Apply CLI parameter overrides to profile."""
        if model_name is not None:
            self.profile.agent.model = model_name
        if workspace_root is not None:
            self.profile.agent.workspace_root = str(workspace_root)
        if allowed_file_extensions is not None:
            self.profile.tools.filesystem.allowed_extensions = allowed_file_extensions
        if block_dangerous_commands is not None:
            self.profile.tools.command.block_dangerous_commands = block_dangerous_commands
        if block_network_commands is not None:
            self.profile.tools.command.block_network_commands = block_network_commands
        if enable_audit_log is not None:
            self.profile.agent.enable_audit_log = enable_audit_log
        if enable_web_tools is not None:
            self.profile.tools.web.enabled = enable_web_tools

    def _resolve_workspace_root(self) -> Path:
        """Resolve workspace root from profile or current directory."""
        if self.profile.agent.workspace_root:
            return Path(self.profile.agent.workspace_root).expanduser().resolve()
        return Path.cwd()

    def _init_config_attributes(self) -> None:
        """Initialize configuration attributes from profile."""
        self.allowed_file_extensions = self.profile.agent.allowed_extensions
        self.block_dangerous_commands = self.profile.agent.block_dangerous_commands
        self.block_network_commands = self.profile.agent.block_network_commands
        self.enable_audit_log = self.profile.agent.enable_audit_log
        self.enable_web_tools = self.profile.tool.web.enabled
        self.queue_mode = self.profile.agent.queue_mode
        self._session_pool: dict[str, Any] = {}
        self.db_path = Path.home() / ".leon" / "leon.db"
        self.sandbox_db_path = Path.home() / ".leon" / "sandbox.db"

    def _init_sandbox(self, sandbox: Any) -> Any:
        """Initialize sandbox infrastructure layer."""
        from sandbox import Sandbox as SandboxBase
        from sandbox import SandboxConfig, create_sandbox, resolve_sandbox_name

        if isinstance(sandbox, SandboxBase):
            return sandbox

        if isinstance(sandbox, str) or sandbox is None:
            sandbox_name = resolve_sandbox_name(sandbox)
            sandbox_config = SandboxConfig.load(sandbox_name)
            return create_sandbox(
                sandbox_config,
                workspace_root=str(self.workspace_root),
                db_path=self.sandbox_db_path,
            )

        raise TypeError(f"sandbox must be Sandbox, str, or None, got {type(sandbox)}")

    def _resolve_env_api_key(self) -> str | None:
        """Resolve API key from environment variables based on model_provider."""
        provider = self.profile.agent.model_provider
        if not provider:
            return os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google_genai": "GOOGLE_API_KEY",
            "bedrock": None,
        }
        env_var = env_map.get(provider)
        return os.getenv(env_var) if env_var else None

    def _resolve_env_base_url(self) -> str | None:
        """Resolve base URL from environment variables based on model_provider."""
        provider = self.profile.agent.model_provider
        if not provider:
            return os.getenv("OPENAI_BASE_URL")

        env_map = {"openai": "OPENAI_BASE_URL"}
        env_var = env_map.get(provider)
        return os.getenv(env_var) if env_var else None

    def _create_model(self):
        """Initialize model with all parameters passed to init_chat_model."""
        kwargs = self._build_model_kwargs()
        return init_chat_model(self.model_name, api_key=self.api_key, **kwargs)

    def _build_model_kwargs(self) -> dict:
        """Build model parameters for model initialization and sub-agents."""
        kwargs = {}

        if self.profile.agent.model_provider:
            kwargs["model_provider"] = self.profile.agent.model_provider

        base_url = self.profile.agent.base_url or self._resolve_env_base_url()
        if base_url:
            kwargs["base_url"] = base_url

        if self.profile.agent.temperature is not None:
            kwargs["temperature"] = self.profile.agent.temperature
        if self.profile.agent.max_tokens is not None:
            kwargs["max_tokens"] = self.profile.agent.max_tokens

        kwargs.update(self.profile.agent.model_kwargs)
        return kwargs

    def close(self):
        """Clean up resources."""
        self._cleanup_sandbox()
        self._mark_terminated()
        self._cleanup_mcp_client()
        self._cleanup_sqlite_connection()

    def _cleanup_sandbox(self) -> None:
        """Clean up sandbox resources."""
        if hasattr(self, "_sandbox") and self._sandbox:
            try:
                self._sandbox.close()
            except Exception as e:
                print(f"[LeonAgent] Sandbox cleanup error: {e}")

    def _mark_terminated(self) -> None:
        """Mark agent as terminated."""
        if hasattr(self, "_monitor_middleware"):
            self._monitor_middleware.mark_terminated()

    def _cleanup_mcp_client(self) -> None:
        """Clean up MCP client."""
        if not hasattr(self, "_mcp_client") or not self._mcp_client:
            return

        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._mcp_client.close())
            finally:
                loop.close()
        except Exception:
            pass
        self._mcp_client = None

    def _cleanup_sqlite_connection(self) -> None:
        """Clean up SQLite connection."""
        if not hasattr(self, "_aiosqlite_conn") or not self._aiosqlite_conn:
            return

        import asyncio

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
  # model_provider: null    # openai / anthropic / bedrock 等，null 时自动推断
  # api_key: null           # 通用 API key，null 时从环境变量读取
  # base_url: null          # 通用 base URL，null 时从环境变量读取
  # temperature: null
  # max_tokens: null
  # model_kwargs: {}        # 透传给 init_chat_model 的额外参数
  enable_audit_log: true
  block_dangerous_commands: true
  # Queue mode: Agent 运行时输入消息的处理方式
  # - steer: 注入当前运行，改变执行方向（默认）
  # - followup: 等当前运行结束后处理
  # - collect: 收集多条消息，合并后处理
  # - steer_backlog: 注入 + 保留为 followup
  # - interrupt: 中断当前运行
  queue_mode: steer
  # Context memory management
  # memory:
  #   enabled: true
  #   pruning:
  #     soft_trim_chars: 3000
  #     hard_clear_threshold: 10000
  #     protect_recent: 3
  #   compaction:
  #     reserve_tokens: 16384
  #     keep_recent_tokens: 20000

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
        """Build middleware stack."""
        middleware = []

        # Get backends from sandbox
        fs_backend = self._sandbox.fs()
        cmd_executor = self._sandbox.shell()

        # 0. Steering (highest priority)
        middleware.append(SteeringMiddleware())

        # 1. Memory (context pruning + compaction)
        if self.profile.agent.memory.enabled:
            self._add_memory_middleware(middleware)

        # 2. Prompt Caching
        middleware.append(PromptCachingMiddleware(ttl="5m", min_messages_to_cache=0))

        # 3. FileSystem
        if self.profile.tool.filesystem.enabled:
            self._add_filesystem_middleware(middleware, fs_backend)

        # 4. Search
        if self.profile.tool.search.enabled:
            self._add_search_middleware(middleware)

        # 5. Web
        if self.profile.tool.web.enabled:
            self._add_web_middleware(middleware)

        # 6. Command
        if self.profile.tool.command.enabled:
            self._add_command_middleware(middleware, cmd_executor)

        # 7. Skills
        if self.profile.skills.enabled and self.profile.skills.paths:
            self._add_skills_middleware(middleware)

        # 8. Todo
        self._todo_middleware = TodoMiddleware(verbose=self.verbose)
        middleware.append(self._todo_middleware)

        # 9. Task (sub-agent orchestration)
        self._task_middleware = TaskMiddleware(
            workspace_root=self.workspace_root,
            parent_model=self.model_name,
            api_key=self.api_key,
            model_kwargs=self._build_model_kwargs(),
            verbose=self.verbose,
        )
        middleware.append(self._task_middleware)

        # 10. Monitor (last to capture all requests/responses)
        self._monitor_middleware = MonitorMiddleware(
            context_limit=self.profile.agent.context_limit,
            model_name=self.model_name,
            verbose=self.verbose,
        )
        middleware.append(self._monitor_middleware)

        return middleware

    def _add_memory_middleware(self, middleware: list) -> None:
        """Add memory middleware to stack."""
        cfg = self.profile.agent.memory
        db_path = Path.home() / ".leon" / "leon.db"
        self._memory_middleware = MemoryMiddleware(
            context_limit=self.profile.agent.context_limit,
            pruning_config=cfg.pruning,
            compaction_config=cfg.compaction,
            db_path=db_path,
            checkpointer=self.checkpointer,
            compaction_threshold=0.7,
            verbose=self.verbose,
        )
        middleware.append(self._memory_middleware)

    def _add_filesystem_middleware(self, middleware: list, fs_backend: Any) -> None:
        """Add filesystem middleware to stack."""
        file_hooks = []
        if self._sandbox.name == "local":
            if self.enable_audit_log:
                file_hooks.append(
                    FileAccessLoggerHook(
                        workspace_root=self.workspace_root,
                        log_file="file_access.log",
                    )
                )
            file_hooks.append(
                FilePermissionHook(
                    workspace_root=self.workspace_root,
                    allowed_extensions=self.allowed_file_extensions,
                )
            )

        fs_tools = {
            "read_file": self.profile.tool.filesystem.tools.read_file.enabled,
            "write_file": self.profile.tool.filesystem.tools.write_file,
            "edit_file": self.profile.tool.filesystem.tools.edit_file,
            "multi_edit": self.profile.tool.filesystem.tools.multi_edit,
            "list_dir": self.profile.tool.filesystem.tools.list_dir,
        }

        middleware.append(
            FileSystemMiddleware(
                workspace_root=self.workspace_root,
                max_file_size=self.profile.tool.filesystem.tools.read_file.max_file_size,
                allowed_extensions=self.allowed_file_extensions,
                hooks=file_hooks,
                enabled_tools=fs_tools,
                operation_recorder=get_recorder(),
                backend=fs_backend,
                verbose=self.verbose,
            )
        )

    def _add_search_middleware(self, middleware: list) -> None:
        """Add search middleware to stack."""
        search_tools = {
            "grep_search": self.profile.tool.search.tools.grep_search.enabled,
            "find_by_name": self.profile.tool.search.tools.find_by_name,
        }
        middleware.append(
            SearchMiddleware(
                workspace_root=self.workspace_root,
                max_results=self.profile.tool.search.max_results,
                max_file_size=self.profile.tool.search.tools.grep_search.max_file_size,
                prefer_system_tools=True,
                enabled_tools=search_tools,
                verbose=self.verbose,
            )
        )

    def _add_web_middleware(self, middleware: list) -> None:
        """Add web middleware to stack."""
        web_tools = {
            "web_search": self.profile.tool.web.tools.web_search.enabled,
            "read_url_content": self.profile.tool.web.tools.read_url_content.enabled,
            "view_web_content": self.profile.tool.web.tools.view_web_content,
        }
        middleware.append(
            WebMiddleware(
                tavily_api_key=self.profile.tool.web.tools.web_search.tavily_api_key or os.getenv("TAVILY_API_KEY"),
                exa_api_key=self.profile.tool.web.tools.web_search.exa_api_key or os.getenv("EXA_API_KEY"),
                firecrawl_api_key=self.profile.tool.web.tools.web_search.firecrawl_api_key
                or os.getenv("FIRECRAWL_API_KEY"),
                jina_api_key=self.profile.tool.web.tools.read_url_content.jina_api_key or os.getenv("JINA_AI_API_KEY"),
                max_search_results=self.profile.tool.web.tools.web_search.max_results,
                timeout=self.profile.tool.web.timeout,
                enabled_tools=web_tools,
                verbose=self.verbose,
            )
        )

    def _add_command_middleware(self, middleware: list, cmd_executor: Any) -> None:
        """Add command middleware to stack."""
        command_hooks = []
        if self._sandbox.name == "local":
            if self.block_dangerous_commands:
                command_hooks.append(
                    DangerousCommandsHook(
                        workspace_root=self.workspace_root,
                        block_network=self.block_network_commands,
                        verbose=self.verbose,
                    )
                )
            command_hooks.append(PathSecurityHook(workspace_root=self.workspace_root))

        command_tools = {
            "run_command": self.profile.tool.command.tools.run_command.enabled,
            "command_status": self.profile.tool.command.tools.command_status,
        }
        middleware.append(
            CommandMiddleware(
                workspace_root=self.workspace_root,
                default_timeout=self.profile.tool.command.tools.run_command.default_timeout,
                hooks=command_hooks,
                enabled_tools=command_tools,
                executor=cmd_executor,
                verbose=self.verbose,
            )
        )

    def _add_skills_middleware(self, middleware: list) -> None:
        """Add skills middleware to stack."""
        middleware.append(
            SkillsMiddleware(
                skill_paths=self.profile.skills.paths,
                enabled_skills=self.profile.skills.skills,
                verbose=self.verbose,
            )
        )

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
                    if hasattr(tool, "metadata") and tool.metadata:
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
        # @@@ WAL mode allows concurrent reads/writes from sandbox manager
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=30000")
        self.checkpointer = AsyncSqliteSaver(conn)
        await self.checkpointer.setup()
        return conn

    def _is_tool_allowed(self, tool) -> bool:
        # Extract original tool name without mcp__ prefix
        tool_name = tool.name
        if tool_name.startswith("mcp__"):
            parts = tool_name.split("__", 2)
            if len(parts) == 3:
                tool_name = parts[2]

        for cfg in self.profile.mcp.servers.values():
            if cfg.allowed_tools:
                return tool_name in cfg.allowed_tools
        return True

    def _build_system_prompt(self) -> str:
        """Build system prompt based on sandbox mode."""
        import platform

        os_name = platform.system()
        shell_name = os.environ.get("SHELL", "/bin/bash").split("/")[-1]

        if self._sandbox.name != "local":
            prompt = self._build_sandbox_prompt()
        else:
            prompt = self._build_local_prompt(os_name, shell_name)

        prompt += self._build_common_prompt_sections()

        if self.allowed_file_extensions:
            prompt += f"\n6. **File Type Restriction**: Only these extensions allowed: {', '.join(self.allowed_file_extensions)}\n"

        return prompt

    def _build_sandbox_prompt(self) -> str:
        """Build system prompt for sandbox mode."""
        env_label = self._sandbox.env_label
        working_dir = self._sandbox.working_dir

        if self._sandbox.name == "docker":
            mode_label = "Sandbox (isolated local container)"
            location_rule = (
                "All file and command operations run in a local Docker container, NOT on the user's host filesystem."
            )
        else:
            mode_label = "Sandbox (isolated cloud environment)"
            location_rule = "All file and command operations run in a remote sandbox, NOT on the user's local machine."

        return f"""You are a highly capable AI assistant with access to a sandbox environment.

**Context:**
- Environment: {env_label}
- Working Directory: {working_dir}
- Mode: {mode_label}

**Important Rules:**

1. **Sandbox Environment**: {location_rule} The sandbox is an isolated Linux environment.

2. **Absolute Paths**: All file paths must be absolute paths.
   - ✅ Correct: `{working_dir}/project/test.py` or `/tmp/output.txt`
   - ❌ Wrong: `test.py` or `./test.py`

3. **Available Tools**: You have tools for file operations (read_file, write_file, edit_file, list_dir) and command execution (run_command).

4. **Security**: The sandbox is isolated. You can install packages, run any commands, and modify files freely within the sandbox.
"""

    def _build_local_prompt(self, os_name: str, shell_name: str) -> str:
        """Build system prompt for local mode."""
        return f"""You are a highly capable AI assistant with access to file and system tools.

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

    def _build_common_prompt_sections(self) -> str:
        """Build common prompt sections for both sandbox and local modes."""
        return """
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

    def invoke(self, message: str, thread_id: str = "default") -> dict:
        """Invoke agent with a message.

        Args:
            message: User message
            thread_id: Thread ID

        Returns:
            Agent response (includes messages and state)
        """
        import asyncio

        async def _ainvoke():
            return await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": thread_id}},
            )

        try:
            return asyncio.run(_ainvoke())
        except Exception as e:
            self._monitor_middleware.mark_error(e)
            raise

    def get_response(self, message: str, thread_id: str = "default", **kwargs) -> str:
        """Get agent's text response.

        Args:
            message: User message
            thread_id: Thread ID
            **kwargs: Additional state parameters

        Returns:
            Agent's text response
        """
        result = self.invoke(message, thread_id, **kwargs)
        return result["messages"][-1].content

    def cleanup(self):
        """Clean up temporary workspace directory."""
        if self.workspace_root.exists() and "tmp" in str(self.workspace_root):
            import shutil

            shutil.rmtree(self.workspace_root, ignore_errors=True)


def create_leon_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
    api_key: str | None = None,
    workspace_root: str | Path | None = None,
    sandbox: Any = None,
    **kwargs,
) -> LeonAgent:
    """Create Leon Agent.

    Args:
        model_name: Model name
        api_key: API key
        workspace_root: Workspace directory
        sandbox: Sandbox instance, name string, or None for local
        **kwargs: Additional configuration parameters

    Returns:
        Configured LeonAgent instance

    Examples:
        # Basic usage
        agent = create_leon_agent()

        # With sandbox
        agent = create_leon_agent(sandbox="agentbay")

        # Custom workspace
        agent = create_leon_agent(workspace_root="/path/to/workspace")
    """
    return LeonAgent(
        model_name=model_name,
        api_key=api_key,
        workspace_root=workspace_root,
        sandbox=sandbox,
        **kwargs,
    )


if __name__ == "__main__":
    # Example usage
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
        response = leon_agent.get_response(f"Read the file {leon_agent.workspace_root}/hello.py", thread_id="demo")
        print(response)
        print()

        print("=== Example 3: Search ===")
        response = leon_agent.get_response(f"Search for 'Hello' in {leon_agent.workspace_root}", thread_id="demo")
        print(response)

    finally:
        leon_agent.cleanup()
