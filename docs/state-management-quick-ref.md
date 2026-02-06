# Leon 状态管理快速参考

> 快速查询表和决策树
> 日期：2026-02-06

---

## 一、快速问答

### Q1: LangGraph 的 StateGraph 是状态机吗？

**A: 不是。**

- LangGraph 是**执行流程图**（DAG），不是**状态机**
- 状态是隐式的，通过节点执行推导
- 无法显式查询 Agent 的运行时状态

### Q2: Leon 的 Queue Mode 覆盖了状态机吗？

**A: 没有。**

- Queue Mode 是**消息队列**，决定"消息何时被处理"
- 状态机是**运行时管理**，决定"Agent 处于什么状态"
- 两者是正交的，可以同时存在

### Q3: Leon 需要额外的状态机吗？

**A: 是的。**

**原因**：
- 用户需要知道 Agent 在做什么
- UI 需要显示 Agent 的状态
- 系统需要基于状态做决策（如"只在 IDLE 时接受新任务"）

### Q4: 应该选择哪个实现方案？

**A: 方案 A（轻量级状态机）。**

| 方案 | 复杂度 | 改动量 | 兼容性 | 推荐 |
|------|--------|--------|--------|------|
| A: 轻量级 | 低 | 小 | ✅ | ✅ |
| B: 深度集成 | 高 | 大 | ⚠️ | ❌ |

---

## 二、架构决策树

```
需要显式管理 Agent 状态？
  ├─ 是 → 需要状态机
  │   ├─ 需要与 LangGraph 深度集成？
  │   │   ├─ 是 → 方案 B（复杂）
  │   │   └─ 否 → 方案 A（推荐）
  │   └─ 选择方案 A
  │       ├─ 创建 AgentRuntime 类
  │       ├─ 在 LeonAgent 中集成
  │       ├─ 在 middleware 中更新状态
  │       └─ 在 TUI 中显示状态
  └─ 否 → 继续使用 LangGraph + Queue Mode
```

---

## 三、功能对比速查表

### 消息队列（Queue Mode）

| 模式 | 行为 | 何时使用 |
|------|------|---------|
| STEER | 立即注入，改变执行方向 | 用户想改变当前任务 |
| FOLLOWUP | 等当前任务完成后处理 | 用户想排队新任务 |
| COLLECT | 收集多条消息，合并处理 | 用户想批量处理 |
| STEER_BACKLOG | 注入 + 保留为 followup | 用户想立即处理 + 保留备份 |
| INTERRUPT | 中断当前执行 | 用户想停止当前任务 |

### 运行时状态（需要实现）

| 状态 | 含义 | 可以接受新任务 |
|------|------|---------------|
| INITIALIZING | 初始化中 | ❌ |
| READY | 就绪 | ✅ |
| ACTIVE | 正在执行 | ⚠️ (取决于 Queue Mode) |
| IDLE | 空闲 | ✅ |
| SUSPENDED | 暂停 | ❌ |
| TERMINATED | 已终止 | ❌ |
| ERROR | 错误 | ❌ |
| RECOVERING | 恢复中 | ❌ |

---

## 四、实现清单

### P0（必须，2-3 天）

- [ ] 创建 `middleware/state/runtime.py`
  - [ ] `AgentState` 枚举
  - [ ] `AgentFlags` 数据类
  - [ ] `AgentRuntime` 类
- [ ] 在 `agent.py` 中集成 `AgentRuntime`
  - [ ] 在 `__init__` 中初始化
  - [ ] 在 `invoke()` 中更新状态
- [ ] 在 middleware 中设置标志
  - [ ] `SteeringMiddleware` 设置 `isWaiting`
  - [ ] `CommandMiddleware` 设置 `isBlocked`
- [ ] 在 TUI 中显示状态
  - [ ] 显示当前状态
  - [ ] 显示关键标志

### P1（应该，3-5 天）

- [ ] 实现上下文压缩
  - [ ] 创建 `middleware/context/compactor.py`
  - [ ] 检测何时需要压缩
  - [ ] 实现摘要逻辑
- [ ] 实现资源预算管理
  - [ ] 创建 `middleware/resource/manager.py`
  - [ ] 跟踪 token 使用
  - [ ] 实现预算检查

### P2（可以，5-7 天）

- [ ] 实现错误恢复策略
  - [ ] 创建 `middleware/recovery/handler.py`
  - [ ] 分类错误
  - [ ] 实现恢复策略
- [ ] 实现状态事件系统
  - [ ] 状态变化事件
  - [ ] 标志变化事件
  - [ ] 事件订阅机制

---

## 五、代码示例

### 最小化实现（P0）

```python
# middleware/state/runtime.py
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any

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
    tokenUsage: int = 0
    tokenLimit: int = 100000

class AgentRuntime:
    def __init__(self):
        self.state = AgentState.READY
        self.flags = AgentFlags()
        self._state_changed_callbacks: list[Callable] = []
    
    def transition(self, new_state: AgentState) -> None:
        if self._is_valid_transition(self.state, new_state):
            self.state = new_state
            self._emit_state_changed(new_state)
        else:
            raise ValueError(f"Invalid transition: {self.state} → {new_state}")
    
    def set_flag(self, flag_name: str, value: Any) -> None:
        if hasattr(self.flags, flag_name):
            setattr(self.flags, flag_name, value)
        else:
            raise ValueError(f"Unknown flag: {flag_name}")
    
    def on_state_changed(self, callback: Callable) -> None:
        self._state_changed_callbacks.append(callback)
    
    def _emit_state_changed(self, new_state: AgentState) -> None:
        for callback in self._state_changed_callbacks:
            callback(new_state)
    
    def _is_valid_transition(self, from_state: AgentState, to_state: AgentState) -> bool:
        # 简化的转移规则
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
# agent.py
from middleware.state.runtime import AgentRuntime, AgentState

class LeonAgent:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.runtime = AgentRuntime()
    
    def invoke(self, message: str, thread_id: str = "default") -> dict:
        # 状态转移：READY → ACTIVE
        self.runtime.transition(AgentState.ACTIVE)
        
        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": thread_id}},
            )
            
            # 状态转移：ACTIVE → IDLE
            self.runtime.transition(AgentState.IDLE)
            
            return result
        except Exception as e:
            # 状态转移：ACTIVE → ERROR
            self.runtime.transition(AgentState.ERROR)
            self.runtime.set_flag("hasError", True)
            raise
```

---

## 六、与 OpenClaw 的对齐进度

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

## 七、常见问题

### Q: 为什么不直接用 LangGraph 的状态？

A: LangGraph 的状态是 TypedDict，用于在节点间传递数据。它不是运行时状态管理，无法表达"Agent 暂停"、"Agent 等待"等概念。

### Q: Queue Mode 和状态机有什么区别？

A: 
- Queue Mode：决定"消息何时被处理"（消息层）
- 状态机：决定"Agent 处于什么状态"（执行层）

### Q: 为什么要在 middleware 中设置标志？

A: 因为 middleware 最接近执行逻辑，能准确捕捉 Agent 的实时状态。

### Q: 状态机会影响性能吗？

A: 不会。状态转移只是简单的赋值操作，开销可以忽略。

---

## 八、相关文件

- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/state-management-analysis.md` - 完整分析
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/openclaw-architecture-analysis.md` - OpenClaw 分析
- `/Users/apple/Desktop/project/v1/文稿/project/leon/agent.py` - Agent 核心
- `/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/queue/middleware.py` - Queue Mode

