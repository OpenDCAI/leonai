# Migration Guide: profile.yaml → config.json

This guide helps you migrate from the old `profile.yaml` format to the new `config.json` configuration system.

## Why Migrate?

The new configuration system provides:

- **Three-tier merging**: System defaults + User config + Project config
- **Virtual model mapping**: Use `leon:*` names for easy model switching
- **Better validation**: Pydantic schema validation catches errors early
- **Environment variable support**: `${VAR}` expansion in all string fields
- **Agent presets**: Built-in configurations for common use cases
- **Cleaner structure**: Nested configuration groups

## Quick Migration

### Old Format (profile.yaml)

```yaml
agent:
  model: "claude-sonnet-4-5-20250929"
  model_provider: "openai"
  base_url: "https://api.example.com/v1"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.5
  max_tokens: 8192
  workspace_root: null
  enable_audit_log: true

tool:
  filesystem:
    enabled: true
    tools:
      read_file:
        enabled: true
        max_file_size: 10485760
      write_file: true
      edit_file: true
  web:
    enabled: true
    tools:
      web_search:
        enabled: true
        tavily_api_key: ${TAVILY_API_KEY}

mcp:
  enabled: true
  servers:
    github:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}

skills:
  enabled: true
  paths:
    - ./skills
```

### New Format (config.json)

```json
{
  "api": {
    "model": "claude-sonnet-4-5-20250929",
    "model_provider": "openai",
    "base_url": "https://api.example.com/v1",
    "api_key": "${OPENAI_API_KEY}",
    "temperature": 0.5,
    "max_tokens": 8192,
    "enable_audit_log": true
  },
  "tools": {
    "filesystem": {
      "enabled": true,
      "tools": {
        "read_file": {
          "enabled": true,
          "max_file_size": 10485760
        },
        "write_file": true,
        "edit_file": true
      }
    },
    "web": {
      "enabled": true,
      "tools": {
        "web_search": {
          "enabled": true,
          "tavily_api_key": "${TAVILY_API_KEY}"
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
  },
  "skills": {
    "enabled": true,
    "paths": ["./skills"]
  }
}
```

## Field Mapping

### Top-Level Changes

| Old (profile.yaml) | New (config.json) | Notes |
|-------------------|-------------------|-------|
| `agent:` | `api:` | Renamed for clarity |
| `tool:` | `tools:` | Pluralized |
| `mcp:` | `mcp:` | No change |
| `skills:` | `skills:` | No change |

### API Configuration

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `agent.model` | `api.model` | Moved to `api` group |
| `agent.model_provider` | `api.model_provider` | Moved to `api` group |
| `agent.base_url` | `api.base_url` | Moved to `api` group |
| `agent.api_key` | `api.api_key` | Moved to `api` group |
| `agent.temperature` | `api.temperature` | Moved to `api` group |
| `agent.max_tokens` | `api.max_tokens` | Moved to `api` group |
| `agent.model_kwargs` | `api.model_kwargs` | Moved to `api` group |
| `agent.context_limit` | `api.context_limit` | Moved to `api` group |
| `agent.enable_audit_log` | `api.enable_audit_log` | Moved to `api` group |
| `agent.allowed_extensions` | `api.allowed_extensions` | Moved to `api` group |
| `agent.block_dangerous_commands` | `api.block_dangerous_commands` | Moved to `api` group |
| `agent.block_network_commands` | `api.block_network_commands` | Moved to `api` group |
| `agent.queue_mode` | `api.queue_mode` | Moved to `api` group |
| `agent.workspace_root` | `workspace_root` | Moved to root level |

### Memory Configuration

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `agent.memory` | `memory` | Moved to root level |
| `agent.memory.pruning` | `memory.pruning` | Structure unchanged |
| `agent.memory.compaction` | `memory.compaction` | Structure unchanged |

### Tools Configuration

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `tool.filesystem` | `tools.filesystem` | Pluralized |
| `tool.search` | `tools.search` | Pluralized |
| `tool.web` | `tools.web` | Pluralized |
| `tool.command` | `tools.command` | Pluralized |

### System Prompt

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `agent.system_prompt` | `system_prompt` | Moved to root level |

## Step-by-Step Migration

### Step 1: Backup Old Configuration

```bash
cp ~/.leon/profile.yaml ~/.leon/profile.yaml.backup
```

### Step 2: Convert to JSON

Use this Python script to convert:

```python
import json
import yaml
from pathlib import Path

# Read old config
old_config = yaml.safe_load(Path("~/.leon/profile.yaml").expanduser().read_text())

# Convert to new format
new_config = {
    "api": {
        "model": old_config.get("agent", {}).get("model"),
        "model_provider": old_config.get("agent", {}).get("model_provider"),
        "base_url": old_config.get("agent", {}).get("base_url"),
        "api_key": old_config.get("agent", {}).get("api_key"),
        "temperature": old_config.get("agent", {}).get("temperature"),
        "max_tokens": old_config.get("agent", {}).get("max_tokens"),
        "model_kwargs": old_config.get("agent", {}).get("model_kwargs", {}),
        "context_limit": old_config.get("agent", {}).get("context_limit", 100000),
        "enable_audit_log": old_config.get("agent", {}).get("enable_audit_log", True),
        "allowed_extensions": old_config.get("agent", {}).get("allowed_extensions"),
        "block_dangerous_commands": old_config.get("agent", {}).get("block_dangerous_commands", True),
        "block_network_commands": old_config.get("agent", {}).get("block_network_commands", False),
        "queue_mode": old_config.get("agent", {}).get("queue_mode", "steer"),
    },
    "memory": old_config.get("agent", {}).get("memory", {}),
    "tools": old_config.get("tool", {}),
    "mcp": old_config.get("mcp", {}),
    "skills": old_config.get("skills", {}),
    "system_prompt": old_config.get("agent", {}).get("system_prompt"),
    "workspace_root": old_config.get("agent", {}).get("workspace_root"),
}

# Remove None values
def remove_none(obj):
    if isinstance(obj, dict):
        return {k: remove_none(v) for k, v in obj.items() if v is not None}
    return obj

new_config = remove_none(new_config)

# Write new config
Path("~/.leon/config.json").expanduser().write_text(json.dumps(new_config, indent=2))
print("Migration complete! New config saved to ~/.leon/config.json")
```

### Step 3: Validate New Configuration

```bash
# Test the new configuration
leonai config show

# Start Leon to verify it works
leonai
```

### Step 4: Remove Old Configuration (Optional)

Once verified, you can remove the old file:

```bash
rm ~/.leon/profile.yaml
```

## Common Migration Issues

### Issue 1: YAML to JSON Syntax

**Problem**: YAML allows unquoted strings, JSON requires quotes

**YAML**:
```yaml
model: claude-sonnet-4-5-20250929
```

**JSON**:
```json
{
  "model": "claude-sonnet-4-5-20250929"
}
```

**Validation**:
```bash
jq . < ~/.leon/config.json  # Should output formatted JSON without errors
```

### Issue 2: Boolean Values

**Problem**: YAML uses `true`/`false`, JSON uses `true`/`false` (same, but watch for YAML's `yes`/`no`)

**YAML**:
```yaml
enabled: yes  # or true
```

**JSON**:
```json
{
  "enabled": true
}
```

**Common mistake**: Using `"true"` (string) instead of `true` (boolean)

### Issue 3: Null Values

**Problem**: YAML uses `null` or `~`, JSON uses `null`

**YAML**:
```yaml
api_key: null
workspace_root: ~
```

**JSON**:
```json
{
  "api_key": null,
  "workspace_root": null
}
```

**Note**: In JSON, `null` is unquoted. `"null"` is a string, not null.

### Issue 4: Lists/Arrays

**Problem**: YAML uses `-` for lists, JSON uses `[]`

**YAML**:
```yaml
paths:
  - ./skills
  - ~/.leon/skills
```

**JSON**:
```json
{
  "paths": ["./skills", "~/.leon/skills"]
}
```

**Common mistake**: Forgetting commas between array elements.

### Issue 5: Environment Variables

**Problem**: Both support `${VAR}`, but ensure proper quoting in JSON

**YAML**:
```yaml
api_key: ${OPENAI_API_KEY}
```

**JSON**:
```json
{
  "api_key": "${OPENAI_API_KEY}"
}
```

**Verification**:
```bash
leonai config show  # Should show expanded value, not ${VAR}
```

### Issue 6: Trailing Commas

**Problem**: JSON doesn't allow trailing commas, YAML doesn't care

**Invalid JSON** ❌:
```json
{
  "api": {
    "model": "claude-opus-4-6",
    "temperature": 0.5,  // ← Trailing comma causes error
  }
}
```

**Valid JSON** ✅:
```json
{
  "api": {
    "model": "claude-opus-4-6",
    "temperature": 0.5
  }
}
```

### Issue 7: Comments Not Supported

**Problem**: JSON doesn't support comments, YAML does

**YAML** (works):
```yaml
agent:
  model: claude-opus-4-6  # Using Opus for complex tasks
```

**JSON** (doesn't work):
```json
{
  "api": {
    "model": "claude-opus-4-6"  // This breaks JSON parsing
  }
}
```

**Solution**: Remove comments or use a separate documentation file.

### Issue 8: Nested Structure Changes

**Problem**: Some fields moved from nested to root level

**Old YAML**:
```yaml
agent:
  workspace_root: /path/to/project
  memory:
    pruning:
      enabled: true
```

**New JSON**:
```json
{
  "workspace_root": "/path/to/project",  // Moved to root
  "memory": {  // Moved to root
    "pruning": {
      "enabled": true
    }
  }
}
```

### Issue 9: Tool vs Tools Naming

**Problem**: Singular `tool` renamed to plural `tools`

**Old**:
```yaml
tool:
  filesystem:
    enabled: true
```

**New**:
```json
{
  "tools": {  // Note the 's'
    "filesystem": {
      "enabled": true
    }
  }
}
```

### Issue 10: Memory Config Structure Changed

**Problem**: Memory configuration fields renamed

**Old**:
```yaml
agent:
  memory:
    pruning:
      soft_trim_chars: 3000
      hard_clear_threshold: 10000
      protect_recent: 3
```

**New**:
```json
{
  "memory": {
    "pruning": {
      "enabled": true,
      "keep_recent": 3,
      "trim_tool_results": true,
      "max_tool_result_length": 3000
    }
  }
}
```

## Migration Checklist

- [ ] Backup old `profile.yaml`
- [ ] Convert `agent:` → `api:`
- [ ] Convert `tool:` → `tools:`
- [ ] Move `agent.workspace_root` → root level
- [ ] Move `agent.memory` → root level
- [ ] Move `agent.system_prompt` → root level
- [ ] Convert YAML syntax to JSON
- [ ] Validate JSON syntax (`jq . < config.json`)
- [ ] Test with `leonai config show`
- [ ] Test agent startup
- [ ] Verify all tools work
- [ ] Remove old `profile.yaml` (optional)

## Migration Success Stories

### Story 1: Simple Local Development Setup

**Before** (profile.yaml):
```yaml
agent:
  model: claude-sonnet-4-5-20250929
  temperature: 0.5
  workspace_root: /Users/dev/myproject

tool:
  filesystem:
    enabled: true
  command:
    enabled: true
```

**After** (config.json):
```json
{
  "api": {
    "model": "leon:balanced",
    "temperature": 0.5
  },
  "workspace_root": "/Users/dev/myproject",
  "tools": {
    "filesystem": {
      "enabled": true
    },
    "command": {
      "enabled": true
    }
  }
}
```

**Result**: Cleaner config using virtual model names, all features working.

### Story 2: Multi-Project Setup with Shared Credentials

**Before**: Duplicated API keys in each project's profile.yaml

**After**:

User config (`~/.leon/config.json`):
```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL}",
    "model_provider": "openai"
  }
}
```

Project A (`.leon/config.json`):
```json
{
  "api": {
    "model": "leon:coding"
  }
}
```

Project B (`.leon/config.json`):
```json
{
  "api": {
    "model": "leon:research"
  },
  "tools": {
    "command": {
      "enabled": false
    }
  }
}
```

**Result**: Credentials in one place, per-project customization, no duplication.

### Story 3: Production Environment with Security

**Before** (profile.yaml):
```yaml
agent:
  model: claude-opus-4-6
  enable_audit_log: false
  block_dangerous_commands: false

tool:
  filesystem:
    enabled: true
  command:
    enabled: true
```

**After** (config.json):
```json
{
  "api": {
    "model": "claude-opus-4-6",
    "enable_audit_log": true,
    "allowed_extensions": ["py", "js", "ts", "json"],
    "block_dangerous_commands": true,
    "block_network_commands": true
  },
  "tools": {
    "filesystem": {
      "enabled": true,
      "tools": {
        "write_file": false,
        "edit_file": false
      }
    },
    "command": {
      "enabled": false
    }
  }
}
```

**Result**: Read-only access, audit logging enabled, dangerous commands blocked.

### Story 4: Research Agent with Web Access

**Before** (profile.yaml):
```yaml
agent:
  model: claude-sonnet-4-5-20250929
  temperature: 0.3

tool:
  web:
    enabled: true
    tools:
      web_search:
        enabled: true
        tavily_api_key: ${TAVILY_API_KEY}
  command:
    enabled: true
```

**After** (config.json):
```json
{
  "api": {
    "model": "leon:research"
  },
  "tools": {
    "web": {
      "enabled": true,
      "tools": {
        "web_search": {
          "enabled": true,
          "max_results": 20,
          "tavily_api_key": "${TAVILY_API_KEY}"
        }
      }
    },
    "command": {
      "enabled": false
    },
    "filesystem": {
      "tools": {
        "write_file": false,
        "edit_file": false
      }
    }
  }
}
```

**Result**: Research-focused agent with enhanced web search, no code execution.

## FAQ

### Q1: Do I have to migrate immediately?

**A**: No, but it's recommended. The old profile.yaml format is deprecated and may be removed in future versions. The new config system provides better validation, three-tier merging, and virtual model mapping.

### Q2: Can I use both profile.yaml and config.json?

**A**: No. Leon will only load config.json if it exists. If both exist, profile.yaml is ignored.

### Q3: What happens to my old profile.yaml after migration?

**A**: The migration tool creates a backup with `.bak` suffix (e.g., `profile.yaml.bak`). You can safely delete it after verifying the migration worked.

### Q4: How do I test the migration without making changes?

**A**: Use dry-run mode:
```bash
leonai config migrate --dry-run
```

This validates the migration without writing files.

### Q5: Can I rollback if something goes wrong?

**A**: Yes, the migration tool creates backups:
```bash
# Restore from backup
cp ~/.leon/profile.yaml.bak ~/.leon/profile.yaml
rm ~/.leon/config.json

# Or use the rollback command (if available)
leonai config rollback
```

### Q6: Do virtual model names work with all providers?

**A**: Virtual models (leon:*) are mapped to specific Claude models by default. If you're using a different provider, you can:
- Use actual model names instead: `"model": "gpt-4"`
- Override the model mapping in your config

### Q7: How do I migrate MCP server configurations?

**A**: MCP config structure is mostly unchanged, just move from YAML to JSON:

**Before**:
```yaml
mcp:
  servers:
    github:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
```

**After**:
```json
{
  "mcp": {
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    }
  }
}
```

### Q8: What if I have custom memory settings?

**A**: Memory config structure changed. Map old fields to new:

**Old fields** → **New fields**:
- `soft_trim_chars` → `max_tool_result_length`
- `protect_recent` → `keep_recent`
- `hard_clear_threshold` → (removed, use `trigger_ratio` instead)
- `reserve_tokens` → (removed, use `trigger_ratio` instead)

### Q9: Can I keep using environment variables?

**A**: Yes! Environment variable expansion (`${VAR}`) works the same way in JSON. You can also use the `LEON__` prefix for nested config:

```bash
export LEON__API__MODEL=claude-opus-4-6
export LEON__API__TEMPERATURE=0.3
```

### Q10: How do I verify my migration was successful?

**A**: Run these checks:

```bash
# 1. Validate JSON syntax
jq . < ~/.leon/config.json

# 2. View merged configuration
leonai config show

# 3. Test agent startup
leonai

# 4. Verify tools are available
# (Check that expected tools appear in agent)
```

### Q11: What if I encounter validation errors?

**A**: Common validation errors and fixes:

**Error**: `Missing 'api.model' field`
**Fix**: Add model to api section:
```json
{
  "api": {
    "model": "claude-sonnet-4-5-20250929"
  }
}
```

**Error**: `Unknown tool: xyz`
**Fix**: Check tool name spelling. Valid tools: `filesystem`, `search`, `web`, `command`

**Error**: `Invalid MCP server config`
**Fix**: Ensure each MCP server has a `command` field:
```json
{
  "mcp": {
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    }
  }
}
```

### Q12: Can I migrate just part of my config?

**A**: Yes, you can start with a minimal config and add more later:

**Minimal config**:
```json
{
  "api": {
    "model": "leon:balanced"
  }
}
```

Then add tools, memory settings, etc. as needed. The three-tier system will merge your config with system defaults.

Instead of migrating, consider using built-in presets:

```bash
# For coding tasks
leonai --agent coder

# For research tasks
leonai --agent researcher

# For testing tasks
leonai --agent tester
```

Then customize only what you need in `~/.leon/config.json`:

```json
{
  "api": {
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL}"
  }
}
```

## Rollback Instructions

If you need to rollback to the old system:

### Step 1: Restore Backup

```bash
cp ~/.leon/profile.yaml.backup ~/.leon/profile.yaml
```

### Step 2: Remove New Config

```bash
rm ~/.leon/config.json
```

### Step 3: Downgrade Leon

```bash
uv tool install leonai==0.2.3
```

## Getting Help

If you encounter issues during migration:

1. Check configuration syntax: `jq . < ~/.leon/config.json`
2. View current config: `leonai config show`
3. Enable verbose logging: `leonai --verbose`
4. Report issues: https://github.com/anthropics/leon/issues

## See Also

- [Configuration Documentation](configuration.md) - Full configuration reference
- [Agent Presets](configuration.md#agent-presets) - Built-in agent configurations
- [Virtual Models](configuration.md#virtual-model-mapping) - Using `leon:*` model names
