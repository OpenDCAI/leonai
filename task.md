# Tasks

## Completed

### Command Middleware
- Custom `CommandMiddleware` with `run_command` / `command_status` tools
- Support for `Blocking` / `Cwd` / `Timeout` parameters
- Security hooks (dangerous command blocking, path restrictions)
- Output truncation with line count annotation

### Agent Profile
- Profile data structure (Pydantic): agent, tools, system_prompt
- Support YAML/JSON/TOML formats
- CLI arguments: `--profile <path>` and `--workspace <dir>`
- Environment variable expansion: `${VAR}`
- Conditional middleware loading based on `tools.*.enabled`

### TUI Resume
- SessionManager: save/load thread_id and thread list
- CLI argument: `--thread <id>` to resume specific conversation
- Auto-resume: continue last conversation by default
- Thread switching: Ctrl+T to browse and switch conversations

---

## Next

### MCP & Skills Support
- Support MCP servers/skills injection as tools
- Profile-based enable/permission/whitelist configuration
- Observability: loading logs, call logs, failure diagnostics
