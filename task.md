 # Tasks

## 背景

Leon 目标：用纯 Middleware 架构模拟 Windsurf Cascade 的 tool-calling 机制。

---

## 已完成（里程碑）

### Command Middleware 重构（替换 LangChain ShellToolMiddleware）

- **完成内容**
  - 替换 LangChain `ShellToolMiddleware` → 自研 `CommandMiddleware`
  - 提供 `run_command` / `command_status` 两个工具
  - 支持 `Blocking` / `Cwd` / `Timeout` 等参数
  - hooks 安全拦截（危险命令、路径限制）
  - 输出截断行为对齐 Cascade（`command_status` 返回最后 N 字符并标注截断行数）

- **测试**
  - `tests/test_command_middleware.py` 覆盖 executor、middleware、hooks、异步执行

- **TUI 体验优化**
  - Ctrl+C：优先中断当前执行；空闲时双击退出
  - Ctrl+D：直接退出

### Agent Profile（静态化 + 配置化 agent 能力）

- **完成内容**
  - Profile 数据结构（Pydantic）：agent、tools、system_prompt
  - 支持 YAML/JSON/TOML 格式
  - CLI 参数：`--profile <path>` 和 `--workspace <dir>`
  - 环境变量展开：`${VAR}` 自动替换
  - CLI 参数覆盖 profile 设置
  - 条件化 middleware 加载（根据 tools.*.enabled）
  - 消除 middleware schema 重复（提取 _get_tool_schemas()）

- **示例 Profile**
  - `profiles/default.yaml`: 全工具启用
  - `profiles/coder.yaml`: 编码专用
  - `profiles/reviewer.yaml`: 只读 + 禁用命令
  - `profiles/researcher.yaml`: 只读 + Web 工具

- **验收标准**
  - ✅ 支持 `--profile <path.(yaml|json|toml)>`
  - ✅ Profile 解析后有强类型校验（Fail Fast）
  - ✅ Agent 初始化逻辑只依赖 profile（或 profile + CLI 覆盖）
  - ✅ 默认 profile 不存在时也能启动（使用合理默认值）
  - ✅ 消除 sync/async schema 重复

### TUI Resume（退出后恢复继续聊，只恢复 messages/thread）

- **完成内容**
  - SessionManager：保存/加载 thread_id 和 thread 列表
  - CLI 参数：`--thread <id>` 恢复指定对话
  - 自动恢复：默认继续上次对话
  - 历史加载：从 checkpointer 加载 messages
  - Thread 切换：Ctrl+T 浏览和切换对话
  - Session 持久化：`~/.config/leon/session.json`

- **验收标准**
  - ✅ 重启后使用同一个 `thread_id` 可加载历史 messages 并继续对话
  - ✅ 提供明确的 "当前 thread_id" 展示与切换入口（Ctrl+T）
  - ✅ 只恢复 messages/thread，不恢复未完成 tool call、不恢复 UI 状态

---

## 接下来 1 个大功能

### MCP Skill 能力支持

- **目标**
  - 支持通过 MCP 引入 skills/servers，并以 tool 的形式注入 agent

- **依赖**
  - 依赖 Agent Profile 作为启用与权限策略入口

- **验收标准**
  - Profile 可配置 MCP servers/skills 的 enable、权限、白名单
  - 可观测性：加载日志、调用日志、失败可定位
