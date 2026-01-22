# Cascade-Like Agent

完全模仿 Windsurf Cascade 的 Agent 实现，使用纯 Middleware 架构。

## 🎯 设计目标

1. **纯 Middleware 架构**：所有工具都在 middleware 层实现，不暴露为独立 Tool
2. **强制绝对路径**：所有文件和目录路径必须是绝对路径
3. **完整安全机制**：权限控制、命令拦截、审计日志
4. **模块化设计**：通过 Hook 系统轻松扩展功能

## 📦 架构概览

```
CascadeLikeAgent
├── AnthropicPromptCachingMiddleware    # 成本优化
├── FileSystemMiddleware                # 文件操作
│   ├── read_file
│   ├── write_file
│   ├── edit_file
│   ├── multi_edit
│   └── list_dir
├── SearchMiddleware                    # 搜索功能
│   ├── grep_search
│   └── find_by_name
└── ExtensibleBashMiddleware            # 命令执行
    ├── PathSecurityHook                # 路径安全
    ├── CommandLoggerHook               # 命令日志
    └── DangerousCommandsHook           # 危险命令拦截
```

## 🛠️ 核心组件

### 1. FileSystemMiddleware

**文件操作中间件** - 实现所有文件系统操作

#### 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `read_file` | 读取文件内容 | `file_path` (绝对路径), `offset` (可选), `limit` (可选) |
| `write_file` | 创建新文件 | `file_path` (绝对路径), `content` |
| `edit_file` | 编辑文件 | `file_path`, `old_string`, `new_string` |
| `multi_edit` | 批量编辑 | `file_path`, `edits` (数组) |
| `list_dir` | 列出目录 | `directory_path` (绝对路径) |

#### 特性

- ✅ 强制绝对路径验证
- ✅ Workspace 限制
- ✅ 文件大小限制（默认 10MB）
- ✅ 文件类型过滤（可选）
- ✅ 只读模式支持
- ✅ Hook 系统集成

#### 示例

```python
from cascade_agent import create_cascade_agent

agent = create_cascade_agent()

# 读取文件
response = agent.get_response(
    f"Read the file {agent.workspace_root}/test.py"
)

# 创建文件
response = agent.get_response(
    f"Create a Python file at {agent.workspace_root}/hello.py "
    f"with a hello world function"
)

# 编辑文件
response = agent.get_response(
    f"In {agent.workspace_root}/hello.py, change 'world' to 'Cascade'"
)
```

### 2. SearchMiddleware

**搜索中间件** - 实现文件搜索功能

#### 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `grep_search` | 内容搜索 | `search_path`, `query`, `case_sensitive`, `fixed_strings`, `includes`, `match_per_line` |
| `find_by_name` | 文件名搜索 | `search_directory`, `pattern`, `extensions`, `type_filter`, `max_depth` |

#### 特性

- ✅ 正则表达式支持
- ✅ Glob 模式匹配
- ✅ 文件类型过滤
- ✅ 最大结果数限制（默认 100）
- ✅ 大文件跳过（>10MB）

#### 示例

```python
# 搜索内容
response = agent.get_response(
    f"Search for 'def' in all Python files under {agent.workspace_root}"
)

# 查找文件
response = agent.get_response(
    f"Find all .py files in {agent.workspace_root}"
)
```

### 3. ExtensibleBashMiddleware

**命令执行中间件** - 带安全 Hook 系统的 Bash 执行

#### Hook 系统

| Hook | 优先级 | 功能 |
|------|--------|------|
| `DangerousCommandsHook` | 5 | 拦截危险命令（rm -rf, sudo 等） |
| `PathSecurityHook` | 10 | 限制路径访问到 workspace |
| `CommandLoggerHook` | 50 | 记录所有命令执行 |

#### 特性

- ✅ 自动加载 `bash_hooks/` 目录下的所有 hooks
- ✅ 按优先级顺序执行
- ✅ 任何 hook 拦截即停止执行
- ✅ 支持命令前后回调

#### 示例

```python
# 安全命令
response = agent.get_response(
    "Use bash to list all Python files and count them"
)

# 危险命令（会被拦截）
response = agent.get_response(
    "Use bash to remove all files with rm -rf *"
)
# 返回: ❌ SECURITY ERROR: Dangerous command detected
```

## 🔒 安全机制

### 1. 路径验证

所有路径必须满足：
- ✅ 绝对路径（从 `/` 开始）
- ✅ 在 workspace 内
- ✅ 不包含路径遍历（`../`）

### 2. 权限控制

通过 `FilePermissionHook` 实现：
- **只读模式**：禁止所有写入操作
- **文件类型限制**：只允许特定扩展名
- **路径黑名单**：禁止访问特定路径

### 3. 命令拦截

通过 `DangerousCommandsHook` 拦截：
- `rm -rf` - 递归删除
- `sudo`, `su` - 权限提升
- `chmod`, `chown` - 权限修改
- `kill`, `pkill` - 进程终止
- `curl`, `wget` - 网络请求（可选）

### 4. 审计日志

自动记录所有操作：
- `bash_commands.log` - 所有 bash 命令
- `file_access.log` - 所有文件操作

## 🚀 快速开始

### 基本用法

```python
from cascade_agent import create_cascade_agent

# 创建 agent
agent = create_cascade_agent()

# 使用 agent
response = agent.get_response(
    f"Create a Python file at {agent.workspace_root}/test.py"
)

print(response)

# 清理
agent.cleanup()
```

### 只读模式

```python
agent = create_cascade_agent(
    read_only=True  # 禁止写入和编辑
)
```

### 文件类型限制

```python
agent = create_cascade_agent(
    allowed_file_extensions=["py", "txt", "md"]  # 只允许这些类型
)
```

### 自定义 Workspace

```python
agent = create_cascade_agent(
    workspace_root="/path/to/your/workspace"
)
```

### 完整配置

```python
agent = create_cascade_agent(
    model_name="claude-sonnet-4-5-20250929",
    workspace_root="/path/to/workspace",
    read_only=False,
    allowed_file_extensions=["py", "txt", "md", "json"],
    block_dangerous_commands=True,
    block_network_commands=True,
    enable_audit_log=True,
)
```

## 📝 示例脚本

运行完整演示：

```bash
python examples/cascade_demo.py
```

演示内容：
1. ✅ 文件操作（创建、读取、编辑、批量编辑）
2. ✅ 搜索功能（内容搜索、文件名搜索）
3. ✅ 命令执行（安全命令、危险命令拦截）
4. ✅ 安全功能（路径验证、权限控制）
5. ✅ 只读模式
6. ✅ 审计日志

## 🔧 扩展开发

### 添加新的文件操作 Hook

1. 在 `middleware/bash_hooks/` 创建新文件：

```python
# my_custom_hook.py
from .base import HookResult

class MyCustomHook:
    def check_file_operation(self, file_path: str, operation: str) -> HookResult:
        # 你的验证逻辑
        if should_block:
            return HookResult.block_command("Error message")
        return HookResult.allow_command()
```

2. 在 `CascadeLikeAgent` 中注册：

```python
file_hooks.append(MyCustomHook(workspace_root=self.workspace_root))
```

### 添加新的 Bash Hook

1. 在 `middleware/bash_hooks/` 创建新文件：

```python
# my_bash_hook.py
from .base import BashHook, HookResult

class MyBashHook(BashHook):
    priority = 20
    name = "MyBashHook"
    
    def check_command(self, command: str, context: dict) -> HookResult:
        # 你的验证逻辑
        return HookResult.allow_command()
```

2. Hook 会被自动加载（通过 `loader.py`）

## 📊 与 Cascade 的对比

| 特性 | Cascade | CascadeLikeAgent | 状态 |
|------|---------|------------------|------|
| 绝对路径要求 | ✅ | ✅ | ✅ 完全一致 |
| 文件操作 | ✅ | ✅ | ✅ 完全实现 |
| 搜索功能 | ✅ | ✅ | ✅ 完全实现 |
| 命令执行 | ✅ | ✅ | ✅ 完全实现 |
| Workspace 限制 | ✅ | ✅ | ✅ 完全一致 |
| 安全机制 | ✅ | ✅ | ✅ 增强版 |
| 审计日志 | ✅ | ✅ | ✅ 完全实现 |
| 纯 Middleware | ✅ | ✅ | ✅ 完全一致 |

## 🎓 设计原则

### 1. 绝对路径优先

**为什么？**
- 消除歧义
- 多 workspace 支持
- 提高安全性
- 简化状态管理

### 2. Middleware 优先于 Tool

**为什么？**
- 更好的控制力
- 统一的拦截点
- 更容易实现安全策略
- 更灵活的扩展性

### 3. Hook 系统

**为什么？**
- 模块化
- 可插拔
- 易于测试
- 清晰的职责分离

### 4. Fail Fast

**为什么？**
- 尽早发现问题
- 明确的错误信息
- 避免级联错误
- 更好的用户体验

## 🐛 故障排除

### 路径错误

```
❌ Path must be absolute: test.py
```

**解决**：使用绝对路径
```python
# ❌ 错误
agent.get_response("Read test.py")

# ✅ 正确
agent.get_response(f"Read {agent.workspace_root}/test.py")
```

### Workspace 限制

```
❌ Path outside workspace
```

**解决**：确保路径在 workspace 内
```python
# 检查 workspace 位置
print(agent.workspace_root)

# 使用 workspace 内的路径
path = agent.workspace_root / "myfile.txt"
```

### 权限错误

```
❌ Write operation not allowed in read-only mode
```

**解决**：移除只读模式
```python
agent = create_cascade_agent(read_only=False)
```

## 📚 API 参考

### CascadeLikeAgent

```python
class CascadeLikeAgent:
    def __init__(
        self,
        model_name: str = "claude-sonnet-4-5-20250929",
        api_key: str | None = None,
        workspace_root: str | Path | None = None,
        *,
        read_only: bool = False,
        allowed_file_extensions: list[str] | None = None,
        block_dangerous_commands: bool = True,
        block_network_commands: bool = False,
        enable_audit_log: bool = True,
    )
    
    def invoke(self, message: str, thread_id: str = "default", **kwargs) -> dict
    def get_response(self, message: str, thread_id: str = "default", **kwargs) -> str
    def cleanup(self)
```

### create_cascade_agent

```python
def create_cascade_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
    api_key: str | None = None,
    workspace_root: str | Path | None = None,
    **kwargs,
) -> CascadeLikeAgent
```

## 🎯 最佳实践

1. **始终使用绝对路径**
2. **在生产环境启用只读模式**（如果不需要写入）
3. **定期检查审计日志**
4. **为敏感操作添加自定义 Hook**
5. **使用 thread_id 管理会话**
6. **在 finally 块中调用 cleanup()**

## 📄 许可证

MIT License

---

**Built with LangChain + Anthropic Claude** 🦜🔗🤖
