# Leon - AI Agent Runtime

## 架构

Middleware-First：6 层中间件栈注入 tools

```
agent.py                    # Agent 核心，组装中间件
├── middleware/
│   ├── prompt_caching.py   # 缓存
│   ├── filesystem/         # read/write/edit/list_dir
│   ├── search/             # grep_search/find_by_name
│   ├── web/                # web_search/read_url_content
│   │   ├── searchers/      # tavily → exa → firecrawl
│   │   └── fetchers/       # jina → markdownify
│   ├── command/            # run_command/command_status
│   │   └── shell/hooks/    # 安全拦截
│   └── skills/             # load_skill
├── tui/                    # Textual UI
│   ├── app.py              # 主应用
│   └── leon_cli.py         # CLI 入口
├── profiles/               # YAML 配置
└── agent_profile.py        # Pydantic 模型
```

## 约定

- 工具参数：PascalCase（FilePath, SearchPath）
- 路径：强制绝对路径，限制 workspace_root
- Hook 优先级：1-10，数字大优先

## 命令

```bash
uv run leonai                        # 启动
uv run leonai --workspace <path>     # 指定目录
uv run leonai --profile <yaml>       # 自定义配置
```

## 环境变量

```
OPENAI_API_KEY      # 必需
OPENAI_BASE_URL     # 代理
TAVILY_API_KEY      # Web 搜索
```

## TODO

- [ ] Hook 系统扩展
- [ ] Plugin 适配
- [ ] 评估系统
- [ ] 轨迹自动优化
- [ ] Agent 协作调度
