# TUI Bug 修复总结

## 修复的 3 个关键 Bug

### Bug #1: 消息不能流式输出 ❌ → ✅

**问题**：AI 回复一次性显示，没有流式效果

**原因**：
- 只在 `last_msg` 更新，没有追踪内容变化
- 没有强制刷新 Markdown 组件

**修复**：
```python
# 之前：只看最后一条消息
last_msg = chunk["messages"][-1]

# 现在：遍历所有消息，追踪内容变化
for msg in chunk["messages"]:
    content = getattr(msg, "content", "")
    if content and content != last_content:  # 检测到新内容
        self._current_assistant_msg.update_content(content)
        last_content = content  # 记录已显示内容
```

### Bug #2: 消息顺序错乱 ❌ → ✅

**问题**：回复被前置，工具调用被后置

**原因**：
- 只处理 `last_msg`，忽略了消息的时间顺序
- 工具调用和结果的处理逻辑分散

**修复**：
```python
# 现在：按时间顺序处理所有消息
for msg in chunk["messages"]:
    if msg_class == "AIMessage":
        # 1. 先显示 AI 文本
        # 2. 再显示工具调用
    elif msg_class == "ToolMessage":
        # 3. 最后显示工具结果
```

### Bug #3: 用户消息延迟渲染 ❌ → ✅

**问题**：发送消息后要等 AI 回复才能看到自己的消息

**原因**：
- 用户消息在 `run_worker` 之前添加，但 UI 没有立即刷新
- Worker 是异步的，UI 更新被延迟

**修复**：
```python
# 添加用户消息
messages_container.mount(UserMessage(content))
chat_container.scroll_end(animate=False)

# 强制刷新 UI（关键！）
self.refresh()

# 再启动 worker
self.run_worker(self._process_message(content), exclusive=False)
```

## 核心改进

### 1. 流式输出机制

```python
# AssistantMessage.update_content()
self._markdown.update(prefix + content)
self._markdown.refresh()  # 强制刷新
```

### 2. 时间顺序保证

```
用户消息 → AI 文本 → 工具调用 → 工具结果 → AI 继续
```

### 3. 即时反馈

```python
# exclusive=False 允许 UI 保持响应
self.run_worker(..., exclusive=False)
```

## 测试验证

运行以下命令测试：

```bash
uv run python leon_cli.py
```

测试场景：
1. ✅ 发送消息立即显示
2. ✅ AI 回复逐字流式输出
3. ✅ 工具调用在 AI 回复后显示
4. ✅ 工具结果在工具调用后显示
5. ✅ 多轮对话顺序正确

## 对比 deepagents-cli

| 特性 | deepagents-cli | leon_cli (修复后) |
|------|----------------|-------------------|
| 流式输出 | ✅ | ✅ |
| 时间顺序 | ✅ | ✅ |
| 即时反馈 | ✅ | ✅ |
| 消息渲染 | Markdown | Markdown |
| 代码量 | ~1000 行 | ~230 行 |

## 技术细节

### stream_mode="values"

LangChain 的 stream 返回完整状态快照，包含所有历史消息。

**关键点**：
- 每个 chunk 包含完整的 messages 列表
- 需要追踪已显示内容避免重复
- 通过内容对比检测新增部分

### 消息去重

```python
self._shown_tool_calls = set()      # 工具调用 ID
self._shown_tool_results = set()    # 工具结果 ID
last_content = ""                   # AI 文本内容
```

### UI 刷新时机

1. **用户消息**: 立即刷新 (`self.refresh()`)
2. **AI 流式**: 每次内容更新刷新
3. **工具调用**: 添加时刷新
4. **工具结果**: 添加时刷新

## 已知限制

- ⚠️ 历史记录功能未实现
- ⚠️ 自动补全功能未实现
- ⚠️ 工具审批界面未实现

这些是高级功能，不影响核心使用。
