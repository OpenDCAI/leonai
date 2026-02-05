# OpenClaw/moltbot 记忆系统分析

> 基于 moltbot/clawebot 研究，为 Leon 记忆系统设计提供参考
> 日期：2026-02-05

---

## 一、记忆系统的三层架构

OpenClaw 的记忆系统采用**三层分离**的设计，对应不同的时间尺度和用途：

### 1.1 长期记忆（Long-term Memory）

**存储位置**：持久化存储（数据库、文件系统）

**特点**：
- 跨会话保存
- 容量大，访问慢
- 包含历史决策、学到的模式、用户偏好

**内容**：
```python
class LongTermMemory:
    # 用户交互历史
    user_profiles: dict          # 用户偏好、历史任务
    interaction_history: list    # 所有历史对话
    
    # 学到的模式
    learned_patterns: dict       # 任务模式、解决方案
    error_patterns: dict         # 常见错误及解决方案
    
    # 知识库
    knowledge_base: dict         # 项目知识、API 文档
    code_snippets: dict          # 可复用代码片段
    
    # 统计数据
    statistics: dict             # 性能指标、成功率
```

**访问方式**：
- 会话初始化时加载相关部分
- 定期更新（任务完成后）
- 检索（相似度搜索、关键词查询）

### 1.2 短期记忆（Short-term Memory）/ 工作记忆

**存储位置**：内存（当前会话）

**特点**：
- 会话级别
- 容量小，访问快
- 包含当前任务的上下文

**内容**：
```python
class ShortTermMemory:
    # 当前会话的消息历史
    messages: list[Message]      # 完整对话历史
    
    # 当前执行上下文
    current_task: Task           # 当前任务
    task_stack: list[Task]       # 任务栈（嵌套任务）
    
    # 变量和状态
    variables: dict              # 局部变量
    execution_state: dict        # 执行状态
    
    # 临时结果
    intermediate_results: dict   # 中间计算结果
    tool_outputs: dict           # 工具调用结果缓存
```

**生命周期**：
- 会话开始时创建
- 会话结束时清空
- 可选：部分内容归档到长期记忆

### 1.3 即时记忆（Immediate Memory）/ 注意力焦点

**存储位置**：当前 LLM 上下文窗口

**特点**：
- 最小化，只包含必要信息
- 最快访问（直接在 prompt 中）
- 包含当前步骤的关键信息

**内容**：
```python
class ImmediateMemory:
    # 当前步骤的关键信息
    current_goal: str            # 当前目标
    recent_messages: list        # 最近 N 条消息
    
    # 关键决策点
    decision_context: dict       # 决策所需的上下文
    
    # 工具调用结果
    last_tool_result: Any        # 最后一个工具调用的结果
    
    # 错误信息
    last_error: str | None       # 最后的错误信息
```

**更新频率**：每个 LLM 调用前更新

---

## 二、上下文压缩（Context Compacting）机制

### 2.1 压缩触发条件

```python
class CompactionTrigger:
    # 基于 token 数
    token_threshold: int = 100000      # 超过此数量触发压缩
    
    # 基于消息数
    message_threshold: int = 500       # 超过此数量触发压缩
    
    # 基于时间
    time_threshold: float = 3600       # 1 小时触发一次压缩
    
    # 基于重要性
    importance_threshold: float = 0.3  # 重要性低于此值的消息可删除
    
    def should_compact(self, session: Session) -> bool:
        return (
            session.token_count > self.token_threshold or
            len(session.messages) > self.message_threshold or
            time.now() - session.last_compact_time > self.time_threshold
        )
```

### 2.2 压缩策略

#### **策略 1：摘要压缩（Summarization）**

```
原始消息序列：
[User: 做一个 API 接口]
[Assistant: 我来帮你设计...]
[Tool: 读取文件 X]
[Assistant: 文件内容是...]
[Tool: 创建文件 Y]
[Assistant: 已创建...]
... (100+ 条消息)

压缩后：
[System: 用户要求创建 API 接口。已完成以下步骤：
  1. 分析了现有代码结构
  2. 设计了新的 API 端点
  3. 创建了实现文件
  关键决策：使用 FastAPI 框架
  当前状态：等待用户反馈]
```

**实现**：
```python
class SummarizationCompactor:
    def compact(self, messages: list[Message]) -> list[Message]:
        # 1. 分组消息（按任务或时间窗口）
        groups = self.group_messages(messages)
        
        # 2. 对每组生成摘要
        summaries = []
        for group in groups:
            summary = self.generate_summary(group)
            summaries.append(summary)
        
        # 3. 保留关键消息（第一条、最后一条、错误消息）
        key_messages = self.extract_key_messages(messages)
        
        # 4. 合并
        return summaries + key_messages
    
    def generate_summary(self, group: list[Message]) -> Message:
        # 使用 LLM 生成摘要
        prompt = f"总结以下对话：\n{group}"
        summary = llm.call(prompt)
        return Message(role="system", content=summary)
```

#### **策略 2：选择性删除（Selective Deletion）**

```python
class SelectiveDeletion:
    def compact(self, messages: list[Message]) -> list[Message]:
        # 计算每条消息的重要性分数
        scores = []
        for msg in messages:
            score = self.calculate_importance(msg)
            scores.append(score)
        
        # 删除低重要性消息
        threshold = self.calculate_threshold(scores)
        return [msg for msg, score in zip(messages, scores) 
                if score >= threshold]
    
    def calculate_importance(self, msg: Message) -> float:
        # 重要性因素：
        # - 是否包含错误信息（高）
        # - 是否包含决策点（高）
        # - 是否包含工具调用（中）
        # - 是否是重复信息（低）
        
        importance = 0.0
        
        if "error" in msg.content.lower():
            importance += 0.8
        
        if any(keyword in msg.content for keyword in 
               ["决定", "选择", "方案", "设计"]):
            importance += 0.6
        
        if msg.role == "tool":
            importance += 0.4
        
        # 检查重复性
        if self.is_duplicate(msg):
            importance -= 0.5
        
        return max(0.0, min(1.0, importance))
```

#### **策略 3：分层压缩（Hierarchical Compression）**

```
第 1 层：最近消息（保留全部）
├─ 最近 50 条消息

第 2 层：活跃任务（保留摘要）
├─ 当前任务的所有消息 → 摘要

第 3 层：已完成任务（保留关键点）
├─ 已完成任务 → 仅保留决策点和结果

第 4 层：历史任务（保留统计）
├─ 历史任务 → 仅保留统计数据
```

**实现**：
```python
class HierarchicalCompactor:
    def compact(self, messages: list[Message]) -> list[Message]:
        # 分层
        recent = messages[-50:]                    # 第 1 层
        active_task = self.extract_active_task(messages)  # 第 2 层
        completed_tasks = self.extract_completed_tasks(messages)  # 第 3 层
        history = self.extract_history(messages)   # 第 4 层
        
        # 压缩每层
        recent_compressed = recent  # 不压缩
        active_compressed = self.summarize(active_task)
        completed_compressed = self.extract_key_points(completed_tasks)
        history_compressed = self.extract_statistics(history)
        
        # 合并
        return (recent_compressed + active_compressed + 
                completed_compressed + history_compressed)
```

### 2.3 压缩过程中的状态管理

```python
class CompactionProcess:
    def compact(self, session: Session) -> None:
        # 1. 进入压缩状态
        session.state = AgentState.COMPACTING
        session.flags.isCompacting = True
        
        # 2. 暂停新的工具调用
        # （不接收新的 tool_use 消息）
        
        # 3. 执行压缩
        try:
            compressed_messages = self.compress_messages(session.messages)
            session.messages = compressed_messages
            
            # 4. 更新统计
            session.compression_count += 1
            session.last_compact_time = time.now()
            
        except Exception as e:
            # 压缩失败，回滚
            session.state = AgentState.ERROR
            raise
        
        finally:
            # 5. 退出压缩状态
            session.flags.isCompacting = False
            session.state = AgentState.ACTIVE
```

---

## 三、记忆的存储和检索

### 3.1 存储架构

```
┌─────────────────────────────────────────────────────────┐
│                  记忆存储层                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  即时记忆         │  │  短期记忆         │            │
│  │  (内存)          │  │  (内存)          │            │
│  │  - 当前目标      │  │  - 消息历史      │            │
│  │  - 最近结果      │  │  - 执行状态      │            │
│  │  - 错误信息      │  │  - 变量          │            │
│  └──────────────────┘  └──────────────────┘            │
│           ↓                      ↓                      │
│  ┌──────────────────────────────────────┐              │
│  │      会话上下文（Session Context）    │              │
│  │  - 消息历史（可压缩）                 │              │
│  │  - 执行状态                          │              │
│  │  - 检查点                            │              │
│  └──────────────────────────────────────┘              │
│           ↓ (会话结束时)                               │
│  ┌──────────────────────────────────────┐              │
│  │    长期记忆（数据库/文件系统）        │              │
│  │  - 交互历史                          │              │
│  │  - 学到的模式                        │              │
│  │  - 知识库                            │              │
│  │  - 统计数据                          │              │
│  └──────────────────────────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 检索机制

#### **基于相似度的检索**

```python
class SimilarityRetrieval:
    def retrieve(self, query: str, top_k: int = 5) -> list[Memory]:
        # 1. 对查询进行向量化
        query_embedding = self.embed(query)
        
        # 2. 从长期记忆中检索相似的记忆
        candidates = self.search_similar(query_embedding, top_k=top_k*2)
        
        # 3. 重排序（考虑时间衰减）
        ranked = self.rerank_with_time_decay(candidates)
        
        # 4. 返回前 k 个
        return ranked[:top_k]
    
    def search_similar(self, embedding: list[float], top_k: int) -> list[Memory]:
        # 使用向量数据库（如 Pinecone、Weaviate）
        results = self.vector_db.query(embedding, top_k=top_k)
        return results
    
    def rerank_with_time_decay(self, candidates: list[Memory]) -> list[Memory]:
        # 最近的记忆权重更高
        now = time.now()
        for candidate in candidates:
            age = now - candidate.timestamp
            decay_factor = math.exp(-age / (7 * 24 * 3600))  # 7 天衰减
            candidate.score *= decay_factor
        
        return sorted(candidates, key=lambda x: x.score, reverse=True)
```

#### **基于关键词的检索**

```python
class KeywordRetrieval:
    def retrieve(self, keywords: list[str]) -> list[Memory]:
        # 1. 从长期记忆中检索包含关键词的记忆
        results = []
        for keyword in keywords:
            matches = self.search_by_keyword(keyword)
            results.extend(matches)
        
        # 2. 去重和排序
        unique_results = list(set(results))
        return sorted(unique_results, key=lambda x: x.relevance, reverse=True)
    
    def search_by_keyword(self, keyword: str) -> list[Memory]:
        # 使用全文搜索（如 Elasticsearch）
        return self.search_engine.search(keyword)
```

#### **基于上下文的检索**

```python
class ContextualRetrieval:
    def retrieve(self, context: dict) -> list[Memory]:
        # 基于当前上下文检索相关记忆
        # 例如：当前任务类型、用户、项目等
        
        filters = {
            "task_type": context.get("task_type"),
            "user_id": context.get("user_id"),
            "project_id": context.get("project_id"),
        }
        
        return self.search_with_filters(filters)
```

---

## 四、记忆的更新和遗忘

### 4.1 更新策略

```python
class MemoryUpdate:
    def update_after_task_completion(self, task: Task, result: Any) -> None:
        # 1. 记录任务完成
        self.long_term_memory.add_interaction({
            "task_id": task.id,
            "task_type": task.type,
            "status": "completed",
            "result": result,
            "timestamp": time.now(),
        })
        
        # 2. 提取学到的模式
        patterns = self.extract_patterns(task)
        self.long_term_memory.add_patterns(patterns)
        
        # 3. 更新统计数据
        self.long_term_memory.update_statistics(task)
    
    def update_after_error(self, error: Exception, context: dict) -> None:
        # 1. 记录错误
        self.long_term_memory.add_error({
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": time.now(),
        })
        
        # 2. 提取错误模式
        error_pattern = self.extract_error_pattern(error, context)
        self.long_term_memory.add_error_pattern(error_pattern)
```

### 4.2 遗忘策略

```python
class ForgetStrategy:
    # 基于时间的遗忘
    def forget_by_time(self, max_age: float) -> None:
        # 删除超过 max_age 的记忆
        now = time.now()
        to_delete = [
            mem for mem in self.long_term_memory.memories
            if now - mem.timestamp > max_age
        ]
        for mem in to_delete:
            self.long_term_memory.delete(mem.id)
    
    # 基于重要性的遗忘
    def forget_by_importance(self, min_importance: float) -> None:
        # 删除重要性低于阈值的记忆
        to_delete = [
            mem for mem in self.long_term_memory.memories
            if mem.importance < min_importance
        ]
        for mem in to_delete:
            self.long_term_memory.delete(mem.id)
    
    # 基于容量的遗忘
    def forget_by_capacity(self, max_size: int) -> None:
        # 当超过容量时，删除最旧的记忆
        if len(self.long_term_memory.memories) > max_size:
            excess = len(self.long_term_memory.memories) - max_size
            oldest = sorted(
                self.long_term_memory.memories,
                key=lambda x: x.timestamp
            )[:excess]
            for mem in oldest:
                self.long_term_memory.delete(mem.id)
```

---

## 五、记忆与上下文管理的关系

### 5.1 上下文构建流程

```
┌─────────────────────────────────────────────────────────┐
│              会话开始                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  1. 从长期记忆检索相关信息                               │
│     - 用户偏好                                          │
│     - 项目历史                                          │
│     - 学到的模式                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  2. 初始化短期记忆                                       │
│     - 创建空消息历史                                    │
│     - 初始化执行状态                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  3. 构建即时记忆（Prompt）                              │
│     - System Prompt（包含用户偏好、项目信息）           │
│     - 最近消息                                          │
│     - 当前目标                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  4. 发送给 LLM                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              任务执行中                                  │
│  - 更新短期记忆（消息、状态）                           │
│  - 监控 token 使用                                      │
│  - 检查是否需要压缩                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  如果需要压缩：                                          │
│  - 暂停执行                                             │
│  - 压缩消息历史                                         │
│  - 更新即时记忆                                         │
│  - 继续执行                                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              会话结束                                    │
│  - 保存检查点                                           │
│  - 更新长期记忆                                         │
│  - 清空短期记忆                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 上下文大小管理

```python
class ContextSizeManager:
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.reserved_tokens = 10000  # 为响应预留
        self.available_tokens = max_tokens - self.reserved_tokens
    
    def calculate_context_size(self, session: Session) -> int:
        # 计算当前上下文的 token 数
        size = 0
        
        # System Prompt
        size += self.count_tokens(session.system_prompt)
        
        # 消息历史
        for msg in session.messages:
            size += self.count_tokens(msg.content)
        
        # 工具定义
        size += self.count_tokens(self.serialize_tools())
        
        return size
    
    def should_compact(self, session: Session) -> bool:
        current_size = self.calculate_context_size(session)
        return current_size > self.available_tokens * 0.8  # 80% 时触发
    
    def get_available_space(self, session: Session) -> int:
        current_size = self.calculate_context_size(session)
        return max(0, self.available_tokens - current_size)
```

---

## 六、Leon 的记忆系统实现建议

### 6.1 分阶段实现

**Phase 1：基础记忆框架**
- 实现三层记忆结构
- 基本的消息历史管理
- 简单的压缩策略（摘要）

**Phase 2：高级压缩**
- 实现分层压缩
- 选择性删除
- 重要性评分

**Phase 3：长期记忆**
- 实现持久化存储
- 相似度检索
- 模式提取

**Phase 4：集成优化**
- 与 Session 管理集成
- 与 State 管理集成
- 性能优化

### 6.2 集成点

```python
# 在 Leon 的 middleware 中添加
middleware/
├── memory/                 # 新增记忆系统
│   ├── __init__.py
│   ├── memory_manager.py   # 记忆管理器
│   ├── storage.py          # 存储层
│   ├── retrieval.py        # 检索层
│   ├── compaction.py       # 压缩层
│   └── models.py           # 数据模型
├── session/                # 会话管理
│   ├── manager.py
│   └── persistence.py
└── state/                  # 状态管理
    ├── machine.py
    └── flags.py
```

### 6.3 与现有 Leon 架构的融合

```python
# agent.py 中的集成
class LeonAgent:
    def __init__(self, ...):
        # 初始化记忆系统
        self.memory_manager = MemoryManager(
            workspace_root=workspace_root,
            max_long_term_size=1000000,  # 1MB
        )
        
        # 初始化会话管理
        self.session_manager = SessionManager(
            memory_manager=self.memory_manager,
        )
    
    async def run(self, user_input: str) -> str:
        # 1. 获取或创建会话
        session = self.session_manager.get_or_create_session()
        
        # 2. 从长期记忆检索相关信息
        relevant_memories = self.memory_manager.retrieve(user_input)
        
        # 3. 构建上下文
        context = self.build_context(session, relevant_memories)
        
        # 4. 执行 Agent 逻辑
        response = await self.agent_loop(context)
        
        # 5. 更新记忆
        self.memory_manager.update_after_task(session, response)
        
        # 6. 检查是否需要压缩
        if self.memory_manager.should_compact(session):
            self.memory_manager.compact(session)
        
        return response
```

---

## 七、关键设计决策

### 7.1 压缩时机

| 触发条件 | 优点 | 缺点 |
|---------|------|------|
| 主动（定期） | 可预测，不影响用户体验 | 可能不必要 |
| 被动（超过阈值） | 及时，避免浪费 | 可能中断执行 |
| 混合 | 平衡 | 复杂度高 |

**建议**：混合策略，优先使用被动触发，但设置最大间隔。

### 7.2 压缩策略选择

| 策略 | 适用场景 | 信息损失 |
|------|---------|---------|
| 摘要 | 通用 | 中等 |
| 选择性删除 | 消息数多 | 低 |
| 分层 | 长会话 | 低 |

**建议**：默认使用分层压缩，可配置。

### 7.3 长期记忆的粒度

| 粒度 | 存储量 | 检索精度 |
|------|--------|---------|
| 消息级 | 大 | 高 |
| 任务级 | 中 | 中 |
| 会话级 | 小 | 低 |

**建议**：任务级，可选消息级备份。

---

## 八、参考实现

### 8.1 最小化记忆系统

```python
from dataclasses import dataclass
from typing import Any
import json
from pathlib import Path

@dataclass
class Memory:
    id: str
    content: str
    timestamp: float
    importance: float = 0.5
    metadata: dict = None

class SimpleMemoryManager:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.short_term: list[Memory] = []
        self.long_term_path = storage_path / "long_term.jsonl"
    
    def add_short_term(self, content: str, importance: float = 0.5) -> None:
        mem = Memory(
            id=str(uuid4()),
            content=content,
            timestamp=time.now(),
            importance=importance,
        )
        self.short_term.append(mem)
    
    def save_to_long_term(self, memories: list[Memory]) -> None:
        with open(self.long_term_path, "a") as f:
            for mem in memories:
                f.write(json.dumps({
                    "id": mem.id,
                    "content": mem.content,
                    "timestamp": mem.timestamp,
                    "importance": mem.importance,
                }) + "\n")
    
    def compact(self, max_messages: int = 100) -> None:
        if len(self.short_term) > max_messages:
            # 保留最重要的消息
            sorted_mems = sorted(
                self.short_term,
                key=lambda x: x.importance,
                reverse=True
            )
            
            # 保留前 50% 的重要消息 + 最后 10 条
            keep = sorted_mems[:max_messages//2] + self.short_term[-10:]
            self.short_term = keep
```

---

## 九、相关文件

- `/Users/apple/Desktop/project/v1/文稿/project/leon/agent.py` - Agent 核心
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/openclaw-architecture-analysis.md` - OpenClaw 架构
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/agent-biology-model.md` - Agent 生物学模型
- `/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/task/middleware.py` - Task 中间件

