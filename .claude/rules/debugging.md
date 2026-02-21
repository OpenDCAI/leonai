# Leon 调试经验

## 问题：Agent 卡死，前端无响应

**症状**：
- 用户发送消息后，前端一直等待，没有任何响应
- 后端日志显示 `openai.APIConnectionError: Connection error.`
- 前端没有显示错误信息

**调试步骤**：

1. **检查最新 thread**：
   ```bash
   sqlite3 ~/.leon/leon.db "SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 5"
   ```

2. **查看 thread 消息历史**：
   ```bash
   curl -s http://127.0.0.1:8001/api/threads/<thread_id> | python3 -m json.tool
   ```
   - 如果最后一条是 HumanMessage，说明 Agent 没有回复

3. **检查后端日志**：
   ```bash
   tail -100 /tmp/leon-backend.log | grep -E "error|Error|Exception"
   ```
   - 找到 `APIConnectionError` 或其他异常

4. **验证 API 可达性**：
   ```bash
   curl -s http://<api_endpoint>/v1/models
   ```

**根本原因**：

在 `services/web/main.py` 的 `event_stream()` 函数中：
- Agent stream 的异常发生在 `await task` (line 1270)
- 只捕获了 `StopAsyncIteration`，其他异常（如 `APIConnectionError`）会传播出去
- 虽然外层有 `except Exception` (line 1444)，但异常发生在 while 循环内部
- **问题**：异常导致 generator 直接停止，没有 yield error 事件给前端

**解决方案**：

在 while 循环中添加异常捕获：

```python
# services/web/main.py:1267-1282
while True:
    try:
        chunk = await task
        task = asyncio.create_task(stream_gen.__anext__())
        app.state.thread_tasks[thread_id] = task
    except StopAsyncIteration:
        break
    except Exception as stream_error:  # ← 新增
        import traceback
        traceback.print_exc()
        yield {"event": "error", "data": json.dumps({"error": str(stream_error)}, ensure_ascii=False)}
        break
```

**效果**：
- ✅ API 连接错误会被捕获并发送 `error` 事件给前端
- ✅ 前端显示错误信息，用户知道发生了什么
- ✅ 不会出现"卡死"的假象

**关键教训**：
- 异步 generator 的异常处理需要在 `await` 点捕获
- 不能依赖外层的 `except Exception`，因为 generator 会在异常时直接停止
- 前端必须能看到后端的错误信息，否则用户无法判断问题
