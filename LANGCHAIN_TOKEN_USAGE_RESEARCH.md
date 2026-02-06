# LangChain Token Usage 数据结构研究

## 概述

LangChain 在 `AIMessage` 中提供了两个关键的 token 使用信息字段：
1. **`usage_metadata`** - 标准化的 token 使用统计（TypedDict）
2. **`response_metadata`** - 原始 provider 响应元数据（Dict）

## 1. UsageMetadata 结构（标准化）

### 定义位置
`langchain_core/messages/ai.py` 第 104-158 行

### 完整结构

```python
class UsageMetadata(TypedDict):
    """标准化的 token 使用统计，跨所有 provider 一致"""
    
    # 必需字段
    input_tokens: int
    """输入（提示）token 总数"""
    
    output_tokens: int
    """输出（完成）token 总数"""
    
    total_tokens: int
    """总 token 数 = input_tokens + output_tokens"""
    
    # 可选字段（NotRequired）
    input_token_details: InputTokenDetails  # 可选
    """输入 token 的详细分项"""
    
    output_token_details: OutputTokenDetails  # 可选
    """输出 token 的详细分项"""
```

### InputTokenDetails 结构

```python
class InputTokenDetails(TypedDict, total=False):
    """输入 token 的详细分项（不需要求和到总数）"""
    
    audio: int
    """音频输入 token"""
    
    cache_creation: int
    """缓存创建时消耗的 token（缓存未命中）
    这些 token 被用来创建缓存"""
    
    cache_read: int
    """从缓存读取的 token（缓存命中）
    这些 token 的模型状态从缓存读取"""
    
    # 可能的额外字段（provider 特定）
    # - priority_* / flex_* (OpenAI service tier)
    # - ephemeral_5m_input_tokens (Anthropic)
    # - ephemeral_1h_input_tokens (Anthropic)
```

### OutputTokenDetails 结构

```python
class OutputTokenDetails(TypedDict, total=False):
    """输出 token 的详细分项（不需要求和到总数）"""
    
    audio: int
    """音频输出 token"""
    
    reasoning: int
    """推理 token（OpenAI o1 模型的思维链过程）
    这些 token 不作为模型输出返回"""
    
    # 可能的额外字段（provider 特定）
    # - priority_* / flex_* (OpenAI service tier)
```

## 2. ChatOpenAI 的 Token 使用映射

### 源码位置
`langchain_openai/chat_models/base.py` 第 3623-3708 行

### 两个转换函数

#### 2.1 `_create_usage_metadata()` - 标准 Chat Completions API

**源数据来自 OpenAI 响应：**
```python
{
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "prompt_tokens_details": {
        "audio_tokens": int,
        "cached_tokens": int,  # 缓存命中的 token
    },
    "completion_tokens_details": {
        "audio_tokens": int,
        "reasoning_tokens": int,  # o1 模型的推理 token
    }
}
```

**转换逻辑：**
```python
def _create_usage_metadata(oai_token_usage: dict, service_tier: str | None = None) -> UsageMetadata:
    input_tokens = oai_token_usage.get("prompt_tokens") or 0
    output_tokens = oai_token_usage.get("completion_tokens") or 0
    total_tokens = oai_token_usage.get("total_tokens") or input_tokens + output_tokens
    
    # 处理 service tier（priority/flex）
    service_tier_prefix = f"{service_tier}_" if service_tier in {"priority", "flex"} else ""
    
    # 输入 token 详情
    input_token_details: dict = {
        "audio": prompt_tokens_details.get("audio_tokens"),
        f"{service_tier_prefix}cache_read": prompt_tokens_details.get("cached_tokens"),
    }
    
    # 输出 token 详情
    output_token_details: dict = {
        "audio": completion_tokens_details.get("audio_tokens"),
        f"{service_tier_prefix}reasoning": completion_tokens_details.get("reasoning_tokens"),
    }
    
    # 如果有 service tier，计算 tier 特定的 token 数
    if service_tier is not None:
        input_token_details[service_tier] = input_tokens - input_token_details.get(
            f"{service_tier_prefix}cache_read", 0
        )
        output_token_details[service_tier] = output_tokens - output_token_details.get(
            f"{service_tier_prefix}reasoning", 0
        )
    
    return UsageMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_token_details=InputTokenDetails(
            **{k: v for k, v in input_token_details.items() if v is not None}
        ),
        output_token_details=OutputTokenDetails(
            **{k: v for k, v in output_token_details.items() if v is not None}
        ),
    )
```

#### 2.2 `_create_usage_metadata_responses()` - Responses API

**源数据来自 OpenAI Responses API：**
```python
{
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int,
    "input_tokens_details": {
        "cached_tokens": int,
    },
    "output_tokens_details": {
        "reasoning_tokens": int,
    }
}
```

**转换逻辑类似，但字段名略有不同**

### 关键特性

1. **缓存 token 支持**
   - `cache_read`: 从缓存读取的 token（OpenAI 缓存命中）
   - 直接来自 OpenAI 的 `cached_tokens` 字段

2. **推理 token 支持**
   - `reasoning`: o1 模型的思维链 token
   - 直接来自 OpenAI 的 `reasoning_tokens` 字段

3. **Service Tier 支持**
   - 当使用 priority/flex tier 时，添加 `priority_*` 或 `flex_*` 前缀
   - 计算 tier 特定的 token 数（排除缓存和推理 token）

## 3. ChatAnthropic 的 Token 使用映射

### 源码位置
`langchain_anthropic/chat_models.py` 第 2082-2122 行

### 单一转换函数

#### `_create_usage_metadata()` - Anthropic API

**源数据来自 Anthropic 响应：**
```python
{
    "input_tokens": int,  # 不包含缓存 token
    "output_tokens": int,
    "cache_read_input_tokens": int,  # 从缓存读取的 token
    "cache_creation_input_tokens": int,  # 创建缓存时消耗的 token
    "cache_creation": {  # 可选，缓存 TTL 信息
        "ephemeral_5m_input_tokens": int,
        "ephemeral_1h_input_tokens": int,
    }
}
```

**转换逻辑：**
```python
def _create_usage_metadata(anthropic_usage: BaseModel) -> UsageMetadata:
    """
    注意：Anthropic 的 input_tokens 不包含缓存 token，
    需要手动加上 cache_read 和 cache_creation 来获得真实总数
    """
    
    input_token_details: dict = {
        "cache_read": getattr(anthropic_usage, "cache_read_input_tokens", None),
        "cache_creation": getattr(anthropic_usage, "cache_creation_input_tokens", None),
    }
    
    # 处理缓存 TTL 信息
    cache_creation = getattr(anthropic_usage, "cache_creation", None)
    if cache_creation:
        if isinstance(cache_creation, BaseModel):
            cache_creation = cache_creation.model_dump()
        for k in ("ephemeral_5m_input_tokens", "ephemeral_1h_input_tokens"):
            input_token_details[k] = cache_creation.get(k)
    
    # 计算真实的输入 token 总数
    # Anthropic 的 input_tokens 不包含缓存 token，需要加回来
    input_tokens = (
        (getattr(anthropic_usage, "input_tokens", 0) or 0)  # 基础输入 token
        + (input_token_details["cache_read"] or 0)  # 从缓存读取的 token
        + (input_token_details["cache_creation"] or 0)  # 创建缓存的 token
    )
    output_tokens = getattr(anthropic_usage, "output_tokens", 0) or 0
    
    return UsageMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        input_token_details=InputTokenDetails(
            **{k: v for k, v in input_token_details.items() if v is not None},
        ),
    )
```

### 关键特性

1. **缓存 token 支持**
   - `cache_read`: 从缓存读取的 token
   - `cache_creation`: 创建缓存时消耗的 token
   - 来自 Anthropic 的 `cache_read_input_tokens` 和 `cache_creation_input_tokens`

2. **缓存 TTL 信息**
   - `ephemeral_5m_input_tokens`: 5 分钟临时缓存的 token
   - `ephemeral_1h_input_tokens`: 1 小时临时缓存的 token

3. **重要差异**
   - Anthropic 的 `input_tokens` 不包含缓存 token
   - LangChain 需要手动计算真实的 `input_tokens` 总数
   - 这与 OpenAI 的行为不同（OpenAI 的 `prompt_tokens` 包含缓存 token）

## 4. response_metadata 结构

### 定义位置
`langchain_core/messages/base.py` 第 114-115 行

### 结构

```python
response_metadata: dict = Field(default_factory=dict)
"""
示例：响应头、logprobs、token 计数、模型名称等

这是一个通用的 Dict，包含 provider 特定的原始数据。
不同 provider 返回的内容差异很大。
"""
```

### ChatOpenAI 的 response_metadata 示例

```python
{
    "token_usage": {
        "completion_tokens": 164,
        "prompt_tokens": 17,
        "total_tokens": 181,
        "prompt_tokens_details": {
            "audio_tokens": 0,
            "cached_tokens": 0,
        },
        "completion_tokens_details": {
            "audio_tokens": 0,
            "reasoning_tokens": 0,
        }
    },
    "model_name": "gpt-4-turbo",
    "system_fingerprint": "fp_76f018034d",
    "finish_reason": "stop",
    "logprobs": None,
}
```

### ChatAnthropic 的 response_metadata 示例

```python
{
    "model": "claude-3-5-sonnet-20241022",
    "stop_reason": "end_turn",
    "usage": {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 20,
        "cache_creation_input_tokens": 10,
    }
}
```

## 5. 规范化对比

### LangChain 的规范化策略

| 方面 | 策略 |
|------|------|
| **标准化** | ✅ 完全规范化到 `UsageMetadata` |
| **透传** | ✅ 原始数据保留在 `response_metadata` |
| **缓存支持** | ✅ 通过 `input_token_details` 支持 |
| **推理支持** | ✅ 通过 `output_token_details` 支持 |
| **Provider 差异处理** | ✅ 在转换函数中处理 |

### 关键差异处理

1. **OpenAI vs Anthropic 缓存计算**
   - OpenAI: `prompt_tokens` 已包含缓存 token
   - Anthropic: `input_tokens` 不包含缓存 token，需要手动加回

2. **字段名映射**
   - OpenAI: `cached_tokens` → `cache_read`
   - Anthropic: `cache_read_input_tokens` → `cache_read`

3. **额外字段**
   - OpenAI: `reasoning_tokens` → `reasoning`
   - Anthropic: `ephemeral_*_input_tokens` → 直接保留

## 6. 统一接口

### 访问 token 使用信息

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

llm = ChatOpenAI(model="gpt-4-turbo")
message: AIMessage = llm.invoke("Hello")

# 方式 1: 标准化的 usage_metadata（推荐）
if message.usage_metadata:
    print(f"Input tokens: {message.usage_metadata['input_tokens']}")
    print(f"Output tokens: {message.usage_metadata['output_tokens']}")
    print(f"Total tokens: {message.usage_metadata['total_tokens']}")
    
    # 访问详细分项
    if input_details := message.usage_metadata.get('input_token_details'):
        print(f"Cache read: {input_details.get('cache_read')}")
        print(f"Cache creation: {input_details.get('cache_creation')}")
    
    if output_details := message.usage_metadata.get('output_token_details'):
        print(f"Reasoning: {output_details.get('reasoning')}")

# 方式 2: 原始 provider 数据（不推荐，provider 特定）
print(message.response_metadata)
```

### 流式处理中的 token 合并

```python
from langchain_core.messages.ai import add_usage

# 合并多个消息的 token 使用
total_usage = None
for chunk in llm.stream("Hello"):
    if chunk.usage_metadata:
        total_usage = add_usage(total_usage, chunk.usage_metadata)

print(f"Total tokens across stream: {total_usage['total_tokens']}")
```

## 7. 版本信息

- **langchain-core**: 0.3.9+（引入 `input_token_details` 和 `output_token_details`）
- **langchain-openai**: 最新版本支持完整的 token 详情
- **langchain-anthropic**: 最新版本支持缓存 token 和 TTL 信息

## 8. 总结

### 关键发现

1. **LangChain 已完全规范化 token 使用**
   - `UsageMetadata` 提供跨 provider 的一致接口
   - 支持缓存、推理等高级特性

2. **Provider 差异被妥善处理**
   - ChatOpenAI: 支持 `cached_tokens`、`reasoning_tokens`、service tier
   - ChatAnthropic: 支持 `cache_read_input_tokens`、`cache_creation_input_tokens`、缓存 TTL

3. **两层设计**
   - `usage_metadata`: 标准化、跨 provider 一致
   - `response_metadata`: 原始数据、provider 特定

4. **可扩展性**
   - `InputTokenDetails` 和 `OutputTokenDetails` 支持额外的 provider 特定字段
   - 通过 `total=False` 允许灵活的字段组合

### 对 Leon 的启示

在 Leon 的 `TokenMonitor` 中：
- 优先使用 `message.usage_metadata` 而不是 `response_metadata`
- 支持 `input_token_details` 和 `output_token_details` 的详细分项
- 处理 Anthropic 的缓存 token 计算差异
- 考虑支持 OpenAI 的 service tier 和推理 token 统计
