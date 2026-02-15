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

### Provider Auto-Detection

Leon automatically detects the model provider based on which API key environment variable is set:

**Priority**: `ANTHROPIC_API_KEY` > `OPENAI_API_KEY` > `OPENROUTER_API_KEY`

```bash
# Use Anthropic format (supports prompt caching)
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_BASE_URL=https://api.anthropic.com
export MODEL=claude-sonnet-4-5-20250929

# Use OpenAI format
export OPENAI_API_KEY=sk-xxx
export OPENAI_BASE_URL=https://api.openai.com
export MODEL=gpt-4o

# Use OpenRouter
export OPENROUTER_API_KEY=sk-or-xxx
export OPENAI_BASE_URL=https://openrouter.ai/api
export MODEL=anthropic/claude-3.5-sonnet
```

The system will:
1. Detect which API key is set
2. Automatically set `model_provider` (anthropic/openai)
3. Create the correct ChatModel instance (ChatAnthropic/ChatOpenAI)

**Note**: Environment variable detection overrides config file settings, allowing easy switching between providers.

### Base URL Normalization

Leon automatically normalizes `base_url` based on the provider to handle different API conventions:

- **OpenAI/OpenRouter**: Adds `/v1` suffix if not present
  - User config: `https://api.openai.com` or `https://api.openai.com/v1`
  - Actual usage: `https://api.openai.com/v1`

- **Anthropic**: Removes `/v1` suffix (SDK adds `/v1/messages` automatically)
  - User config: `https://api.anthropic.com` or `https://api.anthropic.com/v1`
  - Actual usage: `https://api.anthropic.com`

**Example with proxy**:

```json
{
  "api": {
    "model": "claude-haiku-4-5-20251001",
    "base_url": "https://proxy.example.com"
  }
}
```

You don't need to worry about the `/v1` suffix - the system handles it automatically based on the detected provider.

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

### Example 1: Local Development Setup

Perfect for local development with all tools enabled:

`.leon/config.json` in your project:

```json
{
  "api": {
    "model": "leon:coding",
    "temperature": 0.0,
    "allowed_extensions": ["py", "js", "ts", "json", "yaml", "md"]
  },
  "system_prompt": "You are a Python expert working on a FastAPI project. Follow PEP 8 and use type hints.",
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
        "multi_edit": true
      }
    },
    "command": {
      "enabled": true,
      "tools": {
        "run_command": {
          "enabled": true,
          "default_timeout": 120
        }
      }
    },
    "web": {
      "enabled": false
    }
  },
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 10
    },
    "compaction": {
      "enabled": true,
      "trigger_ratio": 0.8
    }
  }
}
```

**Use case**: Working on a local codebase where you need full file system and command access but don't need web search.

### Example 2: Production Deployment

Secure configuration for production environments:

`~/.leon/config.json`:

```json
{
  "api": {
    "model": "claude-opus-4-6",
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL}",
    "model_provider": "openai",
    "temperature": 0.3,
    "enable_audit_log": true,
    "allowed_extensions": ["py", "js", "ts", "json", "yaml"],
    "block_dangerous_commands": true,
    "block_network_commands": true
  },
  "tools": {
    "filesystem": {
      "enabled": true,
      "tools": {
        "read_file": {
          "enabled": true,
          "max_file_size": 5242880
        },
        "write_file": false,
        "edit_file": false
      }
    },
    "command": {
      "enabled": false
    },
    "web": {
      "enabled": false
    }
  },
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 5,
      "trim_tool_results": true,
      "max_tool_result_length": 3000
    }
  }
}
```

**Use case**: Production environment where you need read-only access with strict security controls.

### Example 3: Testing Environment

Configuration optimized for running tests:

`.leon/config.json`:

```json
{
  "api": {
    "model": "leon:balanced",
    "temperature": 0.5
  },
  "tools": {
    "filesystem": {
      "enabled": true
    },
    "command": {
      "enabled": true,
      "tools": {
        "run_command": {
          "enabled": true,
          "default_timeout": 300
        }
      }
    },
    "web": {
      "enabled": false
    }
  },
  "system_prompt": "You are a testing expert. Focus on test coverage, edge cases, and quality assurance."
}
```

**Use case**: Running automated tests where you need longer timeouts and balanced model performance.

### Example 4: Research-Only Agent

Disable code execution for safe research:

```json
{
  "api": {
    "model": "leon:research",
    "temperature": 0.3
  },
  "tools": {
    "command": {
      "enabled": false
    },
    "filesystem": {
      "enabled": true,
      "tools": {
        "read_file": {
          "enabled": true,
          "max_file_size": 20971520
        },
        "write_file": false,
        "edit_file": false
      }
    },
    "web": {
      "enabled": true,
      "tools": {
        "web_search": {
          "enabled": true,
          "max_results": 20,
          "tavily_api_key": "${TAVILY_API_KEY}"
        }
      }
    }
  }
}
```

**Use case**: Research tasks where you need web access and file reading but no code execution.

### Example 5: Multi-Environment Setup

User global config with API credentials:

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
        },
        "read_url_content": {
          "jina_api_key": "${JINA_API_KEY}"
        }
      }
    }
  },
  "mcp": {
    "enabled": true,
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

Project-specific overrides:

`.leon/config.json`:

```json
{
  "api": {
    "model": "leon:powerful",
    "temperature": 0.0
  },
  "system_prompt": "You are working on a critical production system. Be extra careful with changes."
}
```

**Use case**: Keep credentials in user config, override model and behavior per project.

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

### Common Issues and Solutions

#### 1. API Key Not Found

**Error**: `No API key found. Set LEON__API__API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY environment variable.`

**Cause**: No API key configured in environment or config file.

**Solution**:

Option A - Environment variable:
```bash
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

Option B - User config (`~/.leon/config.json`):
```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Verification**:
```bash
leonai config show  # Check if API key is loaded
```

#### 2. Invalid Model Name

**Error**: `Unknown virtual model: leon:xyz`

**Cause**: Using a virtual model name that doesn't exist in the mapping.

**Valid virtual models**:
- `leon:fast` → claude-sonnet-4-5 (temp 0.7, 409kens)
- `leon:balanced` → claude-sonnet-4-5 (temp 0.5, 8192 tokens)
- `leon:powerful` → claude-opus-4-6 (temp 0.3, 16384 tokens)
- `leon:coding` → claude-opus-4-6 (temp 0.0, 16384 tokens)
- `leon:research` → claude-sonnet-4-5 (temp 0.3, 8192 tokens)
- `leon:creative` → claude-sonnet-4-5 (temp 0.9, 8192 tokens)

**Solution**:
```bash
leonai --model leon:balanced  # Use valid virtual name
leonai --model claude-opus-4-6  # Or use actual model name
```

#### 3. Configuration Not Loading

**Issue**: Changes to config.json not taking effect

**Cause**: JSON syntax error, wrong file location, or config not reloade*Solution**:

Step 1 - Validate JSON syntax:
```bash
jq . < ~/.leon/config.json  # Should output formatted JSON
jq . < .leon/config.json    # Check project config too
```

Step 2 - Check file location:
```bash
ls -la ~/.leon/config.json      # User config
ls -la .leon/config.json        # Project config
```

Step 3 - Verify config is loaded:
```bash
leonai config show  # View merged configuration
```

Step 4 - Restart Leon:
```bash
# Exit current session (Ctrl+D)
leonai  # Start fresh
```

**Remember**: Configuration priority is Project > User > System. Project config overrides user config.

#### 4. Tool Not Available

**Issue**: Expected tool not showing up in agent

**Cause**: Tool disabled in configuration or parent middleware disabled.

**Solution**:

Check tool hierarchy - both parent and child must be enabled:

```json
{
  "tools": {
    "web": {
      "enabled": true,  // Parent must be enabled
      "tools": {
        "web_search": {
          "enabled": true  // Child must be enabled
        }
      }
    }
  }
}
```

**Verification**:
```bash
leonai config show | grep -A 10 "web"
```

#### 5. MCP Server Not Starting

**Issue**: MCP tools not available, server fails to start

**Cause**: Invalid command, missing dependencies, or environment variables not set.

**Solution**:

Step 1 - Test command manually:
```bash
npx -y @modelcontextprotocol/server-github
# Should start without errors
```

Step 2 - Check environment variables:
```bash
echo $GITHUB_TOKEN  # Should output token
```

Step 3 - Enable verbose logging:
```bash
leonai --verbose
# Look for MCP server startup messages
```

Step 4 - Verify config:
```json
{
  "mcp": {
    "enabled": true,
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

#### 6. Base URL Not Working with Proxy

**Issue**: Using OpenAI-compatible proxy but getting connection errors

**Cause**: Missing `/v1` suffix or incorrect provider setting.

**Solution**:

For OpenAI-compatible proxies serving Claude:
```json
{
  "api": {
    "model": "claude-opus-4-6",
    "model_provider": "openai",  // Must set to "openai"
    "base_url": "https://api.example.com/v1",  // Must end with /v1
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Note**: The schema automatically adds `/v1` if missing, but explicit provider is required.

#### 7. Memory Issues - Context Too Large

**Issue**: Agent runs out of context, messages getting truncated

**Cause**: Long conversation exceeding context limit.

**Solution**:

Enable aggressive pruning and compaction:
```json
{
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 5,  // Keep fewer messages
      "trim_tool_results": true,
      "max_tool_result_length": 3000  // Smaller limit
    },
    "compaction": {
      "enabled": true,
      "trigger_ratio": 0.7,  // Trigger earlier
      "min_messages": 15  // Compact sooner
    }
  }
}
```

#### 8. File Size Limit Exceeded

**Issue**: Cannot read large files

**Cause**: File exceeds max_file_size limit.

**Solution**:

Increase file size limit:
```json
{
  "tools": {
    "filesystem": {
      "tools": {
        "read_file": {
          "enabled": true,
          "max_file_size": 20971520  // 20MB instead of 10MB
        }
      }
    }
  }
}
```

**Warning**: Larger files consume more tokens and may hit context limits.

#### 9. Command Timeout

**Issue**: Long-running commands getting killed

**Cause**: Command exceeds default timeout (120 seconds).

**Solution**:

Increase timeout:
```json
{
  "tools": {
    "command": {
      "tools": {
        "run_command": {
          "enabled": true,
          "default_timeout": 300  // 5 minutes
        }
      }
    }
  }
}
```

#### 10. Environment Variables Not Expanding

**Issue**: `${VAR}` not being replaced with actual value

**Cause**: Environment variable not set or typo in variable name.

**Solution**:

Step 1 - Verify variable is set:
```bash
echo $OPENAI_API_KEY  # Should output value
```

Step 2 - Check config syntax:
```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}"  // Correct
    // NOT: "api_key": "$OPENAI_API_KEY"  // Wrong
  }
}
```

Step 3 - Verify expansion:
```bash
leonai config show  # Should show actual value, not ${VAR}
```

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

### 1. Use Virtual Models for Portability

Virtual models make it easy to switch between different model configurations without changing your code:

```json
{
  "api": {
    "model": "leon:coding"  // Easy to switch to leon:research later
  }
}
```

**Benefits**:
- Switch models without remembering exact names
- Consistent temperature/token settings per use case
- Easy to update all projects when new models release

### 2. Never Commit API Keys

Always use environment variables for sensitive data:

**Bad** ❌:
```json
{
  "api": {
    "api_key": "sk-ant-api03-actual-key-here"
  }
}
```

**Good** ✅:
```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

Add `.leon/config.json` to `.gitignore` if it contains secrets, or use `~/.leon/config.json` for credentials.

### 3. Separate Project and User Configs

**User config** (`~/.leon/config.json`) - API credentials and personal preferences:
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
  }
}
```

**Project config** (`.leon/config.json`) - Project-specific settings:
```json
{
  "api": {
    "model": "leon:coding",
    "allowed_extensions": ["py", "js", "ts"]
  },
  "system_prompt": "You are working on a FastAPI project. Follow PEP 8."
}
```

**Benefits**:
- Credentials stay in user config (not committed)
- Project settings can be shared with team
- Easy to work on multiple projects

### 4. Start with Agent Presets

Use built-in presets as starting points:

```bash
leonai --agent coder      # For development
leonai --agent researcher # For research
leonai --agent tester     # For testing
```

Then customize only what you need:
```json
{
  "api": {
    "temperature": 0.1  // Slightly more deterministic than default
  }
}
```

**Benefits**:
- Proven configurations for common use cases
- Less configuration to maintain
- Easy to understand what changed

### 5. Enable Security Features in Production

Always enable audit logging and command blocking:

```json
{
  "api": {
    "enable_audit_log": true,
    "allowed_extensions": ["py", "js", "ts", "json", "yaml"],
    "block_dangerous_commands": true,
    "block_network_commands": true
  }
}
```

**What this protects against**:
- Accidental file deletions (`rm -rf`)
- Unauthorized network access
- Execution of dangerous system commands
- Access to sensitive file types

### 6. Tune Memory Settings Based on Usage

**Short conversations** (< 20 messages):
```json
{
  "memory": {
    "pruning": {
      "enabled": false  // No need to prune
    },
    "compaction": {
      "enabled": false  // No need to compact
    }
  }
}
```

**Long conversations** (> 50 messages):
```json
{
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 10,
      "trim_tool_results": true,
      "max_tool_result_length": 3000
    },
    "compaction": {
      "enabled": true,
      "trigger_ratio": 0.7,  // Compact earlier
      "min_messages": 15
    }
  }
}
```

### 7. Disable Unused Tools to Reduce Token Usage

Every enabled tool adds to the system prompt. Disable tools you don't need:

```json
{
  "tools": {
    "web": {
      "enabled": false  // Disable if no internet access needed
    },
    "command": {
      "enabled": false  // Disable if read-only access sufficient
    }
  }
}
```

**Token savings**: ~200-500 tokens per disabled middleware.

### 8. Use Appropriate File Size Limits

**Default** (10MB):
```json
{
  "tools": {
    "filesystem": {
      "tools": {
        "read_file": {
          "max_file_size": 10485760
        }
      }
    }
  }
}
```

**For large codebases** (20MB):
```json
{
  "tools": {
    "filesystem": {
      "tools": {
        "read_file": {
          "max_file_size": 20971520
        }
      }
    }
  }
}
```

**For restricted environments** (5MB):
```json
{
  "tools": {
    "filesystem": {
      "tools": {
        "read_file": {
          "max_file_size": 5242880
        }
      }
    }
  }
}
```

### 9. Configure Timeouts Based on Task Type

**Quick tasks** (default 120s):
```json
{
  "tools": {
    "command": {
      "tools": {
        "run_command": {
          "default_timeout": 120
        }
      }
    }
  }
}
```

**Long-running tasks** (tests, builds):
```json
{
  "tools": {
    "command": {
      "tools": {
        "run_command": {
          "default_timeout": 600  // 10 minutes
        }
      }
    }
  }
}
```

### 10. Document Your Configuration

Add comments to your config (use a separate README if JSON doesn't support comments):

**config-notes.md**:
```markdown
# Leon Configuration Notes

## Model Choice
Using leon:coding for deterministic code generation (temp=0.0)

## Security
- Dangerous commands blocked for safety
- Only Python/JS/TS files allowed
- Audit log enabled for compliance

## Memory
- Aggressive pruning (keep_recent=5) due to long conversations
- Early compaction (trigger_ratio=0.7) to avoid context limits
```

## See Also

- [Migration Guide](migration-guide.md) - Migrating from profile.yaml
- [Sandbox Documentation](SANDBOX.md) - Sandbox configuration
- [Skills System](../skills/README.md) - Creating custom skills
- [MCP Integration](../mcp/README.md) - MCP server setup
