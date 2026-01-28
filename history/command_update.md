# Task: 重构 Command Middleware（替换 LangChain ShellToolMiddleware）

## 目标
实现自己的 CommandMiddleware，达到与 Cascade `run_command` 同等能力，不再依赖 LangChain 的 `ShellToolMiddleware`。

---

## Cascade `run_command` 完整能力

### 参数列表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `CommandLine` | `string` | ✅ | 要执行的命令 |
| `Cwd` | `string` | ❌ | 工作目录（不传则用默认） |
| `Blocking` | `boolean` | ❌ | 是否阻塞等待完成（默认 true） |
| `SafeToAutoRun` | `boolean` | ❌ | 是否安全到可以自动运行（不需用户确认） |
| `WaitMsBeforeAsync` | `integer` | ❌ | 非阻塞模式下，启动后等待多少毫秒再返回（用于捕获快速失败） |

### 行为特性

1. **阻塞 vs 非阻塞**
   - `Blocking=true`：等命令执行完，返回完整输出
   - `Blocking=false`：启动后立即返回一个 `CommandId`，后续用 `command_status` 工具查询

2. **安全检查**
   - `SafeToAutoRun=true`：跳过用户确认，直接执行
   - `SafeToAutoRun=false`（默认）：需要用户批准才执行
   - 危险命令（`rm -rf`、`sudo` 等）即使设置 `SafeToAutoRun=true` 也会被拒绝

3. **工作目录**
   - `Cwd` 指定命令执行的目录
   - 不传则使用 workspace 根目录

4. **超时处理**
   - 阻塞模式下有内置超时
   - 非阻塞模式下通过 `WaitMsBeforeAsync` 控制初始等待

5. **配套工具**
   - `command_status`：查询非阻塞命令的状态和输出

### 错误处理

- 命令不存在 → 返回错误信息
- 超时 → 返回超时错误
- 非零退出码 → 返回 exit code + stderr
- 危险命令 → 拒绝执行并说明原因

---

## 当前实现的差距

| 能力 | Cascade | 当前 `bash` |
|------|---------|--------------|
| 工具名 | `run_command` | `bash` |
| 参数名 | `CommandLine` | `command` |
| Cwd 支持 | ✅ 每次调用可指定 | ❌ 无 |
| Blocking 模式 | ✅ 可选 | ❌ 永远阻塞 |
| 非阻塞状态查询 | ✅ `command_status` | ❌ 无 |
| SafeToAutoRun | ✅ 有 | ❌ 无（用 hooks 做安全检查） |
| 多 shell 支持 | ✅ 根据 OS 自动选 | ❌ 写死 `/bin/bash` |
| 超时控制 | ✅ 内置 | ⚠️ 内部有，但不可调 |

---

## 设计方案

### 目录结构

```
middleware/
  command/
    __init__.py
    middleware.py          # 主入口：注入 tool + 拦截 tool call
    dispatcher.py          # 根据 OS/参数 选择 executor
    base.py                # Executor 基类
    bash/
      __init__.py
      executor.py
    zsh/
      __init__.py
      executor.py
    powershell/
      __init__.py
      executor.py
```

### Tool Schema（对齐 Cascade）

```python
{
    "name": "run_command",
    "description": "Execute shell command. OS auto-detects shell (mac→zsh, linux→bash, win→powershell).",
    "parameters": {
        "type": "object",
        "properties": {
            "CommandLine": {"type": "string", "description": "Command to execute"},
            "Cwd": {"type": "string", "description": "Working directory (optional)"},
            "Blocking": {"type": "boolean", "description": "Wait for completion (default: true)"},
            "Timeout": {"type": "integer", "description": "Timeout in seconds (optional)"},
        },
        "required": ["CommandLine"]
    }
}
```

### 默认 Shell 选择规则

- 使用系统默认 shell

### 核心实现思路

1. **不依赖 LangChain ShellToolMiddleware**
   - 直接用 Python `subprocess` / `asyncio.create_subprocess_shell`
   - 自己管理进程生命周期

2. **Executor 基类**
   ```python
   class BaseExecutor(ABC):
       @abstractmethod
       async def execute(self, command: str, cwd: str | None, timeout: float | None) -> ExecuteResult:
           ...
   ```

3. **Dispatcher**
   ```python
   def get_executor() -> BaseExecutor:
       system = platform.system()
       if system == "Darwin":
           return ZshExecutor()
       elif system == "Windows":
           return PowerShellExecutor()
       else:
           return BashExecutor()
   ```

4. **非阻塞支持**
   - 启动进程后返回 `command_id`
   - 用字典存储运行中的进程
   - 提供 `command_status` 工具查询

---

## 实施步骤

1. [x] 创建 `middleware/command/` 目录结构
2. [x] 实现 `base.py`（Executor 基类 + ExecuteResult）
3. [x] 实现 `bash/executor.py`
4. [x] 实现 `zsh/executor.py`
5. [x] 实现 `dispatcher.py`
6. [x] 实现 `middleware.py`（注入 tool + 拦截处理）
7. [x] 实现 `command_status` 工具（非阻塞查询）
8. [x] 迁移 hooks 系统
9. [x] 删除对 LangChain ShellToolMiddleware 的依赖
10. [x] 更新 agent.py 和相关引用
11. [x] 测试验证（20 tests passed）

---

## 不做向后兼容

- 工具名从 `bash` 改为 `run_command`
- 参数名从 `command` 改为 `CommandLine`
- 删除旧的 `middleware/shell/` 目录
