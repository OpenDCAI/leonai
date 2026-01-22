# Leon - Cascade-Like Agent

一个完全模仿 Windsurf Cascade 的 LangChain Agent，使用纯 Middleware 架构实现所有工具。

**Built with LangChain v1** - 使用最新的 `create_agent` API 和现代 middleware 架构。

## ✨ 特点

### 完全匹配 Cascade 的工具和输出格式

### 1. **Prompt Caching** (`AnthropicPromptCachingMiddleware`)
- Reduces API costs by caching repetitive prompt content
- Caches system prompts, tool definitions, and conversation history
- Configurable TTL (5 minutes or 1 hour)
- Automatic ~10x speedup and cost reduction for repeated context

### 2. **Bash Tool** (`ClaudeBashToolMiddleware`)
- Execute shell commands with Claude's native bash tool
- Persistent shell sessions across commands
- Optional Docker isolation for security
- Configurable startup commands and workspace

### 3. **Text Editor** (`StateClaudeTextEditorMiddleware`)
- Create, view, edit, and delete files in state
- Supports: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`
- Path validation and size limits
- Files persist in LangGraph state

### 4. **Memory** (`StateClaudeMemoryMiddleware`)
- Persistent agent memory across conversation turns
- Automatic memory management in `/memories` directory
- System prompt injection for memory awareness
- Perfect for long-running conversations

### 5. **File Search** (`StateFileSearchMiddleware`)
- Glob pattern search for file discovery
- Grep search for content matching
- Works with both text editor and memory files
- Efficient state-based file system queries

## Installation

### Prerequisites
- Python 3.10+ (LangChain v1 requires Python 3.10 or higher)
- Anthropic API key
- (Optional) Docker for isolated bash execution

### Setup

1. **Clone or create the project directory:**
```bash
cd langchain_anthropic_agent
```

2. **Install dependencies using uv (recommended):**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Or using pip:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U -r requirements.txt
```

**Note**: This project uses the latest LangChain v1 API. The dependencies will automatically install the most recent versions.

3. **Set up environment variables:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API key
```

## Usage

### Basic Usage

```python
from agent import create_comprehensive_agent

# Create agent with all middleware enabled
agent = create_comprehensive_agent()

# Simple conversation
response = agent.get_response(
    "Create a Python script that analyzes CSV data",
    thread_id="my-session"
)
print(response)

# Cleanup when done
agent.cleanup()
```

### Advanced Configuration

```python
from agent import create_comprehensive_agent

agent = create_comprehensive_agent(
    model_name="claude-sonnet-4-5-20250929",  # Model selection
    api_key="your-api-key",                    # Or use env var
    workspace_root="/path/to/workspace",       # Custom workspace
    docker_image="python:3.11-slim",           # Docker image
    enable_docker=True,                        # Enable Docker isolation
)
```

### Running Examples

The `examples.py` file demonstrates all middleware capabilities:

```bash
python examples.py
```

Examples include:
1. **Memory Persistence** - Store and recall information across turns
2. **File Operations** - Create, edit, and manage files
3. **File Search** - Find files and search content
4. **Bash Commands** - Execute shell commands
5. **Combined Workflow** - Complex multi-step data analysis
6. **Prompt Caching** - Demonstrate caching benefits

### Individual Examples

```python
from examples import (
    example_memory_persistence,
    example_file_operations,
    example_file_search,
    example_bash_commands,
    example_combined_workflow,
)

# Run specific example
example_memory_persistence()
```

## Architecture

### LangChain v1 API

This project uses the new **LangChain v1** API:
- `from langchain.agents import create_agent` - New standard for building agents
- `from langchain.chat_models import init_chat_model` - Unified model initialization
- `from langgraph.checkpoint.memory import InMemorySaver` - State persistence

### Middleware Stack

The agent uses a layered middleware architecture:

```
┌─────────────────────────────────────┐
│   AnthropicPromptCachingMiddleware  │ ← Cost optimization
├─────────────────────────────────────┤
│   ClaudeBashToolMiddleware          │ ← Command execution
├─────────────────────────────────────┤
│   StateClaudeTextEditorMiddleware   │ ← File operations
├─────────────────────────────────────┤
│   StateClaudeMemoryMiddleware       │ ← Persistent memory
├─────────────────────────────────────┤
│   StateFileSearchMiddleware (x2)    │ ← File search
└─────────────────────────────────────┘
           ↓
    init_chat_model (LangChain v1)
```

### State Management

The agent uses LangGraph's `InMemorySaver` checkpointer to persist:
- Conversation history
- Text editor files (`text_editor_files`)
- Memory files (`memory_files`)
- Custom state across invocations

## API Reference

### `ComprehensiveAnthropicAgent`

Main agent class with all middleware enabled.

**Constructor Parameters:**
- `model_name` (str): Anthropic model name (default: "claude-sonnet-4-5-20250929")
- `api_key` (str | None): API key (defaults to `ANTHROPIC_API_KEY` env var)
- `workspace_root` (str | None): Workspace directory (defaults to temp dir)
- `docker_image` (str): Docker image for bash execution (default: "python:3.11-slim")
- `enable_docker` (bool): Enable Docker isolation (default: False)

**Methods:**

#### `invoke(message: str, thread_id: str = "default", **kwargs) -> dict`
Invoke agent with full state response.

#### `get_response(message: str, thread_id: str = "default", **kwargs) -> str`
Get agent's text response only.

#### `cleanup()`
Clean up temporary workspace.

### Factory Function

```python
create_comprehensive_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
    api_key: str | None = None,
    workspace_root: str | None = None,
    docker_image: str = "python:3.11-slim",
    enable_docker: bool = False,
) -> ComprehensiveAnthropicAgent
```

## Middleware Details

### Prompt Caching

Caches content up to and including the latest message:
- **First request**: System prompt, tools, and messages are cached
- **Subsequent requests**: Cached content is reused (within TTL)
- **TTL options**: `"5m"` or `"1h"`

### Bash Tool

Execute commands in persistent shell sessions:
- **Workspace isolation**: Commands run in specified workspace
- **Docker support**: Optional containerized execution
- **Startup commands**: Initialize environment on session start
- **Session persistence**: Variables and state maintained across commands

### Text Editor

State-based file system with full CRUD operations:
- **Allowed paths**: `/project`, `/workspace` (configurable)
- **Commands**: view, create, str_replace, insert, delete, rename
- **State key**: `text_editor_files`
- **Persistence**: Files stored in LangGraph state

### Memory

Persistent agent memory system:
- **Memory directory**: `/memories`
- **Auto-injection**: System prompt encourages memory usage
- **State key**: `memory_files`
- **Use cases**: User preferences, task progress, context tracking

### File Search

Two search tools for state-based files:
- **Glob search**: Pattern-based file discovery (`*.py`, `**/*.txt`)
- **Grep search**: Content search with regex support
- **Dual instances**: Search both text editor and memory files

## Best Practices

### 1. Thread Management
Use consistent `thread_id` for conversation continuity:
```python
thread_id = f"user-{user_id}-session-{session_id}"
agent.get_response(message, thread_id=thread_id)
```

### 2. Memory Usage
Encourage agent to use memory for important context:
```python
agent.get_response(
    "Remember my project deadline is March 15th. Confirm what you stored.",
    thread_id=thread_id
)
```

### 3. File Organization
Use clear directory structure:
- `/project/*` - User-facing work
- `/workspace/*` - Temporary/scratch files
- `/memories/*` - Persistent memory (automatic)

### 4. Error Handling
Always use try-finally for cleanup:
```python
agent = create_comprehensive_agent()
try:
    result = agent.get_response("Your task")
finally:
    agent.cleanup()
```

### 5. Docker Security
Enable Docker for untrusted code execution:
```python
agent = create_comprehensive_agent(
    enable_docker=True,
    docker_image="python:3.11-slim"
)
```

## Troubleshooting

### API Key Issues
```
ValueError: ANTHROPIC_API_KEY must be set
```
**Solution**: Set environment variable or pass `api_key` parameter.

### Docker Not Available
```
Error: Docker daemon not running
```
**Solution**: Set `enable_docker=False` or start Docker daemon.

### Import Errors
```
ModuleNotFoundError: No module named 'langchain_anthropic'
```
**Solution**: Install dependencies: `uv pip install -r requirements.txt`

### Memory/File Not Persisting
**Issue**: Files/memory lost between invocations.
**Solution**: Use consistent `thread_id` and ensure checkpointer is configured.

## Performance Tips

1. **Prompt Caching**: Reuse long system prompts across requests
2. **Thread Reuse**: Keep `thread_id` consistent for cache hits
3. **Batch Operations**: Combine multiple file operations in one request
4. **Docker Overhead**: Only enable Docker when security is critical

## Cost Optimization

- **Prompt caching**: ~90% cost reduction on cached tokens
- **Model selection**: Use `claude-sonnet-4-5-20250929` for balance
- **Message management**: Clear old threads to reduce state size
- **Cache TTL**: Use `"5m"` for short sessions, `"1h"` for long ones

## Examples Output

When you run `python examples.py`, you'll see:

```
==========================================================
COMPREHENSIVE ANTHROPIC AGENT - EXAMPLES
==========================================================

Available examples:
  1. Memory Persistence
  2. File Operations
  3. File Search
  4. Bash Commands
  5. Combined Workflow
  6. Prompt Caching

Running all examples...

==========================================================
EXAMPLE 1: Memory Persistence
==========================================================
[Agent demonstrates storing and recalling information]
...
```

## Contributing

This is a demonstration project showing all Anthropic middleware capabilities. Feel free to:
- Extend with custom middleware
- Add new example scenarios
- Integrate with your applications
- Report issues or improvements

## Resources

- [LangChain Documentation](https://docs.langchain.com)
- [Anthropic Middleware Guide](https://docs.langchain.com/oss/python/integrations/middleware/anthropic)
- [Claude API Documentation](https://docs.anthropic.com)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

## License

MIT License - feel free to use in your projects.

---

**Built with LangChain + Anthropic Claude** 🦜🔗🤖
