# Leon 状态管理分析 - 执行总结

## 核心发现

### 1. LangGraph 不是状态机

LangGraph 的 `StateGraph` 是一个**执行流程图（DAG）**，而不是传统的状态机：

- **节点**：执行单元（模型调用、工具执行等）
- **边**：节点间的转移
- **状态**：TypedDict，在节点间流动
- **问题**：状态是隐式的，无法显式查询和管理

**关键区别**：
```
LangGraph: START → [Model] → [Tool] → [Model] → END
           (执行流程图，隐式状态)

OpenClaw: READY → ACTIVE → IDLE → TERMINATED
          (显式状态机，可观测)
```

### 2. Queue Mode 只是消息队列

Leon 已实现的 Queue Mode（steer/followup/collect）解决的是**消息层**的问题：
- 决定"消息何时被处理"
- 不决定"Agent 处于什么状态"

**与状态机的关系**：
```
Queue Mode（消息层）
  ↓
  决定消息何时注入
  ↓
Agent State（执行层）
  ↓
  决定是否可以处理消息
```

两者是**正交的**，可以同时存在。

### 3. Leon 需要额外的状态机

**原因**：
1. 用户需要知道 Agent 在做什么（UI 显示）
2. 系统需要基于状态做决策（如"只在 IDLE 时接受新任务"）
3. OpenClaw 的状态机是必需的功能

**关键差距**：

| 功能 | OpenClaw | Leon | 优先级 |
|------|----------|------|--------|
| 消息队列 | ✅ | ✅ | - |
| 运行时状态 | ✅ | ❌ | P0 |
| 状态标志位 | ✅ | ❌ | P0 |
| 上下文压缩 | ✅ | ❌ | P1 |
| 资源预算 | ✅ | ❌ | P2 |
| 错误恢复 | ✅ | ❌ | P2 |

---

## 建议方案

### 方案 A：轻量级状态机（推荐）

**架构**：
```
LeonAgent
  ├─ AgentRuntime（新增）
  │   ├─ state: AgentState
  │   ├─ flags: AgentFlags
  │   └─ transition(new_state)
  ├─ Middleware Stack（现有）
  │   └─ 在关键点更新状态
  └─ LangGraph StateGraph（现有）
      └─ 执行逻辑
```

**优点**：
- 最小化改动
- 与 LangGraph 兼容
- 快速实现（2-3 天）
- 易于测试和扩展

**缺点**：
- 状态管理与 LangGraph 分离
- 需要手动同步

### 方案 B：深度集成（不推荐）

**架构**：
```
LeonStateGraph（扩展 LangGraph）
  ├─ agent_state: AgentState
  ├─ agent_flags: AgentFlags
  └─ invoke() 中自动管理状态
```

**优点**：
- 状态与 LangGraph 深度集成
- 更清晰的架构

**缺点**：
- 复杂度高
- 改动量大
- 升级 LangGraph 时可能破坏
- 维护成本高

---

## 实现路线图

### P0（必须，2-3 天）

1. 创建 `middleware/state/runtime.py`
   - `AgentState` 枚举（8 个状态）
   - `AgentFlags` 数据类（7 个标志）
   - `AgentRuntime` 类（状态转移逻辑）

2. 在 `agent.py` 中集成
   - 初始化 `AgentRuntime`
   - 在 `invoke()` 中更新状态

3. 在 middleware 中设置标志
   - `SteeringMiddleware` 设置 `isWaiting`
   - `CommandMiddleware` 设置 `isBlocked`

4. 在 TUI 中显示状态
   - 显示当前状态
   - 显示关键标志

### P1（应该，3-5 天）

1. 实现上下文压缩
   - 检测何时需要压缩
   - 实现摘要逻辑

2. 实现资源预算管理
   - 跟踪 token 使用
   - 实现预算检查

### P2（可以，5-7 天）

1. 实现错误恢复策略
   - 分类错误
   - 实现恢复策略

2. 实现状态事件系统
   - 状态变化事件
   - 事件订阅机制

---

## 与 OpenClaw 的对齐进度

### 当前（2026-02-06）

```
✅ Queue Mode（steer/followup/collect）
✅ Session 管理 + Checkpointer
❌ 运行时状态机
❌ 上下文压缩
❌ 资源预算
```

### 3 个月后（2026-05-06）

```
✅ Queue Mode
✅ Session 管理 + Checkpointer
✅ 运行时状态机（P0）
✅ 上下文压缩（P1）
⚠️ 资源预算（P2，可选）
```

### 6 个月后（2026-08-06）

```
✅ 完整的 OpenClaw 功能对齐
✅ 多 Agent 协调（Master-Worker）
✅ 错误恢复策略
✅ 可观测性层
```

---

## 关键代码片段

### AgentRuntime 类（最小化实现）

```python
from enum import Enum
from dataclasses import dataclass

class AgentState(Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ERROR = "error"
    RECOVERING = "recovering"

@dataclass
class AgentFlags:
    isStreaming: bool = False
    isCompacting: bool = False
    isWaiting: bool = False
    isBlocked: bool = False
    canInterrupt: bool = True
    hasError: bool = False
    needsRecovery: bool = False

class AgentRuntime:
    def __init__(self):
        self.state = AgentState.READY
        self.flags = AgentFlags()
    
    def transition(self, new_state: AgentState) -> None:
        if self._is_valid_transition(self.state, new_state):
            self.state = new_state
        else:
            raise ValueError(f"Invalid transition: {self.state} → {new_state}")
    
    def set_flag(self, flag_name: str, value: bool) -> None:
        setattr(self.flags, flag_name, value)
    
    def _is_valid_transition(self, from_state: AgentState, to_state: AgentState) -> bool:
        valid_transitions = {
            AgentState.INITIALIZING: [AgentState.READY, AgentState.ERROR],
            AgentState.READY: [AgentState.ACTIVE, AgentState.TERMINATED],
            AgentState.ACTIVE: [AgentState.IDLE, AgentState.SUSPENDED, AgentState.ERROR],
            AgentState.IDLE: [AgentState.ACTIVE, AgentState.TERMINATED],
            AgentState.SUSPENDED: [AgentState.ACTIVE, AgentState.TERMINATED],
            AgentState.ERROR: [AgentState.RECOVERING, AgentState.TERMINATED],
            AgentState.RECOVERING: [AgentState.READY, AgentState.TERMINATED],
            AgentState.TERMINATED: [],
        }
        return to_state in valid_transitions.get(from_state, [])
```

### 在 LeonAgent 中集成

```python
class LeonAgent:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.runtime = AgentRuntime()
    
    def invoke(self, message: str, thread_id: str = "default") -> dict:
        self.runtime.transition(AgentState.ACTIVE)
        
        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": thread_id}},
            )
            
            self.runtime.transition(AgentState.IDLE)
            return result
        except Exception as e:
            self.runtime.transition(AgentState.ERROR)
            self.runtime.set_flag("hasError", True)
            raise
```

---

## 相关文件

- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/state-management-analysis.md` - 完整分析（21KB）
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/state-management-quick-ref.md` - 快速参考
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/openclaw-architecture-analysis.md` - OpenClaw 分析
- `/Users/apple/Desktop/project/v1/文稿/project/leon/agent.py` - Agent 核心
- `/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/queue/middleware.py` - Queue Mode 实现

---

## 结论

1. **LangGraph 不是状态机** → 需要额外的状态管理层
2. **Queue Mode 不覆盖状态机** → 两者是正交的
3. **Leon 需要状态机** → 用户体验和系统决策的必需
4. **推荐方案 A** → 轻量级、快速、兼容
5. **P0 优先级** → 2-3 天内可实现基础功能

