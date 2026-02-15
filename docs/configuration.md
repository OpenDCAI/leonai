# Leon Configuration System

Leon uses a three-tier configuration system with JSON files, providing flexible control over agent behavior, tools, and runtime settings.

## Quick Start

```bash
# Use default configuration
leonai

# Use a specific agent preset
leonai --agent coder
leonai --agent researcher

# Override model
leonai --model claude-opus-4-6
leonai --model leon:powerful

# View current configuration
leonai config show
```

## Configuration Tiers

Configuration is loaded and merged from three levels (highest priority first):

1. **Project Config**: `.leon/config.json` in workspace root
2. **User Config**: `~/.leon/config.json` in home directory
3. **System Defaults**: Built-in presets (`default`, `coder`, `researcher`, `tester`)

### Merge Strategy

- **API/Memory/Tools**: Deep merge (all tiers combined, later overrides earlier)
- **MCP/Skills**: Lookup (first found wins, no merge)
- **System Prompt**: Lookup (project > user > system)

## Configuration Structure

```json
{
  "api": {
    "model": "claude-sonnet-4-5-20250929",
    "model_provider": null,
    "api_key": null,
    "base_url": null,
    "temperature": 0.5,
    "max_tokens": 8192,
    "model_kwargs": {},
    "context_limit": 100000,
    "enable_audit_log": true,
    "allowed_extensions": null,
    "block_dangerous_commands": true,
    "block_network_commands": false,
    "queue_mode": "steer"
  },
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 10,
      "trim_tool_results": true,
      "max_tool_result_length": 5000
    },
    "compaction": {
      "enabled": true,
      "trigger_ratio": 0.8,
      "min_messages": 20
    }
  },
  "tools": {
    "filesystem": { "enabled": true, "tools": {...} },
    "search": { "enabled": true, "tools": {...} },
    "web": { "enabled": true, "tools": {...} },
    "command": { "enabled": true, "tools": {...} }
  },
  "mcp": {
    "enabled": true,
    "servers": {}
  },
  "skills": {
    "enabled": true,
    "paths": ["./skills"],
    "skills": {}
  },
  "system_prompt": null
}
```

## API Configuration

### Basic Settings

```json
{
  "api": {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.5,
    "max_tokens": 8192
  }
}
```

### Provider Configuration

For OpenAI-compatible proxies:

```json
{
  "api": {
    "model": "claude-opus-4-6",
    "model_provider": "openai",
    "base_url": "https://api.example.com/v1",
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

### Security Settings

```json
{
  "api": {
    "enable_audit_log": true,
    "allowed_extensions": ["py", "js", "ts", "md"],
    "block_dangerous_commands": true,
    "block_network_commands": false
  }
}
```

### Queue Mode

Controls message processing priority:

- `steer`: User messages take priority
- `followup`: Agent follow-up messages take priority
- `collect`: Batch process all messages
- `steer_backlog`: Process backlog before user messages
- `interrupt`: Interrupt current processing

```json
{
  "api": {
    "queue_mode": "steer"
  }
}
```

## Virtual Model Mapping

Leon provides virtual model names for easy switching:

| Virtual Name | Actual Model | Temperature | Max Tokens | Use Case |
|--------------|--------------|-------------|------------|----------|
| `leon:fast` | claude-sonnet-4-5 | 0.7 | 4096 | Simple tasks |
| `leon:balanced` | claude-sonnet-4-5 | 0.5 | 8192 | General use |
| `leon:powerful` | claude-opus-4-6 | 0.3 | 16384 | Complex reasoning |
| `leon:coding` | claude-opus-4-6 | 0.0 | 16384 | Code generation |
| `leon:research` | claude-sonnet-4-5 | 0.3 | 8192 | Research |
| `leon:creative` | claude-sonnet-4-5 | 0.9 | 8192 | Creative tasks |

Usage:

```bash
leonai --model leon:coding
leonai --model leon:research
```

In config:

```json
{
  "api": {
    "model": "leon:powerful"
  }
}
```

## Memory Configuration

### Pruning

Automatically trim old messages to stay within context limits:

```json
{
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 10,
      "trim_tool_results": true,
      "max_tool_result_length": 5000
    }
  }
}
```

- `keep_recent`: Number of recent messages to always keep
- `trim_tool_results`: Truncate large tool outputs
- `max_tool_result_length`: Max characters for tool results

### Compaction

Compress conversation history using LLM summarization:

```json
{
  "memory": {
    "compaction": {
      "enabled": true,
      "trigger_ratio": 0.8,
      "min_messages": 20
    }
  }
}
```

- `trigger_ratio`: Trigger at 80% of context limit
- `min_messages`: Minimum messages before compaction

## Tools Configuration

### Filesystem Tools

```json
{
  "tools": {
    "filesystem": {
      "enabled": true,
      "tools": {
        "read_file": {
          "enabled": true,
          "max_file_size": 10485760
        },
        "write_file": true,
        "edit_file": true,
        "multi_edit": true,
        "list_dir": true
      }
    }
  }
}
```

### Search Tools

```json
{
  "tools": {
    "search": {
      "enabled": true,
      "max_results": 50,
      "tools": {
        "grep_search": {
          "enabled": true,
          "max_file_size": 10485760
        },
        "find_by_name": true
      }
    }
  }
}
```

### Web Tools

```json
{
  "tools": {
    "web": {
      "enabled": true,
      "timeout": 15,
      "tools": {
        "web_search": {
          "enabled": true,
          "max_results": 5,
          "tavily_api_key": "${TAVILY_API_KEY}",
          "exa_api_key": null,
          "firecrawl_api_key": null
        },
        "read_url_content": {
          "enabled": true,
          "jina_api_key": "${JINA_API_KEY}"
        },
        "view_web_content": true
      }
    }
  }
}
```

### Command Tools

```json
{
  "tools": {
    "command": {
      "enabled": true,
      "tools": {
        "run_command": {
          "enabled": true,
          "default_timeout": 120
        },
        "command_status": true
      }
    }
  }
}
```

## MCP Configuration

Configure Model Context Protocol servers:

```json
{
  "mcp": {
    "enabled": true,
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
        "env": {}
      },
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_TOKEN": "${GITHUB_TOKEN}"
        }
      }
    }
  }
}
```

## Skills Configuration

```json
{
  "skills": {
    "enabled": true,
    "paths": ["./skills", "~/.leon/skills"],
    "skills": {
      "code-review": true,
      "git-workflow": true,
      "debugging": false
    }
  }
}
```

## Environment Variables

All string values support environment variable expansion:

```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL}"
  },
  "tools": {
    "web": {
      "tools": {
        "web_search": {
          "tavily_api_key": "${TAVILY_API_KEY}"
        }
      }
    }
  }
}
```

Supported formats:
- `${VAR}`: Environment variable
- `~`: Home directory expansion

### Environment Variable Prefix

You can also use the `LEON__` prefix for nested configuration:

```bash
export LEON__API__MODEL=claude-opus-4-6
export LEON__API__TEMPERATURE=0.3
export LEON__TOOLS__COMMAND__ENABLED=false
```

Use double underscore (`__`) for nesting.

## Agent Presets

Leon includes four built-in agent presets:

### Default Agent

Balanced configuration for general use:

```bash
leonai --agent default
```

- Model: claude-sonnet-4-5
- All tools enabled
- Standard security settings

### Coder Agent

Optimized for software development:

```bash
leonai --agent coder
```

- Model: claude-opus-4-6 (temperature 0.0)
- All tools enabled including command execution
- Multi-edit support
- Larger context window (200k tokens)
- System prompt focused on clean code and best practices

### Researcher Agent

Optimized for information gathering:

```bash
leonai --agent researcher
```

- Model: claude-sonnet-4-5 (temperature 0.3)
- Command execution disabled (read-only)
- Enhanced web search (10 results)
- Larger file size limits (20MB)
- System prompt focused on research and analysis

### Tester Agent

Optimized for testing and QA:

```bash
leonai --agent tester
```

- Model: claude-sonnet-4-5
- All tools enabled
- System prompt focused on test coverage and quality

## Configuration Examples

### Project-Specific Config

`.leon/config.json` in your project:

```json
{
  "api": {
    "model": "leon:coding",
    "allowed_extensions": ["py", "js", "ts", "json", "yaml"]
  },
  "system_prompt": "You are a Python expert working on a FastAPI project. Follow PEP 8 and use type hints.",
  "tools": {
    "web": {
      "enabled": false
    }
  }
}
```

### User Global Config

`~/.leon/config.json`:

```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL}",
    "model_provider": "openai"
  },
  "tools": {
    "web": {
      "tools": {
        "web_search": {
          "tavily_api_key": "${TAVILY_API_KEY}"
        }
      }
    }
  },
  "mcp": {
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_TOKEN": "${GITHUB_TOKEN}"
        }
      }
    }
  }
}
```

### Research-Only Agent

Disable code execution for safe research:

```json
{
  "api": {
    "model": "leon:research"
  },
  "tools": {
    "command": {
      "enabled": false
    },
    "filesystem": {
      "tools": {
        "write_file": false,
        "edit_file": false
      }
    },
    "web": {
      "tools": {
        "web_search": {
          "max_results": 20
        }
      }
    }
  }
}
```

## CLI Overrides

Command-line arguments override all configuration:

```bash
# Override model
leonai --model claude-opus-4-6

# Override workspace
leonai --workspace /path/to/project

# Override agent preset
leonai --agent coder

# Combine overrides
leonai --agent researcher --model leon:powerful
```

## Hot Reloading

Configuration changes are applied on next agent initialization. For immediate effect:

1. Exit current session (Ctrl+D)
2. Restart leonai
3. Configuration is reloaded automatically

## Troubleshooting

### API Key Not Found

**Error**: `No API key found`

**Solution**: Set environment variable or add to config:

```bash
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

Or in `~/.leon/config.json`:

```json
{
  "api": {
    "api_key": "sk-..."
  }
}
```

### Invalid Model Name

**Error**: `Unknown virtual model: leon:xyz`

**Solution**: Use valid virtual model names or actual model names:

```bash
leonai --model leon:balanced  # Valid
leonai --model claude-opus-4-6  # Valid
```

### Configuration Not Loading

**Issue**: Changes not taking effect

**Solution**:
1. Check file location (`.leon/config.json` in workspace or `~/.leon/config.json`)
2. Validate JSON syntax (use `jq . < config.json`)
3. Restart leonai
4. Check merge priority (project > user > system)

### Tool Not Available

**Issue**: Tool not showing up

**Solution**: Check tool is enabled in config:

```json
{
  "tools": {
    "web": {
      "enabled": true,
      "tools": {
        "web_search": {
          "enabled": true
        }
      }
    }
  }
}
```

### MCP Server Not Starting

**Issue**: MCP tools not available

**Solution**:
1. Check command is valid: `npx -y @modelcontextprotocol/server-filesystem`
2. Check environment variables are set
3. Enable debug logging: `leonai --verbose`

## Schema Reference

Full JSON schema available at: `config/schema.py`

Key types:
- `LeonSettings`: Root configuration object
- `APIConfig`: API and model settings
- `MemoryConfig`: Memory management settings
- `ToolsConfig`: Tool enable/disable settings
- `MCPConfig`: MCP server configurations
- `SkillsConfig`: Skills system settings

## Best Practices

1. **Use Virtual Models**: Prefer `leon:*` names for portability
2. **Environment Variables**: Never commit API keys, use `${VAR}` syntax
3. **Project Config**: Keep project-specific settings in `.leon/config.json`
4. **User Config**: Keep personal API keys in `~/.leon/config.json`
5. **Agent Presets**: Start with presets, customize as needed
6. **Security**: Enable audit logging and command blocking in production
7. **Memory**: Tune pruning/compaction based on conversation length
8. **Tools**: Disable unused tools to reduce token usage

## See Also

- [Migration Guide](migration-guide.md) - Migrating from profile.yaml
- [Sandbox Documentation](SANDBOX.md) - Sandbox configuration
- [Skills System](../skills/README.md) - Creating custom skills
- [MCP Integration](../mcp/README.md) - MCP server setup
