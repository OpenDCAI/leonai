# LEON (Lane Runtime)

LEON 是一个面向企业级生产可用的 Agent Runtime：用于构建、运行与治理一组可长期运行的 Agent，并把它们当作可持续协作的 co-workers 来管理与调度。

LEON 以 LangChain Middleware 为核心架构：通过统一的 middleware 管线完成 tool 注入、运行时校验、安全拦截、上下文装载/卸载与可观测性。

## 快速体验（CLI）

当前可用的体验入口是 `leonai`（TUI）：

- `leonai`：启动
- `leonai config`：配置 API key
- `leonai config show`：查看当前配置

## 截图

![LEON TUI Screenshot](./docs/assets/leon-tui.png)

## 最小基座

LEON 认为一个真正可工作的 Agent，至少应具备三类基础能力：

- Web
- Bash
- File System

## 架构方式

- Middleware-first：tool schema 注入、参数/路径校验（Fail Fast）、hooks/policy 拦截、结果整形、可观测性
- Profile-driven（推进中）：用 Profile 描述 Agent 的 `system_prompt` 与 tools/mcp/skill 开关

## 安装

```bash
# 使用 uv（推荐）
uv tool install leonai

# 或使用 pipx
pipx install leonai
```

## 配置

```bash
leonai config
```

配置会保存到 `~/.config/leon/config.env`。

## 路线

- Agent Profile：配置化、强类型校验、统一能力入口
- TUI Resume：恢复 thread（仅 messages/thread）
- MCP Skill：可配置加载、权限、调用日志与失败定位

## 许可证

MIT License
