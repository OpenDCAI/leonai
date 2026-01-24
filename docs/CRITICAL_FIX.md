# 关键修复：用户消息立即显示

## 问题

用户消息延迟 5 秒才显示（等 AI 回复完才看到）

## 根本原因

```python
# ❌ 错误：用户消息在 async worker 里
self.run_worker(self._handle_user_message(content))

async def _handle_user_message(self, content):
    await mount(UserMessage(content))  # 在 worker 里，延迟执行
    await _process_message(content)
```

**问题**：
- `run_worker()` 启动异步任务
- Worker 可能不会立即执行
- 用户消息被延迟到 worker 开始时才显示

## 正确方案

```python
# ✅ 正确：用户消息同步 mount
def on_chat_input_submitted(self, event):
    # 1. 立即同步 mount（不在 worker 里）
    messages_container.mount(UserMessage(content))
    chat_container.scroll_end(animate=False)
    
    # 2. 强制 UI 刷新
    self.call_after_refresh(lambda: None)
    
    # 3. 再启动 worker 处理 agent
    self.run_worker(self._process_message(content))
```

**关键点**：
- `mount()` 是同步的，立即执行
- 在主事件处理函数中直接调用
- 不放在 worker 里
- `call_after_refresh()` 确保 UI 立即更新

## 执行流程

```
用户按 Enter
  ↓
on_chat_input_submitted()  # 主线程
  ↓
mount(UserMessage)  # ← 立即执行（同步）
  ↓
scroll_end()  # 立即滚动
  ↓
call_after_refresh()  # 强制刷新
  ↓
run_worker(_process_message)  # 启动异步 worker
  ↓
[用户已经看到自己的消息]
  ↓
worker 开始执行
  ↓
流式显示 AI 回复
```

## 对比

| 方案 | 用户消息显示时机 | 延迟 |
|------|----------------|------|
| ❌ 在 worker 里 mount | worker 开始时 | 5 秒 |
| ✅ 同步 mount | 按 Enter 后 | 0 秒 |

## 测试

```bash
uv run python leon_cli.py
```

**预期**：
1. 输入消息，按 Enter
2. **立即**看到自己的消息（< 0.1 秒）
3. AI 开始流式回复

## 完整修复总结

### Bug #1: 流式输出 ✅
- 使用 `stream_mode="updates"`
- 只处理增量消息

### Bug #2: 消息顺序 ✅
- `stream_mode="updates"` 确保按序
- AI 文本 → 工具调用 → 工具结果

### Bug #3: 用户消息延迟 ✅
- **同步 mount**（不在 worker 里）
- `call_after_refresh()` 强制刷新

### Bug #4: TypeError ✅
- 处理多模态 content (list)
- 提取文本块

## 核心教训

**Textual 渲染规则**：
1. `mount()` 是同步的，但 UI 更新是异步的
2. 在 worker 里 mount 会延迟显示
3. 必须在主事件处理函数中 mount
4. 使用 `call_after_refresh()` 强制刷新

**正确模式**：
```python
def on_event(self):
    # 立即渲染
    container.mount(widget)
    self.call_after_refresh(lambda: None)
    
    # 再启动异步处理
    self.run_worker(async_task())
```

**错误模式**：
```python
def on_event(self):
    # ❌ 延迟渲染
    self.run_worker(self._handle_event())

async def _handle_event(self):
    await container.mount(widget)  # 延迟！
```
