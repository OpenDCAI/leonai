# 计划：实现 SummaryStore 摘要持久化

## 背景

### 问题
Leon 的 `MemoryMiddleware` 存在关键 bug：
- `_cached_summary` 和 `_compact_up_to_index` 只存在内存中
- 重启后这些变量重置，导致：
  1. 丢失已生成的摘要（浪费 API 成本）
  2. 从 checkpointer 加载完整历史（上下文爆炸）

### 解决方案
实现独立的 `SummaryStore` 持久化存储，参考 Leon 现有的 `TerminalStore` 模式。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储架构 | 独立的 SummaryStore | 与 Checkpointer 分离，遵循 Leon 现有模式 |
| 摘要类型 | SystemMessage | LLM 注意力系数高 |
| Split Turn | 实现 | 处理大消息，双层摘要（参考 OpenClaw） |
| 压缩阈值 | 上下文窗口的 70% | 基于 Token，可配置 |
| 恢复策略 | 重试 + 重建 | 失败时重试操作；数据损坏时从 checkpointer 重建 |
| thread_id 要求 | 必需 | 不降级到内存缓存 |

## 架构设计

### SummaryStore 表结构
```sql
CREATE TABLE summaries (
    summary_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    compact_up_to_index INTEGER NOT NULL,
    compacted_at INTEGER NOT NULL,
    is_split_turn BOOLEAN DEFAULT FALSE,
    split_turn_prefix TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Split Turn 检测
- **触发条件**：新内容 Token 数 > 上下文窗口的 50%
- **策略**：将当前轮次分割为 prefix（摘要化）+ suffix（保留）
- **输出**：双层摘要（历史摘要 + 轮次前缀摘要）

### 摘要生命周期
1. 上下文超过 70% 阈值时生成摘要
2. 保存到 SummaryStore（标记旧摘要为 inactive）
   - 写入失败：重试写入（最多 3 次）
3. 重启时从 SummaryStore 恢复
   - 读取失败：重试读取（最多 3 次）
   - 数据损坏：从 checkpointer 重建摘要

## 实现步骤

### 前置条件
```bash
git checkout dev
git pull origin dev
```

### Phase 1: 创建 SummaryStore
**新增文件**：`middleware/memory/summary_store.py`

参考 `sandbox/terminal.py` 的 TerminalStore 模式：
- 使用 `_connect()` 辅助函数，设置 `PRAGMA busy_timeout=30000`
- 启用 WAL 模式：`PRAGMA journal_mode=WAL`
- 创建 `SummaryData` dataclass 保证类型安全

**核心方法**：
- `save_summary()`：标记旧摘要为 `is_active=FALSE`，插入新摘要
  - 内置重试机制：写入失败时最多重试 3 次
- `get_latest_summary()`：查询 `WHERE is_active=TRUE ORDER BY created_at DESC LIMIT 1`
  - 内置重试机制：读取失败时最多重试 3 次
  - 返回 `None` 表示无摘要或数据损坏
- `list_summaries()`：返回所有摘要用于审计

### Phase 2: 添加 Split Turn 检测
**修改文件**：`middleware/memory/compactor.py`

**Split Turn 检测逻辑**：
- 计算 `new_content_tokens = total_tokens - summarizable_tokens`
- 计算 `max_history_tokens = context_limit * 0.5 * 1.2`（50% 预算 + 20% 安全边际）
- 如果 `new_content_tokens > max_history_tokens`：触发 Split Turn

**核心方法**：
- `detect_split_turn()`：返回 `(is_split_turn: bool, turn_prefix_messages: list)`
- `_extract_turn_prefix()`：在 Token 边界分割 `to_keep`，使用 `_adjust_boundary()` 避免切断 tool_calls
- `compact_with_split_turn()`：生成两个摘要：
  1. 历史摘要（标准指令）
  2. 轮次前缀摘要（特殊指令：关注原始请求）
  - 合并格式：`{历史摘要}\n\n---\n\n**Turn Context (split turn):**\n\n{前缀摘要}`
- `should_compact()`：添加 `threshold` 参数（默认 0.7）

**轮次前缀指令**：
```
"This summary covers the prefix of a split turn. Focus on the original request,
early progress, and any details needed to understand the retained suffix."
```

### Phase 3: 集成 SummaryStore
**修改文件**：`middleware/memory/middleware.py`

**3.1 初始化**：
- 在 `__init__` 中添加 `db_path` 和 `checkpointer` 参数
- 初始化 `self.summary_store = SummaryStore(db_path)`
- 存储 `self.checkpointer` 用于重建功能
- 添加 `self._compaction_threshold` 参数（默认 0.7）

**3.2 摘要恢复**：
- 在 `awrap_model_call()` 中：检查 `if self._cached_summary is None`
- 从 `request.config.configurable.thread_id` 提取 thread_id
- **要求 thread_id**：缺失时抛出 `ValueError`（不降级）
- 调用 `_restore_summary_from_store(thread_id)`

**3.3 恢复逻辑**（`_restore_summary_from_store()`）：
- 调用 `summary_store.get_latest_summary()`（内置重试）
- 如果返回 `None`：
  - 情况 1：无摘要（首次运行）→ 跳过恢复
  - 情况 2：数据损坏 → 调用 `_rebuild_summary_from_checkpointer()`
- 如果返回摘要：验证数据完整性
  - 验证失败：调用 `_rebuild_summary_from_checkpointer()`
  - 验证成功：更新缓存变量

**3.4 重建逻辑**（`_rebuild_summary_from_checkpointer()`）：
- 加载 checkpoint：`checkpointer.get({"configurable": {"thread_id": thread_id}})`
- 从 `checkpoint["channel_values"]["messages"]` 提取消息
- 检查是否需要压缩：`should_compact(estimated, context_limit, threshold)`
- 如果需要：运行完整压缩逻辑（包括 Split Turn 检测）
- 保存重建的摘要到 SummaryStore
- 更新缓存变量

**3.5 压缩更新**（`_do_compact()`）：
- 生成摘要后，调用 `detect_split_turn()`
- 如果是 Split Turn：调用 `compact_with_split_turn()`，更新 `to_keep` 移除 prefix
- 保存到 SummaryStore：`summary_store.save_summary(thread_id, summary, ...)`（内置重试）
  - 保存失败（重试 3 次后仍失败）：记录错误，继续执行（摘要丢失但不影响功能）
- 在第一条保留消息上添加 metadata：
  ```python
  first_kept_msg.additional_kwargs["leon_metadata"] = {
      "compression_triggered": True,
      "summary_id": summary_id,
      "compact_up_to_index": ...,
      "compacted_at": len(messages),
      "is_split_turn": is_split_turn,
      "compacted_time": timestamp,
  }
  ```

**3.6 缓存摘要使用**：
- 使用缓存摘要时：`[SystemMessage(summary)] + messages[compact_up_to_index:]`
- 格式：`"[Conversation Summary]\n{summary_text}"`

### Phase 4: 更新配置
**修改文件**：`agent.py`

在 `create_leon_agent()` 中：
- 设置 `db_path = Path.home() / ".leon" / "leon.db"`
- 传递给 MemoryMiddleware：
  - `db_path=db_path`
  - `checkpointer=checkpointer`（引用现有的 checkpointer 变量）
  - `compaction_threshold=0.7`

## 关键文件

**新增**：
- `middleware/memory/summary_store.py`

**修改**：
- `middleware/memory/compactor.py`
- `middleware/memory/middleware.py`
- `agent.py`

## 验证方案

### 1. 单元测试
创建 `tests/middleware/memory/test_summary_store.py`：
- 测试 `save_summary()` 和 `get_latest_summary()`
- 测试多个摘要（只有最新的是 active）
- 测试 Split Turn 摘要存储
- 运行：`uv run pytest tests/middleware/memory/test_summary_store.py -v`

### 2. 集成测试
创建 `/tmp/test_summary_persistence.py`：
- Phase 1：发送 60 条消息触发压缩
- Phase 2：重启 agent，验证摘要恢复
- Phase 3：检查 SummaryStore，验证摘要存在
- 预期：看到 `[Memory] Restored summary from store` 日志

### 3. Split Turn 测试
创建 `/tmp/test_split_turn.py`：
- 发送超大消息（50k 字符 ≈ 25k tokens）
- 检查 SummaryStore 中 `is_split_turn=True`
- 预期：看到双层摘要格式

### 4. 重建测试
创建 `/tmp/test_summary_rebuild.py`：
- Phase 1：创建带摘要的对话
- Phase 2：手动损坏数据库中的摘要
- Phase 3：重启，验证触发重建
- 预期：看到 `[Memory] Rebuilding summary from checkpointer...`

### 5. 数据库验证
```bash
sqlite3 ~/.leon/leon.db "SELECT summary_id, thread_id, is_split_turn, is_active, created_at FROM summaries ORDER BY created_at DESC LIMIT 5;"
```
预期：每个 thread 只有一个 `is_active=1` 的摘要

### 6. TUI 验证
```bash
uv run leonai
# 1. 发送大量消息触发压缩
# 2. 重启 TUI
# 3. 继续对话，应该看到摘要恢复
# 4. 使用时间旅行查看 [Conversation Summary] 消息
```

## 边界情况

### 1. 多次压缩
- **行为**：第二次压缩标记第一个摘要为 `is_active=FALSE`
- **结果**：只使用最新摘要，旧摘要保留用于审计

### 2. Split Turn 边界
- **问题**：可能在 AIMessage(tool_calls) 和 ToolMessage 之间切断
- **解决**：使用现有的 `_adjust_boundary()` 方法找到安全分割点

### 3. 并发写入
- **问题**：多个进程写入 summaries 表
- **解决**：WAL 模式 + `busy_timeout=30000` + 事务写入

### 4. 缺失 thread_id
- **行为**：抛出 `ValueError` 并提供清晰的错误信息
- **理由**：持久化存储需要 thread_id，不降级

### 5. SummaryStore 读取失败
- **触发**：数据库锁定、权限问题等
- **恢复**：自动重试读取（最多 3 次）
- **降级**：重试失败后，检查是否数据损坏
  - 数据损坏：调用 `_rebuild_summary_from_checkpointer()`
  - 其他错误：记录错误，继续运行但不使用摘要

### 6. SummaryStore 写入失败
- **触发**：数据库锁定、磁盘满、权限问题等
- **恢复**：自动重试写入（最多 3 次）
- **降级**：重试失败后，记录错误，继续运行（摘要丢失但不影响功能）

### 7. 数据损坏
- **触发**：摘要数据不完整或格式错误
- **恢复**：从 checkpointer 重建摘要
- **重建逻辑**：
  - 加载完整历史
  - 重新运行压缩逻辑
  - 保存新摘要到 SummaryStore

### 8. Checkpointer 不可用
- **行为**：记录错误，跳过重建
- **结果**：继续运行但不使用摘要（功能降级但可用）

### 9. 压缩阈值边界情况
- **70% 太激进**：用户可配置更低（如 0.6）
- **70% 太保守**：用户可配置更高（如 0.8）
- **模型特定**：不同模型可能需要不同阈值

## 未来增强

### 1. Pruning Metadata
在被 prune 的消息上添加 metadata：
```python
msg.additional_kwargs["leon_metadata"] = {
    "pruned": True,
    "original_length": original_length,
    "pruned_method": "soft-trim" | "hard-clear",
}
```

### 2. 工具失败收集（参考 OpenClaw）
在 Split Turn 摘要中收集和格式化工具失败：
- 最多 8 个失败
- 每个失败最多 240 字符
- 附加到轮次前缀摘要

### 3. 文件操作追踪（参考 OpenClaw）
在 Split Turn 中追踪文件读写：
- `<read-files>` 部分
- `<modified-files>` 部分

### 4. 前端 UI 改进
在 TUI 中使用 metadata：
- `compression_triggered=True` 时显示 "Compressed" 徽章
- `is_split_turn=True` 时显示 "Split Turn" 徽章
- 默认折叠长工具输出

### 5. 自适应分块比例
根据消息大小动态调整 Split Turn 比例：
- 大消息 → 更小的前缀比例（0.15）
- 小消息 → 更大的前缀比例（0.4）

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| SummaryStore 写入失败 | 摘要丢失 | 自动重试 3 次；失败后记录错误继续运行 |
| SummaryStore 读取失败 | 无法恢复摘要 | 自动重试 3 次；检查数据损坏并重建 |
| 数据损坏 | 摘要不可用 | 从 checkpointer 重建摘要 |
| 摘要重建慢 | 失败恢复时延迟 | 只在数据损坏时发生；可异步重建 |
| Split Turn 检测不准确 | 上下文不完整或过度摘要 | 使用 20% 安全边际；保守估算 Token |
| 数据库迁移问题 | 旧数据不兼容 | 使用 `CREATE TABLE IF NOT EXISTS`；仅增量 schema 变更 |
| 性能开销 | 每次请求额外的数据库查询 | 只在缓存为空时查询一次；使用连接池 |
| Checkpointer 不可用 | 数据损坏时无法重建 | 记录错误并继续；功能降级但可用 |
| 摘要文本过大 | 存储膨胀 | 摘要通常 <5KB；远小于完整历史 |
| thread_id 要求破坏现有代码 | 兼容性问题 | 清晰的错误信息指导用户添加 thread_id |

## 关键设计理由

### 为什么使用独立的 SummaryStore？
- **关注点分离**：消息（checkpointer）vs 摘要（SummaryStore）
- **查询效率**：通过 thread_id 直接查找，无需扫描消息
- **历史保留**：Checkpointer 保留完整历史用于时间旅行
- **审计追踪**：所有摘要带时间戳保留
- **一致性**：遵循 Leon 现有模式（TerminalStore、LeaseStore）

### 为什么要求 thread_id？
- **持久化存储需要标识**：没有 thread_id 无法保存/恢复
- **显式优于隐式**：清晰的错误优于静默降级
- **Leon 的设计**：所有有状态操作都使用 thread_id

### 为什么从 Checkpointer 重建？
- **数据完整性**：Checkpointer 是真实来源
- **自动恢复**：无需手动干预
- **适用场景**：只在数据损坏时重建，不是每次失败都重建
- **重试优先**：先重试操作，重试失败且确认数据损坏才重建

### 为什么是 70% 阈值？
- **平衡**：为响应留足空间（30%）同时最大化上下文
- **可配置**：用户可根据使用场景调整
- **行业实践**：类似 OpenClaw 的方法
