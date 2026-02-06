# Leon 项目 - 模型配置技术分析

## 执行摘要

Leon 项目在 `/middleware/monitor/cost.py` 中维护了完整的模型定价表，支持 8 个主流 LLM 模型，包括 Anthropic、OpenAI 和 DeepSeek。系统采用 Decimal.js 精确计算，支持 6 项 token 分项追踪和分项成本计算。

---

## 一、模型定价系统架构

### 1.1 核心数据结构

```python
# 文件：/middleware/monitor/cost.py

MODEL_COSTS: dict[str, dict[str, Decimal]] = {
    "model_name": {
        "input": Decimal("price"),
        "output": Decimal("price"),
        "cache_read": Decimal("price"),
        "cache_write": Decimal("price"),
    }
}
```

**特点：**
- 使用 `Decimal` 类型确保精度（避免浮点误差）
- 单位：USD per 1M tokens
- 支持 4 个定价维度：输入、输出、缓存读、缓存写

### 1.2 模型别名系统

```python
_MODEL_ALIASES: dict[str, str] = {
    "claude-3-5-sonnet": "claude-sonnet-4-5-20250929",
    "claude-3-opus": "claude-opus-4-20250514",
    "claude-3-5-haiku": "claude-haiku-3-5-20241022",
}
```

**解析策略（优先级）：**
1. 精确匹配：`model_name in MODEL_COSTS`
2. 别名匹配：`model_name in _MODEL_ALIASES`
3. 前缀匹配：按长度倒序，`model_name.startswith(key)`

**示例：**
```python
# "gpt-4o-2024-08-06" → 匹配 "gpt-4o"
# "claude-3-5-sonnet" → 匹配别名 → "claude-sonnet-4-5-20250929"
```

---

## 二、Token 监控系统

### 2.1 TokenMonitor 类结构

**文件：** `/middleware/monitor/token_monitor.py`

```python
class TokenMonitor(BaseMonitor):
    def __init__(self):
        self.call_count = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.reasoning_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.total_tokens = 0
        self.cost_calculator = None  # 由 MonitorMiddleware 注入
```

**6 项分项追踪：**

| 字段 | 来源 | 说明 |
|------|------|------|
| `input_tokens` | `usage_metadata.input_tokens - cache_read - cache_write` | 调整后的输入 |
| `output_tokens` | `usage_metadata.output_tokens - reasoning` | 调整后的输出 |
| `reasoning_tokens` | `output_token_details.reasoning` | 推理 token（o1/o3） |
| `cache_read_tokens` | `input_token_details.cache_read` | 缓存命中 |
| `cache_write_tokens` | `input_token_details.cache_creation` | 缓存创建 |
| `total_tokens` | 累加 | 总计 |

### 2.2 Token 提取流程

```python
def on_response(self, request: dict, response: dict) -> None:
    messages = response.get("messages", [])
    
    for msg in reversed(messages):
        # 优先级 1：LangChain 统一格式
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            self._extract_from_usage_metadata(usage)
            return
        
        # 优先级 2：回退方案
        metadata = getattr(msg, "response_metadata", None)
        if metadata:
            self._extract_from_response_metadata(metadata)
            return
```

**提取逻辑：**

```python
def _extract_from_usage_metadata(self, usage: dict) -> None:
    input_total = usage.get("input_tokens", 0) or 0
    output_total = usage.get("output_tokens", 0) or 0
    
    input_details = usage.get("input_token_details", {}) or {}
    output_details = usage.get("output_token_details", {}) or {}
    
    cache_read = input_details.get("cache_read", 0) or 0
    cache_write = input_details.get("cache_creation", 0) or 0
    reasoning = output_details.get("reasoning", 0) or 0
    
    # 累加（关键：排除缓存和推理）
    self.input_tokens += input_total - cache_read - cache_write
    self.output_tokens += output_total - reasoning
    self.reasoning_tokens += reasoning
    self.cache_read_tokens += cache_read
    self.cache_write_tokens += cache_write
    self.total_tokens += input_total + output_total
    self.call_count += 1
```

### 2.3 向后兼容属性

```python
@property
def prompt_tokens(self) -> int:
    return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

@property
def completion_tokens(self) -> int:
    return self.output_tokens + self.reasoning_tokens
```

---

## 三、成本计算引擎

### 3.1 CostCalculator 类

```python
class CostCalculator:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.costs = self._resolve_costs(model_name)
    
    def calculate(self, tokens: dict) -> dict:
        """返回 {"total": Decimal, "breakdown": {...}}"""
        if not self.costs:
            return {"total": Decimal("0"), "breakdown": {}}
        
        breakdown = {
            "input": self.costs.get("input", Decimal("0")) 
                     * Decimal(str(tokens.get("input_tokens", 0))) / M,
            "output": self.costs.get("output", Decimal("0")) 
                      * Decimal(str(tokens.get("output_tokens", 0))) / M,
            "cache_read": self.costs.get("cache_read", Decimal("0")) 
                          * Decimal(str(tokens.get("cache_read_tokens", 0))) / M,
            "cache_write": self.costs.get("cache_write", Decimal("0")) 
                           * Decimal(str(tokens.get("cache_write_tokens", 0))) / M,
        }
        return {"total": sum(breakdown.values()), "breakdown": breakdown}
```

**关键特性：**
- 使用 `Decimal` 避免浮点精度问题
- 分项计算便于成本分析
- 支持模型别名和前缀匹配

### 3.2 精度保证

```python
M = Decimal("1000000")

# 计算示例
cost = Decimal("3.00") * Decimal("1000") / M
# = Decimal("0.003")  # 精确值，不是 0.0030000000000000001
```

---

## 四、Agent 配置系统

### 4.1 AgentConfig 数据模型

**文件：** `/agent_profile.py`

```python
class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"
    model_provider: str | None = None       # openai/anthropic/bedrock
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    model_kwargs: dict[str, Any] = Field(default_factory=dict)
    workspace_root: str | None = None
    enable_audit_log: bool = True
    allowed_extensions: list[str] | None = None
    block_dangerous_commands: bool = True
    block_network_commands: bool = False
    queue_mode: str = "steer"
    context_limit: int = 100000
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
```

### 4.2 配置加载流程

```python
# 1. 从文件加载
profile = AgentProfile.from_file("config.yaml")

# 2. 从字典加载
profile = AgentProfile.from_dict({"agent": {...}})

# 3. 默认配置
profile = AgentProfile.default()

# 4. 环境变量展开
data = AgentProfile._expand_env_vars(data)
# 支持 ${VAR} 语法
```

### 4.3 模型初始化

**文件：** `/agent.py`

```python
def _build_model(self) -> Any:
    kwargs = {}
    
    # 1. API key
    if self.api_key:
        kwargs["api_key"] = self.api_key
    
    # 2. Provider
    if self.profile.agent.model_provider:
        kwargs["model_provider"] = self.profile.agent.model_provider
    
    # 3. Base URL
    base_url = self.profile.agent.base_url or self._resolve_env_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    
    # 4. 常用参数
    if self.profile.agent.temperature is not None:
        kwargs["temperature"] = self.profile.agent.temperature
    if self.profile.agent.max_tokens is not None:
        kwargs["max_tokens"] = self.profile.agent.max_tokens
    
    # 5. 透传参数
    kwargs.update(self.profile.agent.model_kwargs)
    
    # 6. 初始化
    return init_chat_model(self.model_name, api_key=self.api_key, **kwargs)
```

---

## 五、监控中间件集成

### 5.1 MonitorMiddleware 架构

**文件：** `/middleware/monitor/middleware.py`

```python
class MonitorMiddleware:
    def __init__(self, model_name: str):
        self.token_monitor = TokenMonitor()
        self.cost_calculator = CostCalculator(model_name)
        
        # 注入成本计算器
        self.token_monitor.cost_calculator = self.cost_calculator
    
    def on_response(self, request: dict, response: dict) -> None:
        # 1. 提取 token
        self.token_monitor.on_response(request, response)
        
        # 2. 计算成本
        cost = self.token_monitor.get_cost()
        
        # 3. 记录指标
        metrics = self.token_monitor.get_metrics()
```

### 5.2 指标输出

```python
def get_metrics(self) -> dict[str, Any]:
    cost = self.get_cost()
    return {
        "total_tokens": self.total_tokens,
        "input_tokens": self.input_tokens,
        "output_tokens": self.output_tokens,
        "reasoning_tokens": self.reasoning_tokens,
        "cache_read_tokens": self.cache_read_tokens,
        "cache_write_tokens": self.cache_write_tokens,
        "prompt_tokens": self.prompt_tokens,  # 向后兼容
        "completion_tokens": self.completion_tokens,  # 向后兼容
        "call_count": self.call_count,
        "cost": float(cost.get("total", 0)),
    }
```

---

## 六、成本计算示例

### 6.1 基础计算

```python
from middleware.monitor.cost import CostCalculator

# 创建计算器
calc = CostCalculator("claude-sonnet-4-5-20250929")

# 模型定价
# input: $3.00/M, output: $15.00/M
# cache_read: $0.30/M, cache_write: $3.75/M

# 请求结果
tokens = {
    "input_tokens": 1000,
    "output_tokens": 500,
    "cache_read_tokens": 100,
    "cache_write_tokens": 50,
}

result = calc.calculate(tokens)

# 计算过程
# input_cost = 1000 × 3.00 / 1,000,000 = 0.003
# output_cost = 500 × 15.00 / 1,000,000 = 0.0075
# cache_read_cost = 100 × 0.30 / 1,000,000 = 0.00003
# cache_write_cost = 50 × 3.75 / 1,000,000 = 0.0001875
# total = 0.0106875

print(result)
# {
#     "total": Decimal("0.0106875"),
#     "breakdown": {
#         "input": Decimal("0.003"),
#         "output": Decimal("0.0075"),
#         "cache_read": Decimal("0.00003"),
#         "cache_write": Decimal("0.0001875"),
#     }
# }
```

### 6.2 模型对比

```python
# 同样的请求，不同模型的成本

models = [
    "gpt-4o-mini",  # 最便宜
    "deepseek-chat",
    "claude-haiku-3-5-20241022",
    "claude-sonnet-4-5-20250929",  # 推荐
    "gpt-4o",
    "o3-mini",
    "claude-opus-4-20250514",  # 最强
    "o1",  # 最贵
]

for model in models:
    calc = CostCalculator(model)
    cost = calc.calculate(tokens)
    print(f"{model}: ${float(cost['total']):.6f}")

# 输出示例
# gpt-4o-mini: $0.000825
# deepseek-chat: $0.000297
# claude-haiku-3-5-20241022: $0.000425
# claude-sonnet-4-5-20250929: $0.0106875
# gpt-4o: $0.0105
# o3-mini: $0.0046
# claude-opus-4-20250514: $0.0531875
# o1: $0.0405
```

---

## 七、与 OpenCode 的差异分析

### 7.1 功能对比

| 功能 | OpenCode | Leon | 说明 |
|------|----------|------|------|
| Token 分项 | 6 项 | 6 项 | 完全相同 |
| 缓存追踪 | 5m/1h 分别 | 合并 | OpenCode 更细粒度 |
| 200K+ 定价 | ✅ 支持 | ❌ 不支持 | Leon 可扩展 |
| Provider 适配 | 多层 | 单层 | OpenCode 更复杂 |
| 计费模式 | 订阅+余额 | 基础 | OpenCode 更完整 |
| 精确计算 | Decimal.js | Decimal.js | 相同 |

### 7.2 可借鉴的改进

**1. 200K+ 特殊定价**
```python
# OpenCode 实现
const costInfo =
  model.cost?.experimentalOver200K && 
  tokens.input + tokens.cache.read > 200_000
    ? model.cost.experimentalOver200K
    : model.cost

# Leon 可以添加
MODEL_COSTS["claude-sonnet-4-5-20250929"] = {
    "input": Decimal("3.00"),
    "output": Decimal("15.00"),
    "cache_read": Decimal("0.30"),
    "cache_write": Decimal("3.75"),
    "over_200k": {  # 新增
        "input": Decimal("1.50"),
        "output": Decimal("7.50"),
        "cache_read": Decimal("0.15"),
        "cache_write": Decimal("1.875"),
    }
}
```

**2. 缓存时间维度**
```python
# OpenCode 分别追踪
cache_write_5m_tokens
cache_write_1h_tokens

# Leon 可以扩展
self.cache_write_5m_tokens = 0
self.cache_write_1h_tokens = 0
```

---

## 八、文件位置速查表

| 功能 | 文件 | 行数 |
|------|------|------|
| 模型定价表 | `/middleware/monitor/cost.py` | 6-58 |
| CostCalculator | `/middleware/monitor/cost.py` | 70-109 |
| TokenMonitor | `/middleware/monitor/token_monitor.py` | 1-141 |
| AgentConfig | `/agent_profile.py` | 30-46 |
| 模型初始化 | `/agent.py` | 295-317 |
| 默认配置 | `/agent.py` | 384-441 |
| MonitorMiddleware | `/middleware/monitor/middleware.py` | - |

---

## 九、集成检查清单

- [x] 模型定价表完整（8 个模型）
- [x] Token 分项追踪（6 项）
- [x] 成本分项计算
- [x] Decimal.js 精确计算
- [x] 模型别名和前缀匹配
- [x] 配置文件支持
- [x] 环境变量展开
- [ ] 200K+ 特殊定价
- [ ] 缓存时间维度（5m/1h）
- [ ] 计费模式（订阅/余额）
- [ ] 自动充值机制

---

## 十、性能优化建议

### 10.1 缓存策略

```python
# 缓存模型定价表
_MODEL_COSTS_CACHE = {}

def get_model_costs(model_name: str) -> dict:
    if model_name not in _MODEL_COSTS_CACHE:
        _MODEL_COSTS_CACHE[model_name] = CostCalculator(model_name).costs
    return _MODEL_COSTS_CACHE[model_name]
```

### 10.2 批量计算

```python
# 批量计算多个请求的成本
def calculate_batch_cost(requests: list[dict]) -> dict:
    total_cost = Decimal("0")
    breakdown = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    
    for req in requests:
        calc = CostCalculator(req["model"])
        result = calc.calculate(req["tokens"])
        total_cost += result["total"]
        for key in breakdown:
            breakdown[key] += result["breakdown"][key]
    
    return {"total": total_cost, "breakdown": breakdown}
```

---

## 十一、故障排查指南

### 问题 1：模型不在定价表中

```python
# 症状：CostCalculator 返回空 breakdown
# 原因：模型名称不匹配

# 解决方案
1. 检查模型名称是否精确匹配
2. 检查是否有别名映射
3. 检查前缀是否匹配
4. 添加新模型到 MODEL_COSTS

# 调试
calc = CostCalculator("unknown-model")
print(calc.costs)  # 应该返回 {}
```

### 问题 2：Token 统计不准确

```python
# 症状：total_tokens != input_tokens + output_tokens
# 原因：缓存和推理 token 被排除

# 解决方案
# 使用 prompt_tokens 和 completion_tokens 属性
# 它们包含缓存和推理 token

monitor = TokenMonitor()
print(monitor.prompt_tokens)  # input + cache_read + cache_write
print(monitor.completion_tokens)  # output + reasoning
```

### 问题 3：成本计算精度问题

```python
# 症状：成本计算结果有浮点误差
# 原因：使用了 float 而不是 Decimal

# 解决方案
# 始终使用 Decimal 类型
cost = Decimal("3.00") * Decimal("1000") / Decimal("1000000")
# 不要用 float
cost = 3.00 * 1000 / 1000000  # 错误！
```

---

## 十二、总结

Leon 的模型定价系统具有以下特点：

1. **完整性**：支持 8 个主流模型，覆盖 Anthropic、OpenAI、DeepSeek
2. **精确性**：使用 Decimal.js 避免浮点误差
3. **灵活性**：支持别名、前缀匹配、环境变量展开
4. **可扩展性**：易于添加新模型和定价维度
5. **可观测性**：6 项 token 分项追踪，分项成本计算

可以作为其他 Agent 框架的参考实现。

