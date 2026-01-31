# Leon CLI Usage

## Quick Start

```bash
# Start Leon
leonai

# Or with uv
uv run leonai
```

## Commands

```bash
leonai                    # Start TUI
leonai --profile <path>   # Use specific profile
leonai --workspace <dir>  # Set workspace directory
leonai --thread <id>      # Resume specific conversation
leonai config             # Configure API key
leonai config show        # Show current configuration
```

## Configuration

### API Key Setup

```bash
leonai config
```

Or set environment variables:

```bash
export ANTHROPIC_API_KEY="your-api-key"
# Or for OpenAI-compatible proxy
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://your-proxy.com/v1"
```

## TUI Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Ctrl+Up/Down | Browse history |
| Ctrl+Y | Copy last message |
| Ctrl+E | Export conversation |
| Ctrl+L | Clear history |
| Ctrl+T | Switch thread |
| Ctrl+C | Exit |

## Features

- Streaming output with Markdown rendering
- Tool call visualization
- Conversation history navigation
- Thread persistence and resume
- Workspace isolation
