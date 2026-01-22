# SafeBashMiddleware - Bash 命令路径安全限制

## 功能说明

`SafeBashMiddleware` 为 Leon Agent 提供了 bash 命令的路径安全限制功能，确保所有命令只能在指定的工作目录内执行。

## 安全规则

### ✅ 允许的操作
- 在工作目录内的所有命令
- 相对路径操作（不使用 `../`）
- 系统命令（如 `ls`, `pwd`, `echo` 等）

### ❌ 禁止的操作
- `cd` 到工作目录外的绝对路径（如 `cd /tmp`）
- 使用 `../` 向上遍历目录（如 `cd ../`）
- 访问工作目录外的绝对路径（如 `cat /etc/passwd`）
- 任何试图逃出工作目录的路径操作

## 使用方法

### 1. 基本使用

```python
from agent import create_leon

# 创建 Agent（默认使用 SafeBashMiddleware）
leon = create_leon(workspace_root="/path/to/workspace")

# 安全命令会正常执行
leon.get_response("Execute: ls -la")  # ✅ 成功

# 不安全命令会被拦截
leon.get_response("Execute: cd /tmp")  # ❌ 被拦截
```

### 2. 配置选项

```python
from middleware.safe_bash import SafeBashMiddleware

middleware = SafeBashMiddleware(
    workspace_root="/path/to/workspace",  # 必需：工作目录
    allow_system_python=True,             # 允许使用系统 Python
    strict_mode=True,                     # 严格模式：拦截所有 ../
)
```

## 测试验证

### 运行完整测试

```bash
# 测试路径验证逻辑
uv run python test_middleware_direct.py

# 测试与 Agent 集成
uv run python test_simple.py
```

### 测试结果示例

```
✅ 安全     | ls -la
✅ 安全     | pwd
✅ 安全     | echo 'hello'
✅ 拦截     | cd /tmp
✅ 拦截     | cd ../
✅ 拦截     | cat /etc/passwd
✅ 拦截     | ls /Users/apple/Desktop
```

## 错误提示示例

当命令被拦截时，Agent 会收到详细的错误信息：

```
❌ SECURITY ERROR: Cannot cd to '/tmp'
   Reason: Path is outside workspace
   Workspace: /Users/apple/Desktop/project/v1/文稿/project/leon/workspace
   Attempted: /tmp
   💡 You can only execute commands within the workspace directory.
```

## 工作原理

1. **拦截工具调用**：`wrap_tool_call` 方法拦截所有 bash 工具调用
2. **路径验证**：`_is_safe_command` 方法检查命令是否安全
3. **返回错误**：不安全的命令返回 `ToolMessage` 错误，不会被执行
4. **Agent 解释**：Agent 收到错误后，用自然语言向用户解释

## 实现细节

### 路径检查逻辑

```python
def _is_safe_command(self, command: str) -> tuple[bool, str]:
    # 1. 检查 cd 到绝对路径
    # 2. 检查 ../ 路径遍历
    # 3. 检查访问工作目录外的绝对路径
    # 4. 返回 (is_safe, error_message)
```

### 与 ShellToolMiddleware 的关系

`SafeBashMiddleware` 继承自 `ShellToolMiddleware`，在其基础上添加了：
- 路径安全验证
- 详细的错误提示
- 工作目录限制

## 注意事项

1. **必须指定 workspace_root**：与 `LocalBashMiddleware` 不同，`SafeBashMiddleware` 要求明确指定工作目录
2. **严格模式**：默认启用，会拦截所有包含 `../` 的命令
3. **系统命令**：`/bin/`, `/usr/` 等系统路径不受限制
4. **错误处理**：被拦截的命令不会执行，Agent 会收到错误消息

## 与其他 Middleware 的对比

| 特性 | LocalBashMiddleware | SafeBashMiddleware |
|------|---------------------|-------------------|
| 路径限制 | ❌ 无 | ✅ 严格限制 |
| 工作目录 | 可选 | 必需 |
| 安全检查 | ❌ 无 | ✅ 完整检查 |
| 错误提示 | 基础 | 详细 |
| 适用场景 | 开发测试 | 生产环境 |

## 未来改进

- [ ] 支持白名单路径配置
- [ ] 支持命令白名单/黑名单
- [ ] 添加审计日志功能
- [ ] 支持更细粒度的权限控制
