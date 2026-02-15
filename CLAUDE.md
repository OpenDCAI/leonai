# Leon - AI Agent Runtime

## 架构

两层：Sandbox 基础设施层 + Middleware 策略层

```
sandbox/                        # 基础设施层（执行环境）
├── base.py                     # Sandbox ABC → fs() / shell()
├── config.py                   # SandboxConfig（~/.leon/sandboxes/）
├── local.py                    # LocalSandbox（直通本机）
├── agentbay.py                 # AgentBaySandbox（云沙箱）
├── docker.py                   # DockerSandbox（本地容器）
├── manager.py                  # Session 生命周期（SQLite）
├── provider.py                 # SandboxProvider ABC
├── providers/                  # AgentBayProvider / DockerProvider
└── thread_context.py           # ContextVar thread_id

agent.py                        # Agent 核心，组装 sandbox + 中间件
├── middleware/                  # 策略层（10 层中间件栈）
│   ├── prompt_caching.py       # Anthropic prompt caching（仅 Anthropic 直连需要，其他模型自动缓存）
│   ├── memory/                 # 上下文压缩（Pruning + Compaction）
│   │   ├── pruner.py           # SessionPruner（trim/clear ToolMessage）
│   │   ├── compactor.py        # ContextCompactor（LLM 摘要）
│   │   └── middleware.py       # MemoryMiddleware（容器）
│   ├── filesystem/             # read/write/edit/list_dir
│   │   ├── backend.py          # FileSystemBackend ABC
│   │   ├── local_backend.py    # LocalBackend
│   │   └── sandbox_backend.py  # SandboxFileBackend
│   ├── search/                 # grep_search/find_by_name
│   ├── web/                    # web_search/read_url_content
│   │   ├── searchers/          # tavily → exa → firecrawl
│   │   └── fetchers/           # jina → markdownify
│   ├── command/                # run_command/command_status
│   │   ├── hooks/              # 安全拦截（base/loader/dangerous_commands/...）
│   │   └── sandbox_executor.py # SandboxExecutor
│   ├── skills/                 # load_skill
│   ├── task/                   # sub-agent 调用
│   ├── todo/                   # 任务列表管理
│   ├── queue/                  # Queue Mode (steer/followup/collect)
│   └── monitor/                # 运行时监控（组合模式）
│       ├── base.py             # BaseMonitor 接口
│       ├── token_monitor       # Token 统计（6 项分项：input/output/reasoning/cache_read/cache_write/total）
│       ├── cost.py             # CostCalculator（OpenRouter API 动态定价 → 磁盘缓存 → bundled 兜底）
│       ├── pricing_bundled.json # 离线定价数据（314 模型）
│       ├── context_monitor     # 上下文大小追踪
│       ├── state_monitor       # AgentState + AgentFlags
│       ├── runtime.py          # AgentRuntime（聚合）
│       └── middleware.py       # MonitorMiddleware（容器）
├── tui/                        # Textual UI
│   ├── app.py                  # 主应用
│   ├── leon_cli.py             # CLI 入口
│   └── runner.py               # 非交互式运行器
├── profiles/                   # YAML 配置
└── agent_profile.py            # Pydantic 模型（agent 身份，不含 sandbox）
```

Sandbox 按交互界面提供子能力，Middleware 消费：

| 界面 | 接口 | 消费者 |
|------|------|--------|
| FileSystem | `sandbox.fs()` → `FileSystemBackend` | FileSystemMiddleware |
| Shell | `sandbox.shell()` → `BaseExecutor` | CommandMiddleware |

## 配置系统

基于 pydantic-settings 的三层配置系统（借鉴 Claude Code）：

### 配置层级

1. **系统级**（源码内置）：`config/defaults/agents/*.json`（default/coder/researcher/tester）
2. **用户级**（`~/.leon/`）：
   - `config.json` - 用户全局配置（覆盖系统默认）
   - `agents/` - 用户自定义 agent 配置（合并）
   - `sandboxes/` - Sandbox 配置（linking，查找策略）
   - `skills/` - Skills 目录（linking）
   - `.mcp.json` - MCP 配置（linking）
   - `.env` - 环境变量（API keys）
3. **项目级**（`.leon/`）：同用户级结构，优先级最高

### 配置优先级

**项目级 > 用户级 > 系统级 > 默认值**

运行时覆盖（不持久化）：
- CLI：`--model`, `--workspace` 等参数
- Web：前端选择模型档次

### 合并策略

- **Agent 配置**：深度合并（三层叠加）
- **Sandbox/MCP/Skills**：查找策略（找到第一个就返回，无系统默认）
- **环境变量**：仅用于敏感信息（API keys），通过 `${VAR}` 引用

### 虚拟模型映射

系统默认（可通过 `config.json` 覆盖）：
- `leon:mini` → gpt-4o-mini (openai)
- `leon:medium` → claude-sonnet-4-5 (anthropic)
- `leon:large` → claude-opus-4-6 (anthropic)
- `leon:max` → gpt-5-turbo (openai)

支持分层映射（model + pr他参数继承）：
```json
{
  "model_mapping": {
    "leon:mini": { "model": "deepseek-chat", "provider": "openai" }
  },
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### CLI 使用

```bash
leonai --agent coder              # 使用预设 agent
leonai --model leon:large         # 使用虚拟模型
leonai config show                # 查看当前配置
leonai migrate-config             # 迁移旧配置
```

### 配置文件结构

```
~/.leon/
├── .env                    # 环境变量（API keys）
├── config.json             # 用户配置（覆盖系统默认）
├── agents/                 # 用户 Agent 配置（合并）
│   ├── my-researcher.json
│   └── custom-agen
├── sandboxes/              # Sandbox 配置（linking）
│   ├── my-agentbay.json
│   └── my-docker.json
├── skills/                 # Skills 目录（linking）
└── .mcp.json               # MCP 配置（linking）
```

详见 `docs/configuration.md` 和 `docs/migration-guide.md`

## 命令

```bash
uv run leonai                        # TUI 模式启动（默认 local sandbox）
uv run leonai --workspace <path>     # 指定目录
uv run leonai --agent <preset>       # 使用预设配置（default/coder/researcher/tester）
uv run leonai --model <name>         # 指定模型（支持 leon:* 虚拟名）
uv run leonai --sandbox <name>       # 指定 sandbox（从 ~/.leon/sandboxes/<name>.json 加载）
```

## Web 前后端启动

```bash
# 后端（FastAPI + uvicorn，端口 8001）
cd services/web && uv run python main.py

# 前端（Vite dev server，端口 5173，/api 代理到 127.0.0.1:8001）
cd frontend/app && npm run dev
```

访问 http://localhost:5173


## 环境变量规范

使用 pydantic-settings 自动加载，支持 `.env` 文件和嵌套配置：

```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=...

# Agent 配置
MODEL=leon:medium
WORKSPACE=~/my-workspace
TEMPERATURE=0.7
MAX_TOKENS=4096

# 嵌套配置（使用 __ 分隔符）
MEMORY__ENABLED=true
MEMORY__PRUNING_SOFT_TRIM=3000
TOOLS__WEB_SEARCH=false
```

关键场景：OpenAI 兼容代理调 Claude 时，必须在配置中设 `model_provider: openai`

## Prompt Caching

- 仅 Anthropic 直连（`ChatAnthropic`）需要显式 `cache_control` 标记
- OpenAI / DeepSeek 等自动缓存，无需干预
- 通过 OpenAI 代理调 Claude 时无法做 prompt caching（API 格式不兼容）
- `unsupported_model_behavior` 默认 `"ignore"`，非 Anthropic 模型静默跳过

## 目前开发流程
**小专**：逆向工程与代码分析专家Agent，负责分析 OpenClaw / OpenCode / LangChain 三个项目的文档和代码。文档和代码都在小专的工位上。

**开发流程**：开N 个小专并发分析三个项目 → 取其精华、去其糟粕 → 重构开发leon

**项目**：
1. **OpenClaw** — 最新的持久化 Agent.
2. **OpenCode** — 最新的CodingAgent。
3. **LangChain** — Agent 框架，leon 的核心依赖。

## Teams 文件夹

详见 `teams/README.md`

## 路线图

详见 `.claude/rules/roadmap.md`

## Agent Team 管理规范

详见 `.claude/rules/team-guidelines.md`

## Agent 任务执行注意事项

- Edit 工具返回信息不明确（"File edited... Replaced 1 occurrence"），无法区分是否真正修改了内容
- Agent 验证逻辑可能失败：当目标内容已存在时，无法判断是刚添加还是本来就有
- 简单编辑任务可能陷入验证循环（反复读取文件确认）
- 建议：编辑前先检查文件状态，或给 agent 明确指令"如果内容已存在则报告成功"

## 调试经验

详见 `.claude/rules/debugging.md`

## TODO

### P0 — 配置系统重构（进行中）

基于 pydantic-settings 的统一配置系统：
- ✅ 设计完成：三层配置 + 虚拟模型映射 + 查找/合并策略
- ⏳ Phase 1: 核心配置系统（schema.py, loader.py, resolver.py, validator.py）
- ⏳ Phase 2: Agent 集成（agent.py 使用新配置）
- ⏳ Phase 3: 配置迁移工具（migrate-config 命令）
- ⏳ Phase 4: Web 服务集成（动态模型切换）
- ⏳ Phase 5: 文档与测试

### P1 — 模块化规则系统

借鉴 Claude Code 的 `.claude/rules/` 系统：
- 支持 `.leon/rules/` 目录（自动递归加载）
- 支持 YAML frontmatter 的 paths 字段（路径特定规则）
- 支持符号链接（跨项目共享规则）

### P2 — Agent 协作调度

从单向调用升级为协作模式（双向通信、并行、Pipeline）。需要先设计再实施。

### P3 — Plugin 系统 + 自动优化

Plugin 适配、Hook 扩展、评估系统、轨迹优化。需要先设计再实施。

