# Leon 评估系统（Eval System）实现计划

## Context

Leon 的 `MonitorMiddleware` 只监控 LLM 调用，tool call 是 pass-through（不计时、不记录）。没有轨迹追踪、没有外部测试驱动能力。需要构建一套完整的评估系统：模拟真实用户交互 → 轨迹采集 → 三层指标计算 → LLM-as-judge 主观评分。

**调研结论**：
- 自建方案优于依赖 LangSmith/LangFuse，但应充分复用 LangChain Core 已有能力
- LangChain 的 `BaseTracer` + callback 系统是轨迹采集的正确基础（而非自建 middleware instrumentation）
- `langchain_classic.evaluation.TrajectoryEvalChain` 提供了 LLM-as-judge 的参考实现
- LangGraph 不提供 token/timing/cost 追踪，Leon 的 `CostCalculator` 和 `ContextMonitor` 仍需保留

**设计决策**：
- 轨迹采集**按需开启**（通过 `config={"callbacks": [recorder]}` 注入，不自动记录所有 run）
- eval 包放在**顶层 `eval/`**（与 core/ 平级）
- Phase 1 范围：**采集 + Harness**（端到端可用）

## LangChain/LangGraph 能力复用分析

基于 GitHub 仓库源码和文档的深度调研（`/tmp/langchain-repo`, `/tmp/langgraph-repo`）：

### 可以复用的（不重复造轮子）

| LangChain 能力 | 位置 | 替代我们的 |
|---------------|------|-----------|
| `BaseTracer` | `langchain_core/tracers/base.py` | 自建 TrajectoryRecorder 的基类，提供 Run 生命周期管理 |
| `Run` 数据模型 | `langchain_core/tracers/schemas.py` (= `langsmith.RunTree`) | 自建 LLMCallRecord/ToolCallRecord 的部分字段（timing, parent-child, inputs/outputs） |
| `RunCollectorCallbackHandler` | `langchain_core/tracers/run_collector.py` | 轻量 trajectory 收集，10 行代码，收集完整 Run 树 |
| `on_tool_start/end` callbacks | `langchain_core/callbacks/base.py` | **替代 `MonitorMiddleware.awrap_tool_call` 自建 instrumentation** |
| `on_chat_model_start/end` callbacks | 同上 | 补充 `awrap_model_call` 的 timing 记录 |
| `UsageMetadata` + `add_usage()` | `langchain_core/messages/ai.py` | token delta 计算的标准工具函数 |
| `TrajectoryEvalChain` | `langchain_classic/evaluation/agents/trajectory_eval_chain.py` | Phase 2 judge.py 的 prompt 模板和评分逻辑参考 |
| `stream_mode="debug"` | `langgraph/pregel/debug.py` | 补充 per-step state snapshots（task/checkpoint 事件） |

### 必须自建的（LangChain/LangGraph 不提供）

| 能力 | 原因 |
|------|------|
| Cost 计算 | LangChain 无内置 cost，Leon 的 `CostCalculator`（OpenRouter 动态定价）是唯一来源 |
| Context 窗口追踪 | LangChain 无 `ContextMonitor` 等价物 |
| SQLite 持久化 | `RunCollectorCallbackHandler` 只存内存，需要自建持久化层 |
| 外部测试 Harness | LangGraph 无评估/测试驱动能力 |
| 三层指标计算 | 无现成 MetricsCollector |
| SSE 客户端 | 针对 Leon 后端 API 的专用客户端 |

### 关键架构变更（vs 上一版计划）

**旧方案**：在 `MonitorMiddleware.awrap_tool_call` 中自建 instrumentation
**新方案**：基于 `BaseTracer` 子类，通过 LangChain callback 系统采集轨迹

优势：
1. `run_id` + `parent_run_id` 自动关联 LLM call 与 tool call（无需手动维护 `triggering_llm_call_id`）
2. `Run.start_time` / `Run.end_time` 自动记录（无需手动 `time.monotonic()`）
3. 完整的 Run 树结构（child_runs 嵌套），天然支持 sub-agent 轨迹
4. **不修改 `MonitorMiddleware`**，零侵入现有中间件栈
5. 通过 `config={"callbacks": [recorder]}` 注入，按需开启

## 架构概览

```
eval/                           # 新包 — 评估系统（顶层，与 core/ 平级）
├── __init__.py
├── models.py                   # Pydantic 数据模型（轨迹 + 三层指标 + 场景）
├── tracer.py                   # TrajectoryTracer（BaseTracer 子类，核心采集）
├── storage.py                  # TrajectoryStore（SQLite: ~/.leon/eval.db）
├── collector.py                # MetricsCollector（三层指标计算）
├── judge.py                    # LLM-as-judge 引擎（Phase 2）
├── reporter.py                 # 报告生成（Phase 2）
├── otel.py                     # 可选 OTEL span 导出（Phase 3）
├── harness/                    # 外部测试驱动
│   ├── __init__.py
│   ├── client.py               # SSE 客户端（httpx + SSE 消费）
│   ├── scenario.py             # 场景定义 & YAML 加载
│   └── runner.py               # 并发测试执行引擎
└── scenarios/                  # YAML 场景文件
    └── example.yaml
```

注意：**不再新增 `core/monitor/trajectory.py`，不再修改 `core/monitor/middleware.py`**。
轨迹采集完全通过 `eval/tracer.py`（BaseTracer 子类）+ callback 注入实现。

## Phase 1: 轨迹采集 + 存储 + Harness（首期交付）

### 1.1 数据模型 — `eval/models.py`

核心 Pydantic 模型：

| 模型 | 职责 |
|------|------|
| `LLMCallRecord` | 单次 LLM 调用：run_id, parent_run_id, duration_ms, 6 项 token 分项, cost, tool_calls_requested |
| `ToolCallRecord` | 单次 tool 调用：run_id, parent_run_id, tool_name, duration_ms, success, error |
| `RunTrajectory` | 一次完整 run：thread_id, user_message, final_response, llm_calls[], tool_calls[], run_tree_json |
| `SystemMetrics` | Tier 1：total_tokens, cache_hit_rate, context_usage_percent, cost |
| `ObjectiveMetrics` | Tier 2：per-tool timing stats, LLM latency p95, tokens_per_second |
| `ToolTimingStats` | per-tool 统计：count, avg_ms, max_ms, p95_ms, success_rate |
| `SubjectiveMetrics` | Tier 3：overall_score, dimension scores, flagged_issues（Phase 2） |
| `EvalScenario` | 测试场景：messages[], expected_behaviors[], timeout |
| `ScenarioMessage` | 单条场景消息：role, content, delay_seconds |
| `EvalResult` | 完整评估结果：trajectory + 三层 metrics |
| `TrajectoryCapture` | SSE 流采集结果：text_chunks, tool_calls, tool_results, status_snapshots |

关键变化 vs 上一版：
- `LLMCallRecord.run_id` / `parent_run_id` 来自 LangChain `Run` 对象（自动关联）
- 不再需要手动维护 `triggering_llm_call_id`
- 新增 `run_tree_json` 存储完整 Run 树（用于 debug 和 judge）

### 1.2 TrajectoryTracer — `eval/tracer.py`（核心变更）

基于 `langchain_core.tracers.base.BaseTracer` 子类，替代原计划的自建 middleware instrumentation：

```python
from langchain_core.tracers.base import BaseTracer
from langchain_core.tracers.schemas import Run

class TrajectoryTracer(BaseTracer):
    """基于 LangChain callback 系统的轨迹采集器。

    通过 config={"callbacks": [tracer]} 注入 agent.astream()，
    自动捕获所有 LLM call 和 tool call 的完整 Run 树。

    生命周期：
    1. 创建实例
    2. 注入 astream config
    3. agent 执行完毕后，从 traced_runs 提取轨迹
    4. 转换为 RunTrajectory 并持久化
    """

    name = "trajectory_tracer"

    def __init__(self, thread_id: str, user_message: str, cost_calculator=None):
        super().__init__()
        self.thread_id = thread_id
        self.user_message = user_message
        self.cost_calculator = cost_calculator  # Leon 的 CostCalculator 实例
        self.traced_runs: list[Run] = []

    def _persist_run(self, run: Run) -> None:
        """root run 结束时收集完整 Run 树。"""
        self.traced_runs.append(run)

    def _on_llm_end(self, run: Run) -> None:
        """每次 LLM 调用结束，提取 usage_metadata 用于 cost 计算。"""
        # run.outputs["generations"][0][0].message.usage_metadata
        # 可选：用 cost_calculator 计算 per-call cost

    def to_trajectory(self) -> RunTrajectory:
        """将 Run 树转换为 RunTrajectory 数据模型。"""
        # 遍历 traced_runs[0].child_runs，按 run_type 分类：
        # - run_type == "chat_model" → LLMCallRecord
        # - run_type == "tool" → ToolCallRecord
        # 时间从 Run.start_time / Run.end_time 提取
        # token 从 Run.outputs 中的 AIMessage.usage_metadata 提取
        # parent-child 关系从 Run.parent_run_id 自动获得
```

关键设计：
- `_persist_run` 只在 root run 结束时调用，child runs 嵌套在 `run.child_runs` 中
- `to_trajectory()` 递归遍历 Run 树，提取 LLM/tool call 记录
- `cost_calculator` 可选注入，用于计算 per-call cost（Leon 独有能力）
- 线程安全：每次 eval run 创建新实例，无共享状态

### 1.3 streaming_service.py 集成

在 `stream_agent_execution()` 中，当 `enable_trajectory=True` 时：

```python
# 创建 tracer
tracer = TrajectoryTracer(
    thread_id=thread_id,
    user_message=message,
    cost_calculator=agent.runtime.token.cost_calculator,
)

# 注入 astream config
config = {
    "configurable": {"thread_id": thread_id},
    "callbacks": [tracer],  # ← 关键：通过 callback 注入
}

# agent 执行完毕后
trajectory = tracer.to_trajectory()
store = TrajectoryStore()
store.save_trajectory(trajectory)
```

**修改文件**：`backend/web/services/streaming_service.py`（约 10 行改动）

### 1.4 后端 API 扩展 — trajectory 开关

`backend/web/models/requests.py`：
```python
class RunRequest(BaseModel):
    message: str
    enable_trajectory: bool = False  # 按需开启轨迹采集
```

### 1.5 TrajectoryStore — `eval/storage.py`

SQLite 存储（`~/.leon/eval.db`，独立于 `leon.db`）：

```sql
eval_runs (id PK, thread_id, started_at, finished_at, user_message, final_response,
           status, run_tree_json, trajectory_json)
eval_llm_calls (id PK, run_id FK, parent_run_id, duration_ms,
                input_tokens, output_tokens, total_tokens, cost_usd, model_name)
eval_tool_calls (id PK, run_id FK, parent_run_id, tool_name, tool_call_id,
                 duration_ms, success, error, args_summary, result_summary)
eval_metrics (id PK, run_id, tier TEXT, timestamp, metrics_json)

-- 索引
idx_eval_runs_thread (thread_id, started_at)
idx_eval_tool_name (tool_name)
idx_eval_metrics_run (run_id, tier)
```

接口：`save_trajectory()`, `save_metrics()`, `get_trajectory()`, `list_runs()`, `get_metrics()`

### 1.6 MetricsCollector — `eval/collector.py`

**Tier 1 — SystemMetrics**：从 SSE `status` 事件 + trajectory 汇总
- total_tokens, input/output/cache_read/cache_write, cache_hit_rate
- context_usage_percent, message_count, llm_call_count, tool_call_count, total_cost_usd

**Tier 2 — ObjectiveMetrics**：从 trajectory 计算
- per-tool timing: count, avg_ms, max_ms, p95_ms, success_rate
- LLM latency: avg, max, p95
- 效率指标: total_duration_ms, tokens_per_second, tool_calls_per_llm_call
- 异常检测: shell 命令 > 30s 标记 slow，readFile > 60s 标记 slow

**Tier 3 — SubjectiveMetrics**：由 judge.py 计算（Phase 2）

### 1.7 SSE Client — `eval/harness/client.py`

基于 `httpx` + SSE 解析，对接后端 API：

```python
class EvalClient:
    async def create_thread(sandbox="local", cwd=None) -> str
    async def run_message(thread_id, message, enable_trajectory=True) -> TrajectoryCapture
    async def get_runtime(thread_id) -> dict
    async def delete_thread(thread_id) -> None
```

`TrajectoryCapture` 收集 SSE 流中所有事件：
- text_chunks, tool_calls, tool_results, status_snapshots
- final_status（最后一个 status 事件）
- terminal_event（done/cancelled/error）

### 1.8 场景定义 — `eval/harness/scenario.py` + `eval/scenarios/*.yaml`

```yaml
id: file_ops_basic
name: "基础文件操作"
category: file_ops
timeout_seconds: 120
sandbox: local
messages:
  - content: "在 /tmp/eval_test/ 创建一个 hello.py，包含 hello() 函数"
  - content: "读取 hello.py 并添加 docstring"
expected_behaviors:
  - "调用 write_file"
  - "调用 read_file"
  - "调用 edit_file"
evaluation_criteria:
  - "任务完成度：是否完成所有请求的操作？"
  - "效率：是否避免了不必要的 tool call？"
```

### 1.9 Runner — `eval/harness/runner.py`

```python
class EvalRunner:
    async def run_scenario(scenario) -> EvalResult
    async def run_all(scenarios, max_concurrent=3) -> list[EvalResult]
```

单场景流程：
1. `POST /api/threads` 创建 thread（`enable_trajectory=True`）
2. 逐条发送 messages，消费 SSE 流，收集 TrajectoryCapture
3. `GET /api/threads/{id}/runtime` 获取最终 metrics
4. 计算 Tier 1 + Tier 2 指标
5. `DELETE /api/threads/{id}` 清理
6. 持久化到 TrajectoryStore

并发控制：`asyncio.Semaphore(max_concurrent)`。

## Phase 2: LLM-as-Judge + 报告（后续迭代）

### 2.1 Judge Engine — `eval/judge.py`

参考 `langchain_classic.evaluation.agents.trajectory_eval_chain.py` 的 prompt 模板和评分逻辑。
该实现使用 5 维度评分（helpfulness, logical sequence, tool usage, step count, tool appropriateness），分数 1-5 归一化到 0-1。

Leon 的 judge 在此基础上扩展：

轨迹简化格式（给 judge LLM 看的）：
```
[Task] 用户请求内容
[Step 1] LLM → 决定调用 write_file(path="/tmp/hello.py", content="...")
[Step 2] Tool write_file → 成功 (120ms)
[Step 3] LLM → 决定调用 read_file(path="/tmp/hello.py")
[Step 4] Tool read_file → 返回文件内容 (45ms)
[Step 5] LLM → 回复用户 "已完成..."
[Result] 状态: completed, 总耗时: 8.2s, Token: 3200, 成本: $0.012
```

评分维度：
| 维度 | 说明 | 权重 |
|------|------|------|
| task_completion | 是否完成用户请求 | 0.3 |
| efficiency | tool call 是否精简、无冗余 | 0.2 |
| correctness | 操作是否正确、无错误 | 0.25 |
| hallucination | 是否存在幻觉（声称做了但没做） | 0.15 |
| context_usage | 是否正确利用上下文信息 | 0.1 |

### 2.2 Reporter — `eval/reporter.py`

输出 JSON + Markdown 报告。

## Phase 3: OTEL 导出（可选，后续迭代）

`eval/otel.py`，基于 `opentelemetry-api` + `opentelemetry-sdk`，遵循 GenAI Semantic Conventions。

## 实现顺序（Phase 1 细分步骤）

| Step | 文件 | 内容 |
|------|------|------|
| 1a | `eval/__init__.py`, `eval/models.py` | Pydantic 数据模型 |
| 1b | `eval/tracer.py` | TrajectoryTracer（BaseTracer 子类） |
| 1c | `eval/storage.py` | TrajectoryStore（SQLite） |
| 1d | `eval/collector.py` | MetricsCollector（Tier 1 + Tier 2） |
| 1e | `eval/harness/__init__.py`, `eval/harness/client.py` | SSE 客户端 |
| 1f | `eval/harness/scenario.py` | 场景定义 & YAML 加载 |
| 1g | `eval/harness/runner.py` | 并发测试执行引擎 |
| 1h | `eval/scenarios/example.yaml` | 示例场景 |
| 1i | `backend/web/services/streaming_service.py` | trajectory callback 注入 |
| 1j | `backend/web/models/requests.py` | RunRequest 新增 enable_trajectory |
| 1k | `pyproject.toml` | 添加 eval 包 + optional deps |

## 需修改的现有文件

| 文件 | 修改内容 |
|------|---------|
| `backend/web/services/streaming_service.py` (364行) | 当 enable_trajectory=True 时创建 TrajectoryTracer 并注入 astream config |
| `backend/web/models/requests.py` | RunRequest 新增 `enable_trajectory: bool = False` |
| `pyproject.toml` (107行) | 添加 eval 包到 packages + optional deps |

**不再修改**：`core/monitor/middleware.py`, `core/monitor/runtime.py`（零侵入现有中间件栈）

## 需新增的文件

| 文件 | 内容 |
|------|------|
| `eval/__init__.py` | 包初始化 |
| `eval/models.py` | 全部 Pydantic 数据模型 |
| `eval/tracer.py` | TrajectoryTracer（BaseTracer 子类） |
| `eval/storage.py` | TrajectoryStore（SQLite） |
| `eval/collector.py` | MetricsCollector（Tier 1 + Tier 2） |
| `eval/harness/__init__.py` | 子包初始化 |
| `eval/harness/client.py` | EvalClient（SSE 消费） |
| `eval/harness/scenario.py` | EvalScenario 加载 |
| `eval/harness/runner.py` | EvalRunner（并发执行） |
| `eval/scenarios/example.yaml` | 示例测试场景 |

## 需新增的依赖

```toml
[project.optional-dependencies]
eval = ["httpx-sse>=0.4.0"]
otel = ["opentelemetry-api>=1.20.0", "opentelemetry-sdk>=1.20.0", "opentelemetry-exporter-otlp>=1.20.0"]
```

`httpx` 已在主依赖中。`langchain_core`（含 BaseTracer）已在主依赖中。SQLite 是标准库。

## 验证方案

### 端到端验证（需要后端运行）

1. 启动后端：`uv run python -m uvicorn backend.web.main:app --host 0.0.0.0 --port 8001`
2. 运行示例场景：
```bash
uv run python -m eval.harness.runner --scenario eval/scenarios/example.yaml --base-url http://localhost:8001
```
3. 验证点：
   - SSE 流正确消费（text/tool_call/tool_result/status/done 事件全部捕获）
   - TrajectoryTracer 收集到完整 Run 树（含 child_runs）
   - `~/.leon/eval.db` 写入了 eval_runs + eval_llm_calls + eval_tool_calls 记录
   - Tier 1 SystemMetrics 包含正确的 token/cost/context 数据
   - Tier 2 ObjectiveMetrics 包含 per-tool timing 和 LLM latency
   - enable_trajectory=False 时无 tracer 注入（零开销）

### 单元测试

```bash
uv run pytest tests/eval/ -v
```

测试覆盖：
- `test_models.py`：Pydantic 模型序列化/反序列化
- `test_tracer.py`：TrajectoryTracer 的 Run 树 → RunTrajectory 转换
- `test_storage.py`：SQLite CRUD 操作
- `test_collector.py`：Tier 1/2 指标计算正确性
- `test_client.py`：SSE 事件解析
