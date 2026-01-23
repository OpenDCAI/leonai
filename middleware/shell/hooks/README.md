# Bash Hooks 插件系统

## 概述

这是一个基于插件的 bash 命令扩展系统。添加新功能只需要在 `bash_hooks/` 目录下创建新的 Python 文件。

## 快速开始

### 1. 创建新插件

在 `middleware/bash_hooks/` 目录下创建新文件，例如 `dangerous_commands.py`:

```python
from .base import BashHook, HookResult

class DangerousCommandsHook(BashHook):
    priority = 20  # 数字越小越先执行
    name = "DangerousCommands"
    description = "Block dangerous commands"
    
    def check_command(self, command: str, context):
        # 检查命令
        if "rm -rf /" in command:
            return HookResult.block_command(
                "❌ 'rm -rf /' is extremely dangerous!"
            )
        
        # 允许命令
        return HookResult.allow_command()
```

### 2. 重启 Agent

插件会自动加载，无需修改任何其他代码！

## Hook 生命周期

每个 hook 有三个方法：

1. **check_command(command, context)** - 必须实现
   - 在命令执行前调用
   - 返回 `HookResult` 决定是否允许执行

2. **on_command_success(command, output, context)** - 可选
   - 命令执行成功后调用
   - 可用于日志、统计等

3. **on_command_error(command, error, context)** - 可选
   - 命令执行失败后调用
   - 可用于错误处理、告警等

## HookResult 类型

```python
# 允许命令执行
HookResult.allow_command()

# 拦截命令
HookResult.block_command("错误消息")

# 允许但停止后续 hooks
HookResult.allow_command(metadata={"info": "..."})
result.continue_chain = False
```

## Hook 配置

### Priority（优先级）

- 数字越小越先执行
- 建议范围：
  - 1-20: 安全检查
  - 21-50: 业务逻辑
  - 51-100: 日志、统计

### Enabled（启用状态）

```python
class MyHook(BashHook):
    enabled = True  # 可以动态控制
```

### 接收配置参数

```python
class MyHook(BashHook):
    def __init__(self, workspace_root, my_param=None, **kwargs):
        super().__init__(workspace_root, **kwargs)
        self.my_param = my_param
```

传递配置：

```python
middleware = ExtensibleBashMiddleware(
    workspace_root="/path",
    hook_config={"my_param": "value"}
)
```

## 已有插件示例

### 1. PathSecurityHook (`path_security.py`)

限制命令只能在工作目录内执行：

- 拦截 `cd /tmp`
- 拦截 `cd ../`
- 拦截访问外部文件

### 2. CommandLoggerHook (`command_logger.py`)

记录所有命令到日志文件：

- 记录命令执行时间
- 记录命令输出
- 记录错误信息

## 完整示例

创建一个限制危险命令的插件：

```python
# middleware/bash_hooks/dangerous_commands.py

from .base import BashHook, HookResult

class DangerousCommandsHook(BashHook):
    priority = 15
    name = "DangerousCommands"
    description = "Block dangerous system commands"
    
    # 危险命令列表
    DANGEROUS = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
    ]
    
    def check_command(self, command: str, context):
        # 检查是否包含危险命令
        for dangerous in self.DANGEROUS:
            if dangerous in command:
                return HookResult.block_command(
                    f"❌ DANGER: '{dangerous}' is blocked\n"
                    f"   This command could damage your system.\n"
                    f"   If you really need to run it, ask the user first."
                )
        
        return HookResult.allow_command()
    
    def on_command_error(self, command, error, context):
        # 记录被拦截的危险命令
        if "DANGER" in error:
            print(f"[SECURITY] Blocked dangerous command: {command}")
```

## Context 对象

`context` 包含以下信息：

```python
{
    "tool_call": {...},  # 工具调用信息
    "request": {...},    # 请求对象
}
```

## 调试

启用调试输出：

```python
# 在 hook 中添加 print
def check_command(self, command, context):
    print(f"[{self.name}] Checking: {command}")
    ...
```

## 最佳实践

1. **单一职责**：每个 hook 只做一件事
2. **快速检查**：避免耗时操作
3. **清晰错误**：提供详细的错误信息
4. **异常处理**：捕获并记录异常
5. **可配置**：通过参数控制行为

## 插件开发模板

```python
from .base import BashHook, HookResult
from typing import Any

class MyCustomHook(BashHook):
    priority = 50
    name = "MyCustomHook"
    description = "What this hook does"
    enabled = True
    
    def __init__(self, workspace_root, **kwargs):
        super().__init__(workspace_root, **kwargs)
        # 初始化你的配置
    
    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        # 实现你的检查逻辑
        
        if should_block:
            return HookResult.block_command("Error message")
        
        return HookResult.allow_command()
    
    def on_command_success(self, command: str, output: str, context: dict[str, Any]) -> None:
        # 可选：命令成功后的处理
        pass
    
    def on_command_error(self, command: str, error: str, context: dict[str, Any]) -> None:
        # 可选：命令失败后的处理
        pass
```

## 故障排查

### Hook 没有被加载

1. 检查文件名是否以 `.py` 结尾
2. 检查类是否继承自 `BashHook`
3. 检查 `enabled = True`
4. 查看启动日志中的 `[BashHooks] Loaded` 消息

### Hook 没有生效

1. 检查 `priority` 是否正确
2. 检查 `check_command` 是否返回正确的 `HookResult`
3. 检查是否有其他 hook 提前拦截了命令
4. 添加 `print` 调试输出

### 性能问题

1. 避免在 `check_command` 中进行耗时操作
2. 使用 `continue_chain=False` 提前终止检查链
3. 考虑缓存检查结果
