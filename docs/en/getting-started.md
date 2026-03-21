English | [中文](../zh/getting-started.md)

# Getting Started with Mycel

Mycel is a proactive AI coding assistant with persistent memory, sandboxed code execution, and multi-agent communication. It offers two interfaces: a **Web UI** for visual interaction and a **CLI/TUI** for terminal workflows. Choose whichever suits you.

## Installation

Requires Python 3.12 or later.

### From PyPI

```bash
pip install leonai
```

Or with [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install leonai
```

### From Source

```bash
git clone https://github.com/Ju-Yi-AI-Lab/leonai.git
cd leonai
uv tool install .
```

### Optional Extras

```bash
# PDF and PowerPoint file reading
pip install "leonai[docs]"

# Sandbox providers
pip install "leonai[sandbox]"     # AgentBay
pip install "leonai[e2b]"         # E2B
pip install "leonai[daytona]"     # Daytona

# Observability
pip install "leonai[langfuse]"
pip install "leonai[langsmith]"

# Everything
pip install "leonai[all]"
```

---

## Option A: Web UI (Recommended for Most Users)

The Web UI provides a browser-based interface with real-time streaming, visual agent configuration, and multi-agent chat.

### 1. Start the Backend

```bash
python -m backend.web.main
```

This launches a uvicorn server on `http://localhost:8001` with auto-reload enabled.

To use a different port:

```bash
LEON_BACKEND_PORT=8002 python -m backend.web.main
```

### 2. Start the Frontend

```bash
cd frontend/app
npm install
npm run dev
```

This opens the frontend at `http://localhost:5173`.

### 3. Register and Configure

1. Open your browser and go to `http://localhost:5173`
2. Create an account using the Register form
3. Navigate to **Settings** to configure your LLM provider:
   - Add your API key
   - Set the base URL for your provider
   - Select or register models

Provider credentials for the Web UI are stored in `~/.leon/models.json`. The Web UI supports:

- Multiple providers simultaneously (OpenAI, Anthropic, OpenRouter, etc.)
- Virtual model mapping (e.g., `leon:large` maps to a concrete model)
- Per-model provider routing
- Custom model registration with live testing

### Web UI Features

- Visual agent configuration (system prompts, tools, rules, MCP servers)
- Multi-agent chat between humans and AI agents
- Sandbox session management with resource monitoring
- Real-time streaming of agent responses via SSE

---

## Option B: CLI / TUI

The CLI provides a terminal-based interface for quick interactions and scripting.

### First Run

```bash
leonai
```

If no API key is detected, the interactive config wizard (`leonai config`) starts automatically. It asks for:

1. **API_KEY** (required) -- Your OpenAI-compatible API key. Stored as `OPENAI_API_KEY`.
2. **BASE_URL** (optional) -- The API endpoint. Defaults to `https://api.openai.com/v1`. Auto-appends `/v1` if omitted.
3. **MODEL_NAME** (optional) -- The model to use. Defaults to `claude-sonnet-4-5-20250929`.

Configuration is saved to `~/.leon/config.env` as `KEY=VALUE` pairs.

Re-run the wizard or inspect settings any time:

```bash
leonai config          # Re-run wizard
leonai config show     # View current settings
```

### Usage

```bash
leonai                          # Start a new conversation
leonai -c                       # Continue last conversation
leonai --thread <thread-id>     # Resume a specific thread
leonai --model gpt-4o           # Use a specific model
leonai --workspace /path/to/dir # Set working directory
```

### Thread Management

```bash
leonai thread ls                          # List all conversations
leonai thread history <thread-id>         # View conversation history
leonai thread rewind <thread-id> <cp-id>  # Rewind to checkpoint
leonai thread rm <thread-id>              # Delete a thread
```

### Non-interactive Mode

```bash
leonai run "Explain this codebase"            # Single message
echo "Summarize this" | leonai run --stdin    # Read from stdin
leonai run -i                                  # Interactive without TUI
```

---

## LLM Provider Setup

Mycel uses the OpenAI-compatible API format. Any provider that speaks this protocol works out of the box. The examples below apply to both the CLI (`~/.leon/config.env`) and the Web UI (Settings page).

### Provider Examples

#### OpenAI

```
API_KEY:    sk-...
BASE_URL:   https://api.openai.com/v1
MODEL_NAME: gpt-4o
```

#### Anthropic Claude (via OpenAI-compatible proxy)

Claude models are accessed through an OpenAI-compatible proxy such as OpenRouter:

```
API_KEY:    sk-or-...
BASE_URL:   https://openrouter.ai/api/v1
MODEL_NAME: claude-sonnet-4-5-20250929
```

#### DeepSeek

```
API_KEY:    sk-...
BASE_URL:   https://api.deepseek.com/v1
MODEL_NAME: deepseek-chat
```

#### OpenRouter

OpenRouter provides access to many models through a single API:

```
API_KEY:    sk-or-...
BASE_URL:   https://openrouter.ai/api/v1
MODEL_NAME: anthropic/claude-sonnet-4-5-20250929
```

### Configuration Precedence

Environment variables override `~/.leon/config.env`:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
```

---

## Sandbox Management

Mycel supports multiple sandbox providers for isolated code execution. Configure them by placing JSON files in `~/.leon/sandboxes/`.

```bash
leonai sandbox              # Open sandbox manager TUI
leonai sandbox ls           # List active sessions
leonai sandbox new docker   # Create a new Docker session
leonai sandbox metrics <id> # View resource usage
```

Supported providers: Docker, AgentBay, E2B, Daytona.

## Next Steps

- [Multi-Agent Chat](multi-agent-chat.md) -- The Entity-Chat system for human-agent and agent-agent communication
- [Sandbox Configuration](SANDBOX.md) -- Set up sandboxed execution environments
- [Troubleshooting](TROUBLESHOOTING.md) -- Common issues and solutions
