# OpenClaw 核心架构分析

> 基于 moltbot/clawebot 研究，为 Leon 复刻提供参考
> 日期：2026-02-05

---

## 一、消息队列模式（Queue Mode）

OpenClaw 的核心是**异步消息驱动架构**，通过 5 种队列模式实现 Agent 协调。

### 1.1 五种队列模式

#### **steer（方向盘模式）**
- **职责**：主控制流，决策和调度
- **行为**：
  - 接收用户输入或上游任务
  - 分析任务，决定分解策略
  - 发出 followup 指令给执行 Agent
  - 等待 collect 信号汇总结果
  - 可中断其他 Agent 的执行
- **消息流**：`steer → followup → collect → steer`
- **状态**：`waiting_for_collect` / `steering` / `interrupted`

#### **followup（跟进模式）**
- **职责**：执行具体任务
- **行为**：
  - 接收 steer 的指令
  - 执行工具调用或子任务
  - 定期向 steer 报告进度
  - 遇到阻塞时请求 steer 介入
  - 完成后发送 collect 信号
- **消息流**：`followup → tool_call → progress_report → collect`
- **状态**：`executing` / `blocked` / `completed`

#### **collect（收集模式）**
- **职责**：汇总和验证结果
- **行为**：
  - 等待多个 followup 完成
  - 验证结果一致性
  - 合并结果
  - 返回给 steer
- **消息流**：`collect ← followup1, followup2, ... → steer`
- **状态**：`collecting` / `validating` / `merged`

#### **steer-backlog（待办队列）**
- **职责**：任务缓冲和优先级管理
- **行为**：
  - 存储待处理任务
  - 按优先级排序
  - 当 steer 空闲时推送任务
  - 支持动态优先级调整
  - 支持任务合并（相似任务合并为一个）
- **消息流**：`user_input → steer-backlog → steer`
- **状态**：`queued` / `prioritized` / `dispatched`

#### **interrupt（中断模式）**
- **职责**：紧急控制和错误恢复
- **行为**：
  - 用户或系统发出中断信号
  - 立即停止当前 followup
  - 保存中间状态
  - 可选：回滚到上一个稳定点
  - 可选：切换到不同的执行策略
- **消息流**：`interrupt → stop_followup → save_state → steer`
- **状态**：`interrupted` / `state_saved` / `recovery_mode`

### 1.2 队列模式的状态转移图

```
┌─────────────────────────────────────────────────────────┐
│                    steer-backlog                         │
│              (任务缓冲 + 优先级管理)                      │
└────────────────────┬────────────────────────────────────┘
                     │ dispatch
                     ↓
┌─────────────────────────────────────────────────────────┐
│                      steer                               │
│              (主控制流 + 决策)                            │
│  状态: waiting_for_collect / steering / interrupted     │
└────────────────────┬────────────────────────────────────┘
                     │ issue_followup
                     ↓
┌─────────────────────────────────────────────────────────┐
│                    followup                              │
│              (执行 + 进度报告)                            │
│  状态: executing / blocked / completed                  │
└────────────────────┬────────────────────────────────────┘
                     │ report_progress / request_help
                     ↓
┌─────────────────────────────────────────────────────────┐
│                    collect                               │
│              (结果汇总 + 验证)                            │
│  状态: collecting / validating / merged                 │
└────────────────────┬────────────────────────────────────┘
                     │ return_result
                     ↓
                    steer
                     ↑
                     │ interrupt (可选)
                     │
            ┌────────┴────────┐
            │                 │
        interrupt signal   recovery
```

---

## 二、Agent 运行时状态管理

### 2.1 核心状态机

```python
class AgentState(Enum):
    # 生命周期状态
    INITIALIZING = "initializing"      # 初始化中
    READY = "ready"                    # 就绪
    ACTIVE = "active"                  # 活跃（正在处理任务）
    IDLE = "idle"                      # 空闲
    SUSPENDED = "suspended"            # 暂停
    TERMINATED = "terminated"          # 已终止
    
    # 执行状态
    STREAMING = "streaming"            # 流式输出中
    COMPACTING = "compacting"          # 上下文压缩中
    WAITING = "waiting"                # 等待（工具调用、用户输入等）
    BLOCKED = "blocked"                # 阻塞（资源不足、权限不足等）
    
    # 错误状态
    ERROR = "error"                    # 错误
    RECOVERING = "recovering"          # 恢复中
```

### 2.2 状态标志位

```python
class AgentFlags:
    isStreaming: bool          # 是否正在流式输出
    isCompacting: bool         # 是否正在压缩上下文
    isWaiting: bool            # 是否等待中
    isBlocked: bool            # 是否被阻塞
    canInterrupt: bool         # 是否可被中断
    hasError: bool             # 是否有错误
    needsRecovery: bool        # 是否需要恢复
    
    # 资源状态
    tokenUsage: int            # 当前 token 使用量
    tokenLimit: int            # token 限制
    memoryUsage: int           # 内存使用量
    memoryLimit: int           # 内存限制
    
    # 时间戳
    lastActivityTime: float    # 最后活动时间
    createdAt: float           # 创建时间
    startedAt: float           # 开始时间
```

### 2.3 状态转移规则

```
INITIALIZING
    ↓ (初始化完成)
READY
    ↓ (接收任务)
ACTIVE
    ├─ (isStreaming=true) → 流式输出
    ├─ (isCompacting=true) → 上下文压缩
    ├─ (isWaiting=true) → 等待工具结果
    ├─ (isBlocked=true) → 阻塞
    └─ (interrupt signal) → SUSPENDED
    
SUSPENDED
    ├─ (resume) → ACTIVE
    └─ (terminate) → TERMINATED
    
IDLE
    ├─ (new task) → ACTIVE
    └─ (timeout) → TERMINATED
    
ERROR
    ├─ (needsRecovery=true) → RECOVERING
    └─ (recovery failed) → TERMINATED
    
RECOVERING
    ├─ (recovery success) → READY
    └─ (recovery failed) → TERMINATED
```

### 2.4 上下文压缩（Compacting）

当 `isCompacting=true` 时：
- 暂停新的工具调用
- 对历史消息进行摘要
- 删除冗余信息
- 保留关键决策点
- 完成后继续执行

---

## 三、Tool Call 执行流程和边界控制

### 3.1 Tool Call 生命周期

```
┌─────────────────────────────────────────────────────────┐
│                  Tool Call Request                       │
│  (Agent 生成 tool_use 消息)                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Tool Call Validation                        │
│  - 检查工具是否存在                                      │
│  - 验证参数类型和范围                                    │
│  - 检查权限和资源限制                                    │
│  - 检查安全策略（路径、命令等）                          │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    ✓ Valid                   ✗ Invalid
        │                         │
        ↓                         ↓
┌──────────────────┐    ┌──────────────────┐
│  Tool Execution  │    │  Rejection       │
│  (Hook Chain)    │    │  (Return Error)  │
└────────┬─────────┘    └──────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│              Hook Chain Execution                        │
│  1. Pre-execution hooks (权限检查、日志)                 │
│  2. Tool execution (实际执行)                            │
│  3. Post-execution hooks (结果验证、审计)               │
└────────────────────┬────────────────────────────────────┘
         │
         ├─ Success → Tool Result
         ├─ Timeout → Timeout Error
         ├─ Permission Denied → Permission Error
         └─ Resource Limit → Resource Error
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│              Tool Result Processing                      │
│  - 格式化结果                                            │
│  - 记录审计日志                                          │
│  - 更新资源计数                                          │
│  - 检查是否需要中断                                      │
└────────────────────┬────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│              Return to Agent                             │
│  (ToolMessage 添加到消息历史)                            │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Hook 系统（优先级 1-10，数字大优先）

```python
class ToolHook:
    priority: int  # 1-10
    
    def pre_execute(self, tool_name: str, params: dict) -> bool:
        """返回 False 则拒绝执行"""
        pass
    
    def post_execute(self, tool_name: str, result: Any) -> Any:
        """可以修改结果"""
        pass
```

**内置 Hook 优先级**：
- 10: PathSecurityHook（路径安全检查）
- 9: FilePermissionHook（文件权限检查）
- 8: DangerousCommandsHook（危险命令拦截）
- 7: FileAccessLoggerHook（文件访问日志）
- 6: ResourceLimitHook（资源限制检查）
- 5: AuditLogHook（审计日志）

### 3.3 边界控制

```python
class ToolBoundary:
    # 路径边界
    workspace_root: str        # 工作目录
    allowed_paths: list[str]   # 允许的路径列表
    blocked_paths: list[str]   # 禁止的路径列表
    
    # 命令边界
    allowed_commands: list[str]
    blocked_commands: list[str]
    
    # 资源边界
    max_execution_time: int    # 最大执行时间（秒）
    max_output_size: int       # 最大输出大小（字节）
    max_file_size: int         # 最大文件大小（字节）
    
    # 权限边界
    file_permissions: dict     # 文件权限映射
    command_permissions: dict  # 命令权限映射
```

---

## 四、Session 管理机制

### 4.1 Session 生命周期

```
┌─────────────────────────────────────────────────────────┐
│                  Session Creation                        │
│  - 生成 session_id (UUID)                               │
│  - 初始化消息历史                                        │
│  - 初始化状态存储                                        │
│  - 记录创建时间戳                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                  Session Active                          │
│  - 接收用户消息                                          │
│  - 执行 Agent 逻辑                                       │
│  - 保存消息历史                                          │
│  - 定期保存检查点                                        │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    User Close              Timeout
        │                         │
        ↓                         ↓
┌──────────────────┐    ┌──────────────────┐
│  Session Close   │    │  Session Expire  │
│  (正常关闭)      │    │  (超时关闭)      │
└──────────────────┘    └──────────────────┘
        │                         │
        └────────────┬────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Session Cleanup                             │
│  - 保存最终状态                                          │
│  - 释放资源                                              │
│  - 记录关闭时间戳                                        │
│  - 可选：归档到历史                                      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Session 数据结构

```python
class Session:
    session_id: str                    # 唯一标识
    user_id: str                       # 用户 ID
    agent_id: str                      # Agent ID
    
    # 消息历史
    messages: list[Message]            # 完整消息历史
    message_count: int                 # 消息计数
    
    # 状态
    state: AgentState                  # 当前状态
    flags: AgentFlags                  # 状态标志位
    
    # 上下文
    context: dict                      # 执行上下文
    variables: dict                    # 变量存储
    
    # 时间戳
    created_at: float
    last_activity_at: float
    expires_at: float
    
    # 检查点
    checkpoints: list[Checkpoint]      # 保存的检查点
    current_checkpoint: int            # 当前检查点索引
    
    # 统计
    token_usage: int
    tool_call_count: int
    error_count: int
```

### 4.3 Session 持久化

```python
class SessionPersistence:
    def save_checkpoint(self, session: Session) -> str:
        """保存检查点，返回 checkpoint_id"""
        # 1. 序列化消息历史
        # 2. 保存状态快照
        # 3. 存储到数据库或文件系统
        # 4. 返回 checkpoint_id
        pass
    
    def load_checkpoint(self, checkpoint_id: str) -> Session:
        """从检查点恢复 Session"""
        # 1. 从存储读取数据
        # 2. 反序列化消息历史
        # 3. 恢复状态
        # 4. 返回 Session 对象
        pass
    
    def list_checkpoints(self, session_id: str) -> list[Checkpoint]:
        """列出 Session 的所有检查点"""
        pass
    
    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """删除检查点"""
        pass
```

### 4.4 Session 恢复策略

```
Session 中断
    ↓
检测到中断（网络断开、超时等）
    ↓
┌─────────────────────────────────────────┐
│  恢复策略选择                             │
├─────────────────────────────────────────┤
│ 1. 从最后检查点恢复                      │
│    - 重新加载消息历史                    │
│    - 恢复执行状态                        │
│    - 继续执行                            │
│                                         │
│ 2. 从上一个稳定点恢复                    │
│    - 回滚到上一个完整任务                │
│    - 重新开始当前任务                    │
│                                         │
│ 3. 重新开始                              │
│    - 清空消息历史                        │
│    - 重新初始化                          │
└─────────────────────────────────────────┘
```

---

## 五、其他重要架构特点

### 5.1 多 Agent 协调模式

#### **Master-Worker 模式**
```
Master Agent (steer)
    ├─ Worker-1 (followup)
    ├─ Worker-2 (followup)
    └─ Worker-3 (followup)
    
Master 负责：
- 任务分解
- 进度监控
- 结果汇总
- 错误处理

Worker 负责：
- 执行具体任务
- 报告进度
- 请求帮助
```

#### **Pipeline 模式**
```
Agent-1 (Explorer)
    ↓ (output → input)
Agent-2 (Analyzer)
    ↓ (output → input)
Agent-3 (Coder)
    ↓ (output → input)
Agent-4 (Reviewer)
```

### 5.2 上下文管理

```python
class ContextManager:
    # 上下文分层
    global_context: dict       # 全局上下文（所有 Agent 共享）
    session_context: dict      # Session 上下文（当前 Session）
    agent_context: dict        # Agent 上下文（当前 Agent）
    
    # 上下文压缩
    def compress_context(self, max_tokens: int) -> None:
        """压缩上下文到指定 token 数"""
        # 1. 计算当前 token 数
        # 2. 如果超过限制，执行压缩
        # 3. 保留关键信息
        pass
    
    # 上下文恢复
    def restore_context(self, checkpoint_id: str) -> None:
        """从检查点恢复上下文"""
        pass
```

### 5.3 错误恢复机制

```python
class ErrorRecovery:
    # 错误分类
    RECOVERABLE = [
        "timeout",
        "rate_limit",
        "temporary_network_error",
        "resource_exhausted",
    ]
    
    UNRECOVERABLE = [
        "permission_denied",
        "invalid_input",
        "not_found",
        "authentication_failed",
    ]
    
    def handle_error(self, error: Exception) -> RecoveryStrategy:
        if error.type in RECOVERABLE:
            return RecoveryStrategy.RETRY
        elif error.type in UNRECOVERABLE:
            return RecoveryStrategy.FAIL
        else:
            return RecoveryStrategy.ESCALATE
```

### 5.4 资源管理

```python
class ResourceManager:
    # Token 预算
    token_budget: int          # 总 token 预算
    token_used: int            # 已使用 token
    token_reserved: int        # 预留 token（用于恢复）
    
    # 并发控制
    max_concurrent_agents: int
    max_concurrent_tools: int
    
    # 超时控制
    default_timeout: int       # 默认超时（秒）
    max_timeout: int           # 最大超时（秒）
    
    def allocate_tokens(self, agent_id: str, amount: int) -> bool:
        """分配 token，返回是否成功"""
        if self.token_used + amount <= self.token_budget - self.token_reserved:
            self.token_used += amount
            return True
        return False
    
    def release_tokens(self, agent_id: str, amount: int) -> None:
        """释放 token"""
        self.token_used -= amount
```

### 5.5 可观测性（Observability）

```python
class ObservabilityLayer:
    # 事件日志
    def log_event(self, event: Event) -> None:
        """记录事件"""
        # event.type: "agent_created", "tool_called", "error_occurred", etc.
        # event.timestamp: 时间戳
        # event.data: 事件数据
        pass
    
    # 指标收集
    def record_metric(self, metric: Metric) -> None:
        """记录指标"""
        # metric.name: "token_usage", "tool_call_latency", etc.
        # metric.value: 指标值
        # metric.tags: 标签（agent_id, tool_name, etc.）
        pass
    
    # 追踪
    def start_trace(self, trace_id: str) -> None:
        """开始追踪"""
        pass
    
    def end_trace(self, trace_id: str) -> None:
        """结束追踪"""
        pass
```

---

## 六、Leon 复刻建议

### 6.1 优先级排序

1. **P0 - 必须实现**
   - 消息队列模式（steer/followup/collect）
   - 状态管理（AgentState + AgentFlags）
   - Tool Call 执行流程 + Hook 系统
   - Session 管理 + 检查点

2. **P1 - 应该实现**
   - 多 Agent 协调（Master-Worker）
   - 上下文压缩
   - 错误恢复机制
   - 资源管理

3. **P2 - 可以实现**
   - 可观测性层
   - 高级协调模式（Pipeline）
   - 性能优化

### 6.2 集成点

```python
# 在 Leon 的 middleware 中添加
middleware/
├── queue/              # 消息队列模式
│   ├── steer.py
│   ├── followup.py
│   ├── collect.py
│   └── backlog.py
├── session/            # Session 管理
│   ├── manager.py
│   ├── persistence.py
│   └── checkpoint.py
├── state/              # 状态管理
│   ├── machine.py
│   └── flags.py
└── recovery/           # 错误恢复
    ├── handler.py
    └── strategies.py
```

### 6.3 与现有 Leon 架构的融合

```
当前 Leon:
- FileSystemMiddleware
- SearchMiddleware
- CommandMiddleware
- TaskMiddleware (Sub-agent)

新增 OpenClaw 特性:
- QueueMiddleware (steer/followup/collect)
- SessionMiddleware (持久化 + 恢复)
- StateMiddleware (状态机)
- RecoveryMiddleware (错误恢复)

融合点:
- TaskMiddleware 可以使用 QueueMiddleware 的 followup 模式
- 所有 middleware 共享 SessionMiddleware 的上下文
- CommandMiddleware 的 Hook 系统可以扩展为通用 Hook 框架
```

---

## 七、参考实现

### 7.1 最小化 Queue 实现

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any

class QueueMode(Enum):
    STEER = "steer"
    FOLLOWUP = "followup"
    COLLECT = "collect"
    BACKLOG = "backlog"
    INTERRUPT = "interrupt"

@dataclass
class QueueMessage:
    mode: QueueMode
    agent_id: str
    task_id: str
    payload: dict
    timestamp: float
    priority: int = 5

class QueueManager:
    def __init__(self):
        self.queues = {mode: [] for mode in QueueMode}
    
    def enqueue(self, msg: QueueMessage) -> None:
        self.queues[msg.mode].append(msg)
    
    def dequeue(self, mode: QueueMode) -> QueueMessage | None:
        if self.queues[mode]:
            return self.queues[mode].pop(0)
        return None
```

### 7.2 最小化 Session 实现

```python
from uuid import uuid4
from datetime import datetime, timedelta

class Session:
    def __init__(self, user_id: str, agent_id: str):
        self.session_id = str(uuid4())
        self.user_id = user_id
        self.agent_id = agent_id
        self.messages = []
        self.state = AgentState.READY
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=1)
    
    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def save_checkpoint(self) -> str:
        checkpoint_id = str(uuid4())
        # 保存到数据库或文件系统
        return checkpoint_id
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
```

---

## 八、相关文件

- `/Users/apple/Desktop/project/v1/文稿/project/leon/middleware/task/middleware.py` - 当前 Task 中间件
- `/Users/apple/Desktop/project/v1/文稿/project/leon/agent.py` - Agent 核心
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/agent-biology-model.md` - Agent 生物学模型
- `/Users/apple/Desktop/project/v1/文稿/project/leon/docs/subagent-design.md` - Sub-agent 设计

