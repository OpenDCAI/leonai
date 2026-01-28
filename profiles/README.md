# Profile 配置原则

## 结构

```
agent  - 模型、工作区
tool   - 工具能力（filesystem/search/web/command）
mcp    - MCP 服务器
```

## 参数归类原则

**根据实际作用域归类，而非代码位置**

### 全局级 (agent)
影响所有工具
- `model`: 模型名称
- `workspace_root`: 工作目录

### Middleware 级 (tool.xxx)
影响该 middleware 下多个工具
- `tool.search.max_results`: 影响 grep 和 find
- `tool.web.timeout`: 影响所有 web 请求

### 工具级 (tool.xxx.tools.yyy)
只影响单个工具
- `tool.filesystem.tools.read_file.max_file_size`: 只在 read_file 检查
- `tool.web.tools.web_search.tavily_api_key`: 只用于 web_search
- `tool.command.tools.run_command.default_timeout`: 只在 run_command 使用

## 示例

### 最小配置
```yaml
agent:
  model: claude-sonnet-4-5-20250929
```

### 只读模式
```yaml
tool:
  filesystem:
    tools:
      write_file: false
      edit_file: false
```

### 禁用工具
```yaml
tool:
  filesystem:
    enabled: false  # 禁用整个 middleware
  web:
    tools:
      web_search:
        enabled: false  # 只禁用单个工具
```

## 注意

- API Keys 为 null 时自动从环境变量读取
- 新增参数前必须调研其实际作用域
- default.yaml 是完整模板
