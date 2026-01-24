# Leon TUI 快速测试指南

## 已修复的问题

1. ✅ **输入框无法输入** - 重写了 ChatInput 组件，参考 deepagents-cli 实现
2. ✅ **Enter 键处理** - 正确实现了 Enter 发送，Shift+Enter/Ctrl+J 换行
3. ✅ **消息事件传递** - 修复了事件冒泡机制

## 测试步骤

### 1. 简单测试（无需 agent）

```bash
uv run python test_tui_simple.py
```

这个测试应用：
- 可以输入文本
- Enter 发送消息
- Shift+Enter 换行
- 显示用户消息和回复
- 输入 `/quit` 退出

### 2. 完整 TUI 测试

```bash
./run_tui.sh
```

或

```bash
uv run python leon_cli.py
```

## 使用说明

### 输入控制

- **Enter**: 发送消息
- **Shift+Enter** 或 **Ctrl+J**: 插入换行
- **Ctrl+C**: 退出程序

### 特殊命令

- `/clear`: 清空对话历史
- `/exit` 或 `/quit`: 退出

## 核心改进

### ChatInput 组件

```python
# 之前的问题：
- 直接继承 TextArea，事件处理不完整
- 没有正确的消息传递机制

# 现在的实现：
- ChatTextArea: 处理键盘事件
- ChatInput: 容器组件，包含提示符 ">" 和输入框
- 正确的事件冒泡: ChatTextArea.Submitted → ChatInput.Submitted → LeonApp
```

### 事件流

```
用户按 Enter
  ↓
ChatTextArea._on_key() 捕获
  ↓
发送 ChatTextArea.Submitted(value)
  ↓
ChatInput.on_chat_text_area_submitted() 接收
  ↓
发送 ChatInput.Submitted(value)
  ↓
LeonApp.on_chat_input_submitted() 处理
```

## 对比 deepagents-cli

| 特性 | deepagents-cli | leon_cli (当前) |
|------|----------------|-----------------|
| 输入框 | ✓ 完整实现 | ✓ 核心功能已实现 |
| 历史记录 | ✓ 上下键浏览 | ⚠️ 待实现 |
| 自动补全 | ✓ 文件/命令 | ⚠️ 待实现 |
| 消息渲染 | ✓ Markdown | ✓ Markdown |
| 工具可视化 | ✓ | ✓ |
| 流式输出 | ✓ | ✓ |

## 已知限制

1. **历史记录**: 暂未实现上下键浏览历史
2. **自动补全**: 暂未实现文件路径和命令补全
3. **工具审批**: 暂未实现交互式审批界面

这些是高级功能，核心交互已经可用。

## 故障排除

### 输入框仍然无法输入

1. 检查终端是否支持 Textual
2. 尝试运行简单测试: `uv run python test_tui_simple.py`
3. 确保依赖已安装: `uv sync`

### 显示异常

```bash
# 清除终端
clear

# 重新运行
./run_tui.sh
```

### 按键无响应

- 确保焦点在输入框（应该看到光标闪烁）
- 尝试点击输入区域
- 检查是否有其他进程占用键盘输入

## 下一步改进

如果基础功能正常，可以添加：

1. **历史记录**: 实现 HistoryManager
2. **自动补全**: 实现 CompletionManager
3. **更好的错误处理**: 显示详细错误信息
4. **主题切换**: 支持多种颜色主题
