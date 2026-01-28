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

---

## 接下来 3 个大功能（开发顺序已决策）

### 1) Agent Profile（静态化 + 配置化 agent 能力）

- **目标**
  - 用配置文件管理 agent 能力开关与参数，避免散落在代码里
  - 作为后续 `resume` 和 `MCP skills` 的统一入口

- **配置形式**
  - 配置文件：YAML/TOML/JSON
  - 只做最小必要能力，不引入复杂模板系统

- **建议配置块**
  - `agent`: model、workspace_root、read_only、audit、thread_id（可选）
  - `tools`: filesystem/search/web/command 的 enable 与参数
  - `command.hooks`: dangerous_commands/path_security 等

- **验收标准**
  - 支持 `--profile <path.(yaml|toml|json)>`
  - Profile 解析后有强类型校验（Fail Fast）
  - agent 初始化逻辑只依赖 profile（或 profile + CLI 覆盖）
  - 默认 profile 不存在时也能启动（使用合理默认值）

### 2) TUI Resume（退出后恢复继续聊，只恢复 messages/thread）

- **目标**
  - 退出 TUI 后，下次启动能继续某个对话 thread
  - 只恢复 `messages/thread`，不恢复未完成 tool call、不恢复 UI 状态

- **建议实现**
  - session 文件（例如保存最近 thread_id 列表、last_thread_id）
  - CLI 参数支持：`--thread <id>`

- **验收标准**
  - 重启后使用同一个 `thread_id` 可加载历史 messages 并继续对话
  - 提供明确的 “当前 thread_id” 展示与切换入口

### 3) MCP Skill 能力支持

- **目标**
  - 支持通过 MCP 引入 skills/servers，并以 tool 的形式注入 agent

- **依赖**
  - 依赖 Agent Profile 作为启用与权限策略入口

- **验收标准**
  - Profile 可配置 MCP servers/skills 的 enable、权限、白名单
  - 可观测性：加载日志、调用日志、失败可定位

---

## 当前决策

- **开发顺序**
  - 先做 Agent Profile
  - 再做 TUI Resume（只恢复 messages/thread）
  - 做 MCP Skill
