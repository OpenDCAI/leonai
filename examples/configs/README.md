# Leon Configuration Examples

This directory contains example configuration files for common use cases.

## Quick Start

Copy an example to your config location:

```bash
# User config (API keys and personal settings)
cp examples/configs/user-config.json ~/.leon/config.json

# Project config (project-specific settings)
cp examples/configs/local-dev.json .leon/config.json
```

## Available Examples

### User Configuration

- **user-config.json** - Basic user configuration with API credentials
- **user-config-proxy.json** - Configuration for OpenAI-compatible proxy

### Project Configurations

- **local-dev.json** - Local development with full access
- **production.json** - Production environment (read-only, secure)
- **testing.json** - Testing environment with extended timeouts
- **research.json** - Research agent (web access, no code execution)
- **minimal.json** - Minimal configuration example

### Migration Examples

- **migration-before.yaml** - Example old profile.yaml format
- **migration-after.json** - Equivalent new config.json format

## Configuration Tips

1. **Never commit API keys** - Use environment variables (`${VAR}`)
2. **Separate concerns** - User config for credentials, project config for settings
3. **Start simple** - Begin with minimal config, add features as needed
4. **Use virtual models** - `leon:*` names are easier to manage than full model names
5. **Enable security** - Always use `block_dangerous_commands: true` in production

## See Also

- [Configuration Documentation](../../docs/configuration.md)
- [Migration Guide](../../docs/migration-guide.md)
