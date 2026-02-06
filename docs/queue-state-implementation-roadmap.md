# Leon 队列模式与状态机集成实现路线图

## 阶段 1：基础集成（P0 - 必须实现）

### 1.1 集成 StateMonitor 到 TUI

**目标**：使 TUI 能够访问和使用 StateMonitor

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**修改点**：
```python
# 在 LeonApp.__init__ 中添加
from middleware.monitor import StateMonitor

class LeonApp(App):
    def __init__(self, ...):
        # ... 现有代码 ...
        self.state_monitor = StateMonitor()
        self.state_monitor.mark_ready()  # 初始化为 READY
        
        # 注册状态变化回调
        self.state_monitor.on_state_changed(self._on_state_changed)
```

**工作量**：1-2 小时

---

### 1.2 实现状态感知的消息路由

**目标**：根据 AgentState 而不是 _agent_running 来决定消息路由

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**修改点**：
```python
def on_message_submit(self, content: str) -> None:
    """Handle message submission with state-aware routing"""
    from middleware.monitor import AgentState
    
    current_state = self.state_monitor.state
    
    if current_state == AgentState.ACTIVE:
        # Agent is actively running
        queue_manager = get_queue_manager()
        if self._queue_mode == QueueMode.INTERRUPT:
            # Interrupt: transition to SUSPENDED
            self.state_monitor.transition(AgentState.SUSPENDED)
            if self._agent_worker:
                self._agent_worker.cancel()
            self.notify("⚠ 已暂停")
        else:
            # Queue the message
            queue_manager.enqueue(content, self._queue_mode)
            self.notify(f"✓ 消息已{self._get_mode_label()}")
    
    elif current_state in (AgentState.READY, AgentState.IDLE):
        # Agent is ready to accept new task
        self.state_monitor.transition(AgentState.ACTIVE)
        self._agent_running = True
        self._agent_worker = self.run_worker(
            self._handle_submission(content),
            exclusive=False
        )
    
    elif current_state == AgentState.SUSPENDED:
        # Agent is suspended, queue for later
        queue_manager = get_queue_manager()
        queue_manager.enqueue(content, QueueMode.FOLLOWUP)
        self.notify("✓ 消息已排队（等待恢复）")
    
    else:
        # Other states: cannot accept input
        self.notify(f"⚠ 当前状态 {current_state.value} 无法接受输入")
```

**工作量**：2-3 小时

---

### 1.3 实现状态转移驱动的队列处理

**目标**：当状态转移到 IDLE 时自动处理 followup 队列

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**修改点**：
```python
def _on_state_changed(self, old_state: AgentState, new_state: AgentState) -> None:
    """Handle state transitions"""
    from middleware.monitor import AgentState
    
    if new_state == AgentState.IDLE:
        # Automatically process followup queue when transitioning to IDLE
        self._process_followup_queue()
    
    elif new_state == AgentState.SUSPENDED:
        # Save state for potential recovery
        self._save_suspension_checkpoint()
    
    elif new_state == AgentState.ERROR:
        # Handle error state
        self.notify("⚠ 发生错误")
    
    # Update UI to reflect state change
    self._update_status_display(new_state)
```

**工作量**：1-2 小时

---

### 1.4 修改 Agent 运行完成处理

**目标**：在 Agent 运行完成时转移到 IDLE 状态

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**修改点**：
```python
async def _handle_submission(self, content: str) -> None:
    """Handle message submission asynchronously"""
    # ... 现有代码 ...
    
    try:
        # Run agent
        async for chunk in self.agent.agent.astream(...):
            # ... 处理 chunk ...
            pass
    
    except Exception as e:
        # Handle error
        self.state_monitor.mark_error(e)
    
    finally:
        # Transition to IDLE (which triggers followup processing)
        self.state_monitor.transition(AgentState.IDLE)
        self._agent_running = False
```

**工作量**：1-2 小时

---

## 阶段 2：完整的中断和恢复机制（P0 - 必须实现）

### 2.1 实现检查点保存

**目标**：在中断时保存执行状态

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**新增方法**：
```python
def _save_suspension_checkpoint(self) -> None:
    """Save state when suspending"""
    checkpoint = {
        "timestamp": datetime.now().isoformat(),
        "messages": self.agent.get_messages(),  # 获取当前消息历史
        "state": self.state_monitor.state.value,
        "flags": {
            "streaming": self.state_monitor.flags.isStreaming,
            "waiting": self.state_monitor.flags.isWaiting,
            "blocked": self.state_monitor.flags.isBlocked,
        }
    }
    self._suspension_checkpoint = checkpoint
    self.notify("✓ 状态已保存")
```

**工作量**：1-2 小时

---

### 2.2 实现恢复机制

**目标**：从 SUSPENDED 状态恢复执行

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**新增方法**：
```python
def handle_resume(self) -> None:
    """Resume from suspended state"""
    if self.state_monitor.state != AgentState.SUSPENDED:
        self.notify("⚠ 当前不在暂停状态")
        return
    
    if not self._suspension_checkpoint:
        self.notify("⚠ 无可恢复的检查点")
        return
    
    # Restore checkpoint
    checkpoint = self._suspension_checkpoint
    
    # Restore messages
    for msg in checkpoint["messages"]:
        self.agent.add_message(msg)
    
    # Transition back to ACTIVE
    self.state_monitor.transition(AgentState.ACTIVE)
    
    # Continue execution
    self._agent_running = True
    self._agent_worker = self.run_worker(
        self._continue_execution(),
        exclusive=False
    )
    
    self.notify("✓ 已恢复执行")
```

**工作量**：2-3 小时

---

### 2.3 添加恢复快捷键

**目标**：用户可以通过快捷键恢复

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/tui/app.py`

**修改点**：
```python
BINDINGS = [
    # ... 现有绑定 ...
    ("ctrl+r", "resume", "Resume"),  # 新增
]

def action_resume(self) -> None:
    """Resume from suspended state"""
    self.handle_resume()
```

**工作量**：30 分钟

---

## 阶段 3：增强的状态管理（P1 - 应该实现）

### 3.1 状态转移的原子性保证

**目标**：确保状态转移是原子的，不会出现竞态条件

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/monitor/state_monitor.py`

**修改点**：
```python
import threading

class StateMonitor(BaseMonitor):
    def __init__(self):
        # ... 现有代码 ...
        self._transition_lock = threading.Lock()
    
    def transition(self, new_state: AgentState) -> bool:
        """State transition with atomicity guarantee"""
        with self._transition_lock:
            if new_state in VALID_TRANSITIONS.get(self.state, []):
                old_state = self.state
                self.state = new_state
                self._emit_state_changed(old_state, new_state)
                return True
            return False
```

**工作量**：1 小时

---

### 3.2 状态转移的审计日志

**目标**：记录所有状态转移事件

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/monitor/state_monitor.py`

**修改点**：
```python
import logging

logger = logging.getLogger(__name__)

class StateMonitor(BaseMonitor):
    def transition(self, new_state: AgentState) -> bool:
        """State transition with audit logging"""
        with self._transition_lock:
            if new_state in VALID_TRANSITIONS.get(self.state, []):
                old_state = self.state
                self.state = new_state
                
                # Audit log
                logger.info(
                    f"State transition: {old_state.value} -> {new_state.value}",
                    extra={
                        "timestamp": datetime.now().isoformat(),
                        "old_state": old_state.value,
                        "new_state": new_state.value,
                    }
                )
                
                self._emit_state_changed(old_state, new_state)
                return True
            return False
```

**工作量**：1 小时

---

### 3.3 状态转移的错误恢复

**目标**：如果状态转移失败，能够恢复

**文件**：`/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/monitor/state_monitor.py`

**修改点**：
```python
class StateMonitor(BaseMonitor):
    def transition(self, new_state: AgentState) -> bool:
        """State transition with error recovery"""
        with self._transition_lock:
            if new_state not in VALID_TRANSITIONS.get(self.state, []):
                logger.warning(
                    f"Invalid state transition: {self.state.value} -> {new_state.value}",
                    extra={
                        "current_state": self.state.value,
                        "requested_state": new_state.value,
                        "valid_transitions": [s.value for s in VALID_TRANSITIONS.get(self.state, [])],
                    }
                )
                return False
            
            try:
                old_state = self.state
                self.state = new_state
                self._emit_state_changed(old_state, new_state)
                return True
            except Exception as e:
                logger.error(
                    f"Error during state transition: {e}",
                    exc_info=True
                )
                # Attempt to recover to previous state
                self.state = old_state
                return False
```

**工作量**：1-2 小时

---

## 总体时间估计

| 阶段 | 任务 | 工作量 | 优先级 |
|------|------|--------|--------|
| 1.1 | 集成 StateMonitor | 1-2h | P0 |
| 1.2 | 状态感知路由 | 2-3h | P0 |
| 1.3 | 状态驱动队列 | 1-2h | P0 |
| 1.4 | 修改完成处理 | 1-2h | P0 |
| 2.1 | 检查点保存 | 1-2h | P0 |
| 2.2 | 恢复机制 | 2-3h | P0 |
| 2.3 | 恢复快捷键 | 0.5h | P0 |
| 3.1 | 原子性保证 | 1h | P1 |
| 3.2 | 审计日志 | 1h | P1 |
| 3.3 | 错误恢复 | 1-2h | P1 |
| **总计** | | **14-21h** | |

---

## 实现建议

### 优先顺序
1. **第一周**：完成阶段 1（基础集成）- 5-9 小时
2. **第二周**：完成阶段 2（中断和恢复）- 5-8 小时
3. **第三周**：完成阶段 3（增强管理）- 3-5 小时

### 测试策略
- 单元测试：状态转移规则
- 集成测试：消息路由和队列处理
- 端到端测试：完整的用户交互流程

### 风险评估
- **低风险**：状态转移逻辑相对独立
- **中风险**：与现有 TUI 逻辑的集成
- **高风险**：中断和恢复的复杂性

### 回滚计划
- 保留 `_agent_running` 布尔值作为备用
- 在 StateMonitor 中添加 `legacy_mode` 标志
- 可以快速切换回旧实现
