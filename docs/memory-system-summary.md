# OpenClaw 记忆系统 - 关键设计总结

> 快速参考指南
> 日期：2026-02-05

---

## 核心概念

### 三层记忆架构

```
┌─────────────────────────────────────────┐
│  即时记忆（Immediate）                   │
│  - 当前 LLM 上下文窗口                   │
│  - 当前目标、最近消息、关键信息          │
│  - 更新频率：每个 LLM 调用前             │
└─────────────────────────────────────────┘
                    ↑↓
┌─────────────────────────────────────────┐
│  短期记忆（Short-term）                  │
│  - 当前会话内存                          │
│  - 完整消息历史、执行状态、变量          │
│  - 生命周期：会话级别                    │
└─────────────────────────────────────────┘
                    ↑↓
┌─────────────────────────────────────────┐
│  长期记忆（Long-term）                   │
│  - 持久化存储（数据库/文件系统）        │
│  - 交互历史、学到的模式、知识库          │
│  - 生命周期：跨会话                      │
└─────────────────────────────────────────┘
```

---

## 上下文压缩（Context Compacting）

### 触发条件

```python
# 任意一个满足即触发
token_count > 100000              # Token 数超过阈值
message_count > 500               # 消息数超过阈值
time_since_last_compact > 3600s   # 距离上次压缩超过 1 小时
```

### 三种压缩策略

| 策略 | 机制 | 适用场景 |
|------|------|---------|
| **摘要压缩** | 用 LLM 生成摘要，替换原消息 | 通用，信息损失中等 |
| **选择性删除** | 计算重要性分数，删除低分消息 | 消息数多，信息损失低 |
| **分层压缩** | 按任务分层，不同层级不同压缩策略 | 长会话，信息损失最低 |

### 压缩过程

```
1. 进入 COMPACTING 状态
   ↓
2. 暂停新的工具调用
   ↓
3. 执行压缩（选择策略）
   ↓
4. 更新统计数据
   ↓
5. 退出 COMPACTING 状态，返回 ACTIVE
```

---

## 记忆的存储和检索

### 存储层次

```
即时记忆 (内存)
    ↓ (会话级别)
短期记忆 (内存)
    ↓ (会话结束时)
长期记忆 (数据库/文件系统)
```

### 检索方式

| 方式 | 用途 | 实现 |
|------|------|------|
| **相似度检索** | 找相关的历史记忆 | 向量化 + 向量数据库 |
| **关键词检索** | 找包含特定词的记忆 | 全文搜索 |
| **上下文检索** | 基于当前上下文找记忆 | 过滤器查询 |

---

## 关键设计决策

### 1. 压缩时机：被动 + 主动混合

```python
# 被动触发（优先）
if token_count > threshold:
    compact()

# 主动触发（备用）
if time_since_last_compact > max_interval:
    compact()
```

**优点**：及时响应，避免浪费，但不过度压缩

### 2. 压缩策略：分层优先

```python
# 分层压缩的优势
- 最近消息：保留全部（最重要）
- 活跃任务：保留摘要（中等重要）
- 已完成任务：保留关键点（低重要）
- 历史任务：保留统计（最低重要）
```

### 3. 长期记忆粒度：任务级

```python
# 存储单位：任务
{
    "task_id": "...",
    "task_type": "code_review",
    "status": "completed",
    "result": "...",
    "timestamp": 1234567890,
    "patterns": [...],
    "errors": [...],
}
```

**优点**：存储量适中，检索精度好，易于统计

### 4. 重要性评分

```python
importance = 0.0

# 错误信息（高）
if "error" in content:
    importance += 0.8

# 决策点（高）
if any(keyword in content for keyword in ["决定", "选择", "方案"]):
    importance += 0.6

# 工具调用（中）
if role == "tool":
    importance += 0.4

# 重复信息（低）
if is_duplicate(msg):
    importance -= 0.5

return max(0.0, min(1.0, importance))
```

---

## 与 Leon 现有架构的融合

### 新增中间件

```python
middleware/
├── memory/
│   ├── memory_manager.py      # 核心管理器
│   ├── storage.py             # 存储层（数据库）
│   ├── retrieval.py           # 检索层（向量 + 关键词）
│   ├── compaction.py          # 压缩层（三种策略）
│   └── models.py              # 数据模型
```

### 集成点

```python
# agent.py
class LeonAgent:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.session_manager = SessionManager(memory_manager=...)
    
    async def run(self, user_input):
        # 1. 检索相关长期记忆
        relevant_memories = self.memory_manager.retrieve(user_input)
        
        # 2. 构建上下文（包含长期记忆）
        context = self.build_context(relevant_memories)
        
        # 3. 执行 Agent
        response = await self.agent_loop(context)
        
        # 4. 检查是否需要压缩
        if self.memory_manager.should_compact():
            self.memory_manager.compact()
        
        # 5. 更新长期记忆
        self.memory_manager.update_after_task(response)
```

---

## 实现优先级

### P0 - 必须实现

- [ ] 三层记忆结构
- [ ] 基本消息历史管理
- [ ] 简单摘要压缩
- [ ] 会话级别的短期记忆

### P1 - 应该实现

- [ ] 分层压缩
- [ ] 选择性删除
- [ ] 重要性评分
- [ ] 长期记忆持久化

### P2 - 可以实现

- [ ] 相似度检索
- [ ] 关键词检索
- [ ] 模式提取
- [ ] 统计分析

---

## 代码示例

### 最小化实现

```python
from dataclasses import dataclass
from uuid import uuid4
import time

@dataclass
class Memory:
    id: str
    content: str
    timestamp: float
    importance: float = 0.5

class MemoryManager:
    def __init__(self):
        self.short_term: list[Memory] = []
        self.long_term: list[Memory] = []
    
    def add_message(self, content: str, importance: float = 0.5):
        mem = Memory(
            id=str(uuid4()),
            content=content,
            timestamp=time.time(),
            importance=importance,
        )
        self.short_term.append(mem)
    
    def should_compact(self) -> bool:
        # 简单触发条件
        return len(self.short_term) > 100
    
    def compact(self):
        # 简单压缩：保留重要的消息
        sorted_mems = sorted(
            self.short_term,
            key=lambda x: x.importance,
            reverse=True
        )
        
        # 保留前 50 个最重要的
        self.short_term = sorted_mems[:50]
    
    def save_to_long_term(self):
        # 会话结束时保存
        self.long_term.extend(self.short_term)
        self.short_term = []
```

---

## 常见问题

### Q1: 压缩会丢失信息吗？

**A**: 会，但是有策略：
- 摘要压缩：信息损失 ~30%，但保留关键点
- 选择性删除：信息损失 ~10%，只删除重复/低重要性
- 分层压缩：信息损失 ~5%，最近消息不压缩

### Q2: 何时应该压缩？

**A**: 
- 被动：Token 数 > 80% 容量时
- 主动：距离上次压缩 > 1 小时时
- 不压缩：正在执行关键工具调用时

### Q3: 长期记忆怎么防止无限增长？

**A**: 三种遗忘策略：
- 基于时间：删除超过 N 天的记忆
- 基于重要性：删除重要性 < 阈值的记忆
- 基于容量：超过容量时删除最旧的

### Q4: 如何保证压缩后的上下文仍然有效？

**A**:
- 保留关键决策点
- 保留错误信息
- 保留最近的消息
- 测试压缩后的 Agent 行为

---

## 参考文档

- 完整分析：`/Users/apple/Desktop/project/v1/文稿/project/leon/docs/memory-system-analysis.md`
- OpenClaw 架构：`/Users/apple/Desktop/project/v1/文稿/project/leon/docs/openclaw-architecture-analysis.md`
- Agent 生物学模型：`/Users/apple/Desktop/project/v1/文稿/project/leon/docs/agent-biology-model.md`

