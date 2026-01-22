# Bash 插件系统使用指南

## 🎯 核心理念

**添加新功能 = 添加一个新的 Python 文件**

不需要修改现有代码，只需在 `middleware/bash_hooks/` 目录下创建新文件，系统会自动加载。

## 📁 目录结构

```
middleware/
├── bash_hooks/              # 插件目录
│   ├── __init__.py         # 插件系统入口
│   ├── base.py             # BashHook 基类
│   ├── loader.py           # 自动加载器
│   ├── path_security.py    # 路径安全检查插件
│   ├── command_logger.py   # 命令日志插件
│   └── README.md           # 详细文档
├── extensible_bash.py      # 可扩展的 bash middleware
└── ...
```

## 🚀 快速开始

### 1. 创建新插件

在 `middleware/bash_hooks/` 下创建 `my_feature.py`:

```python
from .base import BashHook, HookResult

class MyFeatureHook(BashHook):
    priority = 50
    name = "MyFeature"
    description = "What this hook does"
    
    def check_command(self, command: str, context):
        # 你的检查逻辑
        if should_block:
            return HookResult.block_command("Error message")
        
        return HookResult.allow_command()
```

### 2. 重启 Agent

```bash
uv run chat.py -d ./workspace
```

插件自动加载！查看启动日志：

```
[BashHooks] Loaded: MyFeature (priority=50)
[ExtensibleBash] Loaded 3 hooks: ['PathSecurity', 'MyFeature', 'CommandLogger']
```

## 📝 插件示例

### 示例 1: 拦截危险命令

```python
# middleware/bash_hooks/dangerous_commands.py

from .base import BashHook, HookResult

class DangerousCommandsHook(BashHook):
    priority = 15
    name = "DangerousCommands"
    description = "Block dangerous system commands"
    
    DANGEROUS = ["rm -rf /", "mkfs", "dd if=/dev/zero"]
    
    def check_command(self, command: str, context):
        for dangerous in self.DANGEROUS:
            if dangerous in command:
                return HookResult.block_command(
                    f"❌ '{dangerous}' is extremely dangerous!"
                )
        return HookResult.allow_command()
```

### 示例 2: 命令统计

```python
# middleware/bash_hooks/command_stats.py

from .base import BashHook, HookResult
from collections import defaultdict

class CommandStatsHook(BashHook):
    priority = 100
    name = "CommandStats"
    description = "Track command usage statistics"
    
    def __init__(self, workspace_root, **kwargs):
        super().__init__(workspace_root, **kwargs)
        self.stats = defaultdict(int)
    
    def check_command(self, command: str, context):
        # 统计命令使用次数
        cmd_name = command.split()[0] if command else "unknown"
        self.stats[cmd_name] += 1
        return HookResult.allow_command()
    
    def on_command_success(self, command, output, context):
        print(f"[Stats] Total commands: {sum(self.stats.values())}")
```

### 示例 3: 命令审批

```python
# middleware/bash_hooks/approval_required.py

from .base import BashHook, HookResult

class ApprovalRequiredHook(BashHook):
    priority = 20
    name = "ApprovalRequired"
    description = "Require approval for sensitive commands"
    
    SENSITIVE = ["sudo", "apt install", "pip install"]
    
    def check_command(self, command: str, context):
        for sensitive in self.SENSITIVE:
            if sensitive in command:
                return HookResult.block_command(
                    f"⚠️  Command '{command}' requires user approval.\n"
                    f"   Please ask the user: 'May I run: {command}?'"
                )
        return HookResult.allow_command()
```

## 🔧 Hook API

### BashHook 基类

```python
class BashHook(ABC):
    priority: int = 100        # 执行优先级（越小越先）
    name: str = "UnnamedHook"  # Hook 名称
    description: str = ""      # Hook 描述
    enabled: bool = True       # 是否启用
    
    def __init__(self, workspace_root, **kwargs):
        self.workspace_root = Path(workspace_root)
        self.config = kwargs
    
    @abstractmethod
    def check_command(self, command: str, context: dict) -> HookResult:
        """必须实现：检查命令是否允许执行"""
        pass
    
    def on_command_success(self, command: str, output: str, context: dict):
        """可选：命令执行成功后的回调"""
        pass
    
    def on_command_error(self, command: str, error: str, context: dict):
        """可选：命令执行失败后的回调"""
        pass
```

### HookResult 类型

```python
# 允许命令执行
HookResult.allow_command()

# 拦截命令
HookResult.block_command("错误消息")

# 允许但停止后续 hooks
result = HookResult.allow_command()
result.continue_chain = False

# 带元数据
HookResult.allow_command(metadata={"info": "..."})
```

## 🎨 配置选项

### Priority（优先级）

```python
priority = 10   # 1-20: 安全检查（最先执行）
priority = 50   # 21-50: 业务逻辑
priority = 100  # 51-100: 日志、统计（最后执行）
```

### 接收配置参数

```python
class MyHook(BashHook):
    def __init__(self, workspace_root, my_param=None, **kwargs):
        super().__init__(workspace_root, **kwargs)
        self.my_param = my_param or "default"
```

在 agent.py 中传递配置：

```python
ExtensibleBashMiddleware(
    workspace_root=workspace,
    hook_config={
        "my_param": "custom_value",
        "strict_mode": True,
    }
)
```

### 动态启用/禁用

```python
class MyHook(BashHook):
    enabled = os.getenv("ENABLE_MY_HOOK", "true").lower() == "true"
```

## 📊 已有插件

### 1. PathSecurityHook (priority=10)

**功能**: 限制命令只能在工作目录内执行

**拦截**:
- `cd /tmp` - 跳转到外部目录
- `cd ../` - 向上遍历
- `cat /etc/passwd` - 访问外部文件

**配置**:
```python
hook_config={"strict_mode": True}  # 严格模式
```

### 2. CommandLoggerHook (priority=50)

**功能**: 记录所有命令到日志文件

**日志位置**: `{workspace}/bash_commands.log`

**配置**:
```python
hook_config={"log_file": "custom.log"}
```

## 🧪 测试插件

```bash
# 测试插件系统
uv run python test_extensible_bash.py

# 测试单个插件
uv run python -c "
from middleware.bash_hooks.path_security import PathSecurityHook
from pathlib import Path

hook = PathSecurityHook(workspace_root=Path.cwd())
result = hook.check_command('cd /tmp', {})
print(f'Allowed: {result.allow}')
print(f'Error: {result.error_message}')
"
```

## 🐛 调试技巧

### 1. 查看加载的插件

启动 agent 时查看日志：

```
[BashHooks] Loaded: PathSecurity (priority=10)
[BashHooks] Loaded: CommandLogger (priority=50)
[BashHooks] Total 2 hooks loaded
```

### 2. 添加调试输出

```python
def check_command(self, command: str, context):
    print(f"[{self.name}] Checking: {command}")
    # 你的逻辑
```

### 3. 检查 hook 执行顺序

```python
def check_command(self, command: str, context):
    print(f"[{self.name}] Priority {self.priority}: {command}")
    return HookResult.allow_command()
```

## 📚 完整示例：时间限制插件

```python
# middleware/bash_hooks/time_restriction.py

from datetime import datetime
from .base import BashHook, HookResult

class TimeRestrictionHook(BashHook):
    """只允许在工作时间执行某些命令"""
    
    priority = 30
    name = "TimeRestriction"
    description = "Restrict certain commands to working hours"
    
    RESTRICTED_COMMANDS = ["apt", "sudo", "systemctl"]
    WORK_HOURS = (9, 18)  # 9:00 - 18:00
    
    def check_command(self, command: str, context):
        # 检查是否是受限命令
        is_restricted = any(cmd in command for cmd in self.RESTRICTED_COMMANDS)
        
        if is_restricted:
            current_hour = datetime.now().hour
            start, end = self.WORK_HOURS
            
            if not (start <= current_hour < end):
                return HookResult.block_command(
                    f"⏰ Command '{command}' is restricted to working hours "
                    f"({start}:00 - {end}:00)\n"
                    f"   Current time: {datetime.now().strftime('%H:%M')}\n"
                    f"   💡 Please try again during working hours or ask user for override."
                )
        
        return HookResult.allow_command()
    
    def on_command_error(self, command, error, context):
        if "restricted to working hours" in error:
            # 记录非工作时间的尝试
            with open(self.workspace_root / "after_hours.log", "a") as f:
                f.write(f"{datetime.now()}: {command}\n")
```

## 🎯 最佳实践

1. **单一职责**: 每个 hook 只做一件事
2. **快速检查**: 避免耗时操作（如网络请求）
3. **清晰错误**: 提供详细的错误信息和解决建议
4. **异常处理**: 捕获并记录异常，不要让一个 hook 影响其他
5. **可配置**: 通过参数控制行为，而不是硬编码
6. **文档注释**: 说明 hook 的功能、配置和示例

## 🔄 Hook 执行流程

```
用户命令
    ↓
ExtensibleBashMiddleware.wrap_tool_call
    ↓
按 priority 顺序执行所有 hooks
    ↓
Hook 1 (priority=10): check_command()
    ├─ allow=True, continue_chain=True → 继续
    └─ allow=False → 返回错误，停止
    ↓
Hook 2 (priority=50): check_command()
    ├─ allow=True, continue_chain=True → 继续
    └─ allow=True, continue_chain=False → 允许但停止
    ↓
执行命令
    ↓
成功 → 调用所有 hooks 的 on_command_success()
失败 → 调用所有 hooks 的 on_command_error()
```

## 📦 插件模板

复制此模板开始创建新插件：

```python
# middleware/bash_hooks/your_feature.py

from .base import BashHook, HookResult
from typing import Any

class YourFeatureHook(BashHook):
    """
    简短描述你的 hook 功能
    
    功能：
    - 功能 1
    - 功能 2
    """
    
    priority = 50  # 调整优先级
    name = "YourFeature"
    description = "One-line description"
    enabled = True
    
    def __init__(self, workspace_root, **kwargs):
        super().__init__(workspace_root, **kwargs)
        # 初始化配置
    
    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        """检查命令是否允许执行"""
        
        # 实现你的检查逻辑
        if should_block:
            return HookResult.block_command(
                "❌ Error message\n"
                "   Reason: ...\n"
                "   💡 Suggestion: ..."
            )
        
        return HookResult.allow_command()
    
    def on_command_success(self, command: str, output: str, context: dict[str, Any]) -> None:
        """可选：命令成功后的处理"""
        pass
    
    def on_command_error(self, command: str, error: str, context: dict[str, Any]) -> None:
        """可选：命令失败后的处理"""
        pass
```

## 🎓 进阶用法

### 链式拦截

多个 hooks 可以协同工作：

```python
# Hook 1: 检查路径安全 (priority=10)
# Hook 2: 检查危险命令 (priority=15)
# Hook 3: 记录日志 (priority=50)
```

### 条件启用

```python
class MyHook(BashHook):
    def __init__(self, workspace_root, **kwargs):
        super().__init__(workspace_root, **kwargs)
        # 只在特定条件下启用
        self.enabled = self.workspace_root.name == "production"
```

### 状态共享

通过 metadata 在 hooks 之间共享信息：

```python
# Hook 1
def check_command(self, command, context):
    return HookResult.allow_command(metadata={"checked_by": self.name})

# Hook 2
def check_command(self, command, context):
    # 可以访问之前 hook 的 metadata
    previous_checks = context.get("metadata", {})
    ...
```

## 📖 更多资源

- 详细 API 文档: `middleware/bash_hooks/README.md`
- 示例模板: `middleware/bash_hooks/example_dangerous_commands.py.template`
- 测试脚本: `test_extensible_bash.py`

---

**现在你可以像添加文件一样轻松地扩展 bash 功能了！** 🎉
