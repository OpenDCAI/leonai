"""
Comprehensive LangChain Agent with All Anthropic Middleware

This module demonstrates a production-ready agent using all available
Anthropic middleware components:
- Prompt caching for cost reduction
- Bash tool for command execution
- Text editor for file operations
- Memory for persistent context
- File search for state-based file systems

Uses LangChain v1 API with create_agent.
"""

import os
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from middleware import (
    AnthropicPromptCachingMiddleware,
    StateClaudeMemoryMiddleware,
    StateClaudeTextEditorMiddleware,
    StateFileSearchMiddleware,
)
from middleware.extensible_bash import ExtensibleBashMiddleware


class LeonAgent:
    """
    A comprehensive agent with all Anthropic middleware enabled.

    Features:
    - Prompt caching: Reduces costs by caching repetitive content
    - Bash tool: Execute shell commands in isolated Docker environment
    - Text editor: Create and edit files in state
    - Memory: Persistent agent memory across conversations
    - File search: Search through state-based files
    """

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-5-20250929",
        api_key: str | None = None,
        workspace_root: str | Path | None = None,
    ):
        """
        Initialize the Leon agent.

        Args:
            model_name: Anthropic model to use
            api_key: API key (defaults to OPENAI_API_KEY env var for proxy compatibility)
            workspace_root: Root directory for bash operations (defaults to ./workspace)
        """
        self.model_name = model_name

        # Default to OPENAI_API_KEY for third-party Anthropic proxy compatibility
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "API key must be set via:\n"
                "  - OPENAI_API_KEY environment variable (recommended for proxy)\n"
                "  - ANTHROPIC_API_KEY environment variable\n"
                "  - api_key parameter"
            )

        # Setup workspace - default to /Users/apple/Desktop/project/v1/文稿/project/leon/workspace
        if workspace_root:
            self.workspace_root = Path(workspace_root)
        else:
            # Default: workspace in leon project root
            self.workspace_root = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")

        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Initialize model using init_chat_model (LangChain v1 API)
        # Support custom base URL for third-party proxy
        model_kwargs = {"api_key": self.api_key}
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            model_kwargs["base_url"] = base_url

        self.model = init_chat_model(
            self.model_name,
            **model_kwargs,
        )

        # Setup middleware
        middleware = []

        # 1. Prompt caching - reduces costs for repeated content
        middleware.append(
            AnthropicPromptCachingMiddleware(
                ttl="5m",  # Cache for 5 minutes
                min_messages_to_cache=0,
            )
        )

        # 2. Bash tool - use ExtensibleBashMiddleware with plugin system
        middleware.append(
            ExtensibleBashMiddleware(
                workspace_root=str(self.workspace_root),
                allow_system_python=True,
                hook_config={"strict_mode": True},  # 传递给所有 hooks 的配置
            )
        )

        # 3. Text editor - file creation and editing in state
        middleware.append(
            StateClaudeTextEditorMiddleware(
                allowed_path_prefixes=["/project", "/workspace"],
            )
        )

        # 4. Memory - persistent agent memory
        middleware.append(
            StateClaudeMemoryMiddleware(
                allowed_path_prefixes=["/memories"],
            )
        )

        # 5. File search - search text editor files
        # Note: StateFileSearchMiddleware can only be added once
        middleware.append(
            StateFileSearchMiddleware(
                state_key="text_editor_files",
            )
        )

        # Create agent with all middleware (LangChain v1 API)
        # Note: Checkpointer removed due to bash middleware serialization issues
        # thread_id will not persist across agent restarts
        self.agent = create_agent(
            model=self.model,
            tools=[],  # Tools are provided by middleware
            middleware=middleware,
        )

        self.system_prompt = f"""You are a highly capable AI assistant with access to:

1. **Bash commands**: Execute shell commands within workspace directory
   - 🔒 SECURITY: Commands are validated by security plugins
   - Workspace: {self.workspace_root}
   - Commands are checked before execution
   - If blocked, you'll receive a clear error message
2. **Text editor**: Create, view, and edit files in the /project and /workspace directories
3. **Memory system**: Store and retrieve important information in /memories
4. **File search**: Search through files using glob patterns and grep

When working on tasks:
- Use memory to track progress and important context
- Create files in /project for user-facing work
- Use bash for system operations and data processing
- Search files efficiently when looking for specific content
- If a command is blocked, explain the security reason to the user

Always be helpful, accurate, and efficient in your responses."""

    def invoke(
        self,
        message: str,
        thread_id: str = "default",
        **kwargs
    ) -> dict:
        """
        Invoke the agent with a message.

        Args:
            message: User message
            thread_id: Thread ID for conversation persistence
            **kwargs: Additional state parameters

        Returns:
            Agent response with messages and state
        """
        config = {"configurable": {"thread_id": thread_id}}

        result = self.agent.invoke(
            {
                "messages": [{"role": "user", "content": message}],
                **kwargs
            },
            config=config,
        )

        return result

    def get_response(
        self,
        message: str,
        thread_id: str = "default",
        **kwargs
    ) -> str:
        """
        Get the agent's text response to a message.

        Args:
            message: User message
            thread_id: Thread ID for conversation persistence
            **kwargs: Additional state parameters

        Returns:
            Agent's text response
        """
        result = self.invoke(message, thread_id, **kwargs)
        return result["messages"][-1].content

    def cleanup(self):
        """Clean up temporary workspace if created."""
        if self.workspace_root.exists() and "tmp" in str(self.workspace_root):
            import shutil
            shutil.rmtree(self.workspace_root, ignore_errors=True)


def create_leon(
    model_name: str = "claude-sonnet-4-5-20250929",
    api_key: str | None = None,
    workspace_root: str | Path | None = None,
) -> LeonAgent:
    """
    Factory function to create Leon agent.

    Args:
        model_name: Anthropic model to use
        api_key: API key (defaults to OPENAI_API_KEY for proxy compatibility)
        workspace_root: Root directory for bash operations (defaults to ./workspace)

    Returns:
        Configured LeonAgent instance

    Examples:
        # Default configuration
        leon = create_leon()

        # Custom workspace
        leon = create_leon(workspace_root="/path/to/workspace")
    """
    return LeonAgent(
        model_name=model_name,
        api_key=api_key,
        workspace_root=workspace_root,
    )


if __name__ == "__main__":
    # Example usage
    leon = create_leon()

    try:
        # Example 1: Use memory
        print("=== Example 1: Memory ===")
        response = leon.get_response(
            "Remember that my favorite programming language is Python and I'm working on a data analysis project.",
            thread_id="demo-session"
        )
        print(response)
        print()

        # Example 2: Create files with text editor
        print("=== Example 2: Text Editor ===")
        response = leon.get_response(
            "Create a Python script at /project/hello.py that prints 'Hello from LangChain!'",
            thread_id="demo-session"
        )
        print(response)
        print()

        # Example 3: Search files
        print("=== Example 3: File Search ===")
        response = leon.get_response(
            "Search for all Python files in the project",
            thread_id="demo-session"
        )
        print(response)
        print()

        # Example 4: Recall memory
        print("=== Example 4: Recall Memory ===")
        response = leon.get_response(
            "What's my favorite programming language?",
            thread_id="demo-session"
        )
        print(response)

    finally:
        leon.cleanup()
