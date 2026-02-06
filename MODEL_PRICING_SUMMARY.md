# Leon 项目 - 模型定价表和配置信息

## 1. 模型单价表（USD per 1M tokens）

### 完整定价表 (来自 `/middleware/monitor/cost.py`)

#### Anthropic 模型

| 模型 | 输入 | 输出 | 缓存读 | 缓存写 |
|------|------|------|--------|--------|
| claude-sonnet-4-5-20250929 | $3.00 | $15.00 | $0.30 | $3.75 |
| claude-opus-4-20250514 | $15.00 | $75.00 | $1.50 | $18.75 |
| claude-haiku-3-5-20241022 | $0.80 | $4.00 | $0.08 | $1.00 |

#### OpenAI 模型

| 模型 | 输入 | 输出 | 缓存读 | 缓存写 |
|------|------|------|--------|--------|
| gpt-4o | $2.50 | $10.00 | $1.25 | $2.50 |
| gpt-4o-mini | $0.15 | $0.60 | $0.075 | $0.15 |
| o1 | $15.00 | $60.00 | $7.50 | $15.00 |
| o3-mini | $1.10 | $4.40 | $0.55 | $1.10 |

#### DeepSeek 模型

| 模型 | 输入 | 输出 | 缓存读 | 缓存写 |
|------|------|------|--------|--------|
| deepseek-chat | $0.27 | $1.10 | $0.07 | $0.27 |

### 模型别名映射

```python
_MODEL_ALIASES = {
    "claude-3-5-sonnet": "claude-sonnet-4-5-20250929",
    "claude-3-opus": "claude-opus-4-20250514",
    "claude-3-5-haiku": "claude-haiku-3-5-20241022",
}
```

**说明：** 支持前缀匹配，如 `gpt-4o-2024-08-06` 会匹配到 `gpt-4o` 的定价。

---

## 2. Token 分项追踪（6 项）

Leon 的 TokenMonitor 支持以下 6 项分项追踪：

| 分项 | 字段名 | 说明 |
|------|--------|------|
| 输入 | `input_tokens` | 调整后的输入 token（排除缓存读写） |
| 输出 | `output_tokens` | 输出 token（排除推理 token） |
| 推理 | `reasoning_tokens` | 推理 token（仅 o1/o3 等模型） |
| 缓存读 | `cache_read_tokens` | 缓存命中的 token |
| 缓存写 | `cache_write_tokens` | 缓存创建的 token |
| 总计 | `total_tokens` | 总 token 数 |

### Token 提取来源

**优先级 1：** `usage_metadata`（LangChain 统一格式）
```python
{
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int,
    "input_token_details": {
        "cache_read": int,
        "cache_creation": int,  # cache_write
    },
    "output_token_details": {
        "reasoning": int,
    }
}
```

**优先级 2：** `response_metadata`（回退方案）
```python
{
    "token_usage": {
        "prompt_tokens": int,
        "completion_tokens": int,
        "total_tokens": int,
    }
}
```

---

## 3. 成本计算

### 计算公式

```
成本 = Σ(token_i × price_i / 1,000,000)

其中：
- token_i：第 i 项的 token 数
- price_i：第 i 项的单价（美元/百万 token）
- 结果单位：美元
```

### 分项成本计算

```python
breakdown = {
    "input": input_tokens × input_price / 1,000,000,
    "output": output_tokens × output_price / 1,000,000,
    "cache_read": cache_read_tokens × cache_read_price / 1,000,000,
    "cache_write": cache_write_tokens × cache_write_price / 1,000,000,
}
total_cost = sum(breakdown.values())
```

### 特殊情况：200K+ Token 定价

OpenCode 支持超过 200K token 的特殊定价（Leon 暂未实现）：

```typescript
const costInfo =
  model.cost?.experimentalOver200K && 
  tokens.input + tokens.cache.read > 200_000
    ? model.cost.experimentalOver200K
    : model.cost
```

---

## 4. 模型配置

### 默认模型

```yaml
agent:
  model: claude-sonnet-4-5-20250929
```

### 可配置参数

```python
class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"
    model_provider: str | None = None       # openai/anthropic/bedrock 等
    api_key: str | None = None              # 通用 API key
    base_url: str | None = None             # 通用 base URL
    temperature: float | None = None
    max_tokens: int | None = None           # 最大输出 token
    model_kwargs: dict[str, Any] = {}       # 透传给 init_chat_model 的参数
```

### 配置文件示例

```yaml
agent:
  model: claude-sonnet-4-5-20250929
  # model_provider: null    # 自动推断
  # api_key: null           # 从环境变量读取
  # base_url: null          # 从环境变量读取
  # temperature: null
  # max_tokens: null
  # model_kwargs: {}
  enable_audit_log: true
  block_dangerous_commands: true
  queue_mode: steer
```

---

## 5. Context Window 和 Max Tokens

### 模型 Context Window（参考值）

根据官方文档，各模型的 context window：

| 模型 | Context Window | 说明 |
|------|----------------|------|
| claude-sonnet-4-5-20250929 | 200K | Anthropic 最新 Sonnet |
| claude-opus-4-20250514 | 200K | Anthropic Opus |
| claude-haiku-3-5-20241022 | 200K | Anthropic Haiku |
| gpt-4o | 128K | OpenAI GPT-4 Omni |
| gpt-4o-mini | 128K | OpenAI GPT-4 Mini |
| o1 | 128K | OpenAI o1（推理模型） |
| o3-mini | 128K | OpenAI o3-mini |
| deepseek-chat | 4K-64K | DeepSeek（取决于版本） |

### Max Tokens 配置

Leon 允许通过配置文件或参数指定 `max_tokens`：

```python
# 配置文件
agent:
  max_tokens: 4096

# 或通过参数
agent = LeonAgent(model_name="claude-sonnet-4-5-20250929")
# 然后在 profile 中设置 max_tokens
```

**说明：** `max_tokens` 是输出的最大 token 数，不是 context window。

---

## 6. Token 监控指标

### 获取 Token 统计

```python
# 从 TokenMonitor 获取
metrics = token_monitor.get_metrics()

# 返回结构
{
    "total_tokens": int,
    "input_tokens": int,
    "output_tokens": int,
    "reasoning_tokens": int,
    "cache_read_tokens": int,
    "cache_write_tokens": int,
    "prompt_tokens": int,  # 向后兼容
    "completion_tokens": int,  # 向后兼容
    "call_count": int,
    "cost": float,  # 美元
}
```

### 获取成本信息

```python
# 计算当前累计成本
cost_info = token_monitor.get_cost()

# 返回结构
{
    "total": Decimal,  # 总成本（美元）
    "breakdown": {
        "input": Decimal,
        "output": Decimal,
        "cache_read": Decimal,
        "cache_write": Decimal,
    }
}
```

---

## 7. CostCalculator 使用示例

```python
from middleware.monitor.cost import CostCalculator

# 创建计算器
calculator = CostCalculator("claude-sonnet-4-5-20250929")

# 计算成本
tokens = {
    "input_tokens": 1000,
    "output_tokens": 500,
    "cache_read_tokens": 100,
    "cache_write_tokens": 50,
}

result = calculator.calculate(tokens)
# {
#     "total": Decimal("0.0045"),
#     "breakdown": {
#         "input": Decimal("0.003"),
#         "output": Decimal("0.0075"),
#         "cache_read": Decimal("0.00003"),
#         "cache_write": Decimal("0.0001875"),
#     }
# }
```

---

## 8. 环境变量

```bash
OPENAI_API_KEY      # OpenAI API key
OPENAI_BASE_URL     # OpenAI 代理 URL
ANTHROPIC_API_KEY   # Anthropic API key
TAVILY_API_KEY      # Web 搜索 API key
```

---

## 9. 文件位置参考

| 功能 | 文件路径 |
|------|---------|
| 模型定价表 | `/middleware/monitor/cost.py` |
| Token 监控 | `/middleware/monitor/token_monitor.py` |
| 成本计算 | `/middleware/monitor/cost.py` (CostCalculator) |
| Agent 配置 | `/agent_profile.py` |
| Agent 核心 | `/agent.py` |
| 监控中间件 | `/middleware/monitor/middleware.py` |

---

## 10. 与 OpenCode 的对比

| 特性 | OpenCode | Leon |
|------|----------|------|
| Token 追踪 | ✅ 6 项分项 | ✅ 6 项分项 |
| 成本计算 | ✅ 分项计算 + 200K+ 特殊定价 | ✅ 基础分项计算 |
| 缓存支持 | ✅ 5m/1h 分别追踪 | ✅ 基础支持 |
| 推理 token | ✅ 支持 | ✅ 支持 |
| 精确计算 | ✅ Decimal.js | ✅ Decimal.js |
| 模型支持 | ✅ 8+ 模型 | ✅ 8 模型 |

---

## 11. 快速参考

### 最便宜的模型
- **OpenAI:** gpt-4o-mini ($0.15/$0.60)
- **Anthropic:** claude-haiku-3-5-20241022 ($0.80/$4.00)
- **DeepSeek:** deepseek-chat ($0.27/$1.10)

### 最强的模型
- **Anthropic:** claude-opus-4-20250514 ($15.00/$75.00)
- **OpenAI:** o1 ($15.00/$60.00)

### 推荐平衡方案
- **Anthropic:** claude-sonnet-4-5-20250929 ($3.00/$15.00)
- **OpenAI:** gpt-4o ($2.50/$10.00)

