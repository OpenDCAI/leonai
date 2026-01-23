"""
Leon - 完全模仿 Windsurf Cascade 的 Agent 实现

使用纯 Middleware 架构实现所有工具：
- FileSystemMiddleware: read_file, write_file, edit_file, multi_edit, list_dir
- SearchMiddleware: grep_search, find_by_name
- ShellMiddleware: run_command (with hooks)
- PromptCachingMiddleware: 成本优化

所有路径必须使用绝对路径，完整的安全机制和审计日志。
"""

import os
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from middleware.filesystem import FileSystemMiddleware
from middleware.prompt_caching import PromptCachingMiddleware
from middleware.search import SearchMiddleware
from middleware.shell import ShellMiddleware

# 导入 hooks
from middleware.shell.hooks.dangerous_commands import DangerousCommandsHook
from middleware.shell.hooks.file_access_logger import FileAccessLoggerHook
from middleware.shell.hooks.file_permission import FilePermissionHook


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
    3. 命令执行：bash (通过 ShellMiddleware)
    """

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-5-20250929",
        api_key: str | None = None,
        workspace_root: str | Path | None = None,
        *,
        read_only: bool = False,
        allowed_file_extensions: list[str] | None = None,
        block_dangerous_commands: bool = True,
        block_network_commands: bool = False,
        enable_audit_log: bool = True,
    ):
        """
        初始化 Cascade-Like Agent

        Args:
            model_name: Anthropic 模型名称
            api_key: API key (默认从环境变量读取)
            workspace_root: 工作目录（所有操作限制在此目录内）
            read_only: 只读模式（禁止写入和编辑）
            allowed_file_extensions: 允许的文件扩展名（None 表示全部允许）
            block_dangerous_commands: 是否拦截危险命令
            block_network_commands: 是否拦截网络命令
            enable_audit_log: 是否启用审计日志
        """
        self.model_name = model_name

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
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            self.workspace_root = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")

        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # 配置参数
        self.read_only = read_only
        self.allowed_file_extensions = allowed_file_extensions
        self.block_dangerous_commands = block_dangerous_commands
        self.block_network_commands = block_network_commands
        self.enable_audit_log = enable_audit_log

        # 初始化模型
        model_kwargs = {"api_key": self.api_key}
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            model_kwargs["base_url"] = base_url

        self.model = init_chat_model(self.model_name, **model_kwargs)

        # 构建 middleware 栈
        middleware = []

        # 1. Prompt Caching - 成本优化
        middleware.append(
            PromptCachingMiddleware(
                ttl="5m",
                min_messages_to_cache=0,
            )
        )

        # 2. FileSystem Middleware - 文件操作
        file_hooks = []

        # 添加文件访问日志 hook
        if self.enable_audit_log:
            file_hooks.append(
                FileAccessLoggerHook(
                    workspace_root=self.workspace_root, log_file="file_access.log"
                )
            )

        # 添加文件权限控制 hook
        file_hooks.append(
            FilePermissionHook(
                workspace_root=self.workspace_root,
                read_only=self.read_only,
                allowed_extensions=self.allowed_file_extensions,
            )
        )

        middleware.append(
            FileSystemMiddleware(
                workspace_root=self.workspace_root,
                read_only=self.read_only,
                allowed_extensions=self.allowed_file_extensions,
                hooks=file_hooks,
            )
        )

        # 3. Search Middleware - 搜索功能
        middleware.append(SearchMiddleware(workspace_root=self.workspace_root))

        # 4. Bash Middleware - 命令执行（带安全 hooks）
        bash_hook_config = {"strict_mode": True}

        # 如果启用危险命令拦截，需要手动添加到 hooks
        # 注意：ShellMiddleware 会自动加载 shell/hooks/ 目录下的所有 hooks
        middleware.append(
            ShellMiddleware(
                workspace_root=str(self.workspace_root),
                allow_system_python=True,
                hook_config=bash_hook_config,
            )
        )

        # 创建 agent
        self.agent = create_agent(
            model=self.model,
            tools=[],  # 所有工具都由 middleware 提供
            middleware=middleware,
        )

        # System prompt
        self.system_prompt = self._build_system_prompt()

        print(f"[LeonAgent] Initialized successfully")
        print(f"[LeonAgent] Workspace: {self.workspace_root}")
        print(f"[LeonAgent] Read-only: {self.read_only}")
        print(f"[LeonAgent] Audit log: {self.enable_audit_log}")

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        prompt = f"""You are a highly capable AI assistant with access to powerful file and system tools.

**Available Tools:**

1. **File Operations** (all paths must be absolute):
   - `read_file`: Read file content (supports pagination)
   - `write_file`: Create new files
   - `edit_file`: Edit existing files (string replacement)
   - `multi_edit`: Apply multiple edits sequentially
   - `list_dir`: List directory contents

2. **Search Tools** (all paths must be absolute):
   - `grep_search`: Search file contents using regex
   - `find_by_name`: Find files by name pattern

3. **Command Execution**:
   - `bash`: Execute shell commands
   - Commands are validated by security hooks
   - Restricted to workspace directory

**Important Rules:**

1. **Absolute Paths Only**: All file paths and directory paths MUST be absolute paths starting from root (/).
   - ✅ Correct: `/Users/apple/Desktop/project/v1/文稿/project/leon/workspace/test.py`
   - ❌ Wrong: `test.py` or `./test.py`

2. **Workspace Restriction**: All operations are restricted to: {self.workspace_root}
   - You cannot access files outside this directory
   - Attempts to access external paths will be blocked

3. **Security**:
   - Dangerous commands are blocked (rm -rf, sudo, etc.)
   - All operations are logged for audit
"""

        if self.read_only:
            prompt += "\n   - **READ-ONLY MODE**: Write and edit operations are disabled\n"

        if self.allowed_file_extensions:
            prompt += f"\n   - **File Type Restriction**: Only these extensions allowed: {', '.join(self.allowed_file_extensions)}\n"

        prompt += """
4. **Best Practices**:
   - Always use `read_file` before editing to understand file structure
   - Use `list_dir` to explore directory structure
   - Use `grep_search` to find specific content across files
   - For multiple edits, use `multi_edit` instead of multiple `edit_file` calls

5. **Error Handling**:
   - If a command is blocked, explain the security reason to the user
   - Suggest alternative approaches when operations fail
   - Always provide clear feedback about what happened

Be helpful, accurate, and security-conscious in all your operations.
"""

        return prompt

    def invoke(self, message: str, thread_id: str = "default", **kwargs) -> dict:
        """
        调用 agent

        Args:
            message: 用户消息
            thread_id: 线程 ID
            **kwargs: 额外的状态参数

        Returns:
            Agent 响应（包含消息和状态）
        """
        config = {"configurable": {"thread_id": thread_id}}

        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}], **kwargs}, config=config
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


if __name__ == "__main__":
    # 示例用法
    agent = create_leon_agent()

    try:
        print("=== Example 1: File Operations ===")
        response = agent.get_response(
            f"Create a Python file at {agent.workspace_root}/hello.py that prints 'Hello, Cascade!'",
            thread_id="demo",
        )
        print(response)
        print()

        print("=== Example 2: Read File ===")
        response = agent.get_response(
            f"Read the file {agent.workspace_root}/hello.py", thread_id="demo"
        )
        print(response)
        print()

        print("=== Example 3: Search ===")
        response = agent.get_response(
            f"Search for 'Hello' in {agent.workspace_root}", thread_id="demo"
        )
        print(response)

    finally:
        agent.cleanup()
