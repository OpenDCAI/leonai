# Mycel Configuration Examples

Example `runtime.json` configurations for common use cases. These are project-level configs — place them at `.leon/runtime.json` in your project root.

## Usage

```bash
# Copy to your project
mkdir -p .leon
cp examples/configs/local-dev.json .leon/runtime.json
```

## Available Examples

| File | Use Case | Description |
|------|----------|-------------|
| `minimal.json` | Getting started | Just temperature — everything else uses defaults |
| `user-config.json` | User config (`~/.leon/runtime.json`) | API credentials, MCP servers, web tools |
| `local-dev.json` | Development | Full filesystem + command access, no web |
| `production.json` | Production (read-only) | No writes, no commands, audit logging enabled |
| `research.json` | Research agent | Web search + fetch enabled, no code execution |
| `testing.json` | QA / Testing | Extended command timeout (300s), no web |

## Tips

1. **Never commit API keys** — use `${VAR}` syntax for env var substitution
2. **Start simple** — begin with `minimal.json`, add settings as needed
3. **Separate concerns** — user config in `~/.leon/runtime.json`, project config in `.leon/runtime.json`

## See Also

- [Configuration Documentation](../../docs/en/configuration.md)
- [Sandbox Examples](../sandboxes/) — sandbox provider configs
