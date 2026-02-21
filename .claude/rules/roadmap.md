# Leon 路线图

目标：借鉴 OpenClaw、Opencode 的核心功能。参考文档：`docs/openclaw-architecture-analysis.md`

## 差距分析

| 模块 | OpenClaw | Leon | 状态 |
|------|----------|------|------|
| 消息队列模式 | steer/followup/collect/backlog/interrupt | ✅ Queue Mode | ✅ |
| 运行时状态机 | AgentState + AgentFlags | ✅ MonitorMiddleware（8 状态 + 7 标志） | ✅ |
| 队列-状态集成 | 状态驱动队列路由 | ✅ IDLE 回调触发 followup，SUSPENDED/ERROR 可恢复 | ✅ |
| Token/资源追踪 | Token 预算 + 并发控制 | ✅ TokenMonitor（6 项分项 + usage_metadata）+ CostCalculator（OpenRouter 动态定价）+ ContextMonitor | ✅ |
| Sandbox 基础设施 | 隔离执行环境 | ✅ sandbox/ 独立包，backend 注入 middleware | ✅ |
| 上下文压缩 | isCompacting + 自动压缩 | ✅ MemoryMiddleware（Pruning + Compaction） | ✅ |
| Tool Call 边界 | Hook 链 + 优先级 | ✅ middleware/command/hooks/ | ✅ |
| Session 管理 | 生命周期 + 检查点 | ✅ checkpointer + 时间旅行 | ✅ |
| 多 Agent 协调 | Master-Worker / Pipeline | TaskMiddleware 单向调用 | ⚠️ P2 |
| 错误恢复 | 可恢复/不可恢复 + 策略 | ✅ ERROR → RECOVERING → READY（状态机驱动） | ✅ |

## 实现顺序

1. ~~**P0-1 消息队列模式**~~ → ✅ `middleware/queue/` 已完成
2. ~~**P0-2 运行时状态机**~~ → ✅ `middleware/monitor/` 已完成（MonitorMiddleware 组合模式）
3. ~~**P0-3 队列-状态集成**~~ → ✅ TUI 消息路由基于 AgentState，followup 由状态回调驱动
4. ~~**P0-4 Sandbox 基础设施**~~ → ✅ `sandbox/` 独立包 + backend 注入 middleware
5. ~~**P1-1 上下文压缩**~~ → ✅ `middleware/memory/`（Pruning + Compaction，独立中间件）
6. **P2-1 多 Agent 协调** → 扩展 `middleware/task/`（双向通信 + Pipeline）
