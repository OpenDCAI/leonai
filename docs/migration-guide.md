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

## Using Agent Presets Instead

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
