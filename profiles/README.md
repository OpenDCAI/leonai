# Agent Profiles

Profile 配置文件，用于定义 Agent 的行为和工具集。

## 使用方法

```bash
# 使用默认配置
leonai

# 使用指定 profile
leonai --profile profiles/reviewer.yaml

# CLI 参数覆盖 profile
leonai --profile profiles/reviewer.yaml --workspace /path/to/project
```

## 可用 Profiles

### default.yaml
标准配置，所有工具启用，适合日常开发。

### coder.yaml
编码专用，所有工具启用，适合编写和修改代码。

### reviewer.yaml
只读模式，禁用命令执行，适合代码审查。
- 自定义 system_prompt 强调代码质量分析
- 无法修改文件或执行命令

### researcher.yaml
研究模式，只读 + Web 工具，适合信息搜集。
- 禁用命令执行
- 禁用审计日志（减少开销）

## Profile 结构

```yaml
agent:
  model: "claude-sonnet-4-5-20250929"
  workspace_root: null  # null = 使用当前目录
  read_only: false
  enable_audit_log: true

system_prompt: null  # null = 使用默认提示词

tools:
  filesystem:
    enabled: true
    read_only: false
    allowed_extensions: null  # null = 允许所有扩展名

  search:
    enabled: true

  web:
    enabled: true

  command:
    enabled: true
    block_dangerous_commands: true
    block_network_commands: false
```

## 环境变量展开

Profile 支持环境变量展开：

```yaml
agent:
  workspace_root: "${HOME}/projects/myapp"
```

## CLI 参数优先级

CLI 参数 > Profile 配置 > 默认值

```bash
# Profile 设置 read_only=true，但 CLI 覆盖为 false
leonai --profile profiles/reviewer.yaml --workspace /tmp
```
