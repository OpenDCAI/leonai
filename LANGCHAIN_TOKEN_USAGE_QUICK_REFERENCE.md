# LangChain Token Usage 快速参考

## 核心数据结构

### UsageMetadata（标准化）
```python
{
    "input_tokens": int,              # 必需
    "output_tokens": int,             # 必需
    "total_tokens": int,              # 必需
    "input_token_details": {          # 可选
        "audio": int,
        "cache_creation": int,
        "cache_read": int,
        # 可能的额外字段：priority_*, flex_*, ephemeral_*
    },
    "output_token_details": {         # 可选
        "audio": int,
        "reasoning": int,
        # 可能的额外字段：priority_*, flex_*
    }
}
```

### response_metadata（原始数据）
```python
{
    # Provider 特定的原始数据
    # OpenAI: token_usage, model_name, system_fingerprint, finish_reason, logprobs
    # Anthropic: model, stop_reason, usage
}
```

## 访问方式

### 推荐方式（标准化）
```python
message.usage_metadata['input_tokens']
message.usage_metadata['output_tokens']
message.usage_metadata['total_tokens']
message.usage_metadata.get('input_token_details', {}).get('cache_read')
message.usage_metadata.get('output_token_details', {}).get('reasoning')
```

### 不推荐方式（Provider 特定）
```python
message.response_metadata  # 避免直接使用，provider 差异大
```

## Provider 差异速查表

| 特性 | OpenAI | Anthropic |
|------|--------|-----------|
| **缓存支持** | ✅ cached_tokens | ✅ cache_read_input_tokens |
| **缓存创建** | ❌ | ✅ cache_creation_input_tokens |
| **推理 token** | ✅ reasoning_tokens (o1) | ❌ |
| **input_tokens 含缓存** | ✅ | ❌ 需手动加回 |
| **缓存 TTL** | ❌ | ✅ ephemeral_* |
| **Service Tier** | ✅ priority/flex | ❌ |

## 关键差异

### OpenAI
```python
# input_tokens 已包含缓存 token
usage_metadata['input_tokens']  # 包含 cache_read

# 缓存 token 在详情中
input_details['cache_read']  # 从缓存读取的 token
```

### Anthropic
```python
# input_tokens 不包含缓存 token
response_metadata['usage']['input_tokens']  # 不包含缓存

# 需要手动计算真实总数
true_input_tokens = (
    response_metadata['usage']['input_tokens'] +
    response_metadata['usage'].get('cache_read_input_tokens', 0) +
    response_metadata['usage'].get('cache_creation_input_tokens', 0)
)

# 但 usage_metadata 已规范化
usage_metadata['input_tokens']  # 已包含缓存（LangChain 计算）
```

## 常见操作

### 1. 获取基础 token 数
```python
if message.usage_metadata:
    input_tokens = message.usage_metadata['input_tokens']
    output_tokens = message.usage_metadata['output_tokens']
    total_tokens = message.usage_metadata['total_tokens']
```

### 2. 检查缓存效果
```python
input_details = message.usage_metadata.get('input_token_details', {})
cache_read = input_details.get('cache_read', 0)
cache_creation = input_details.get('cache_creation', 0)

if cache_read + cache_creation > 0:
    cache_hit_rate = cache_read / (cache_read + cache_creation)
```

### 3. 检查推理 token（o1 模型）
```python
output_details = message.usage_metadata.get('output_token_details', {})
reasoning_tokens = output_details.get('reasoning', 0)
actual_output = message.usage_metadata['output_tokens'] - reasoning_tokens
```

### 4. 合并流式 token
```python
from langchain_core.messages.ai import add_usage

total_usage = None
for chunk in llm.stream(messages):
    if chunk.usage_metadata:
        total_usage = add_usage(total_usage, chunk.usage_metadata)
```

### 5. 减法操作
```python
from langchain_core.messages.ai import subtract_usage

remaining = subtract_usage(total_budget, used_tokens)
```

## 成本计算示例

### OpenAI
```python
# gpt-4-turbo: $0.01/1K input, $0.03/1K output
usage = message.usage_metadata
cost = (
    usage['input_tokens'] * 0.01 +
    usage['output_tokens'] * 0.03
) / 1000
```

### Anthropic
```python
# claude-3-5-sonnet: $0.003/1K input, $0.015/1K output
# 缓存读取: $0.0003/1K (10% of normal)
usage = message.usage_metadata
input_details = usage.get('input_token_details', {})

base_input = usage['input_tokens'] - input_details.get('cache_read', 0)
cache_read = input_details.get('cache_read', 0)

cost = (
    base_input * 0.003 +
    cache_read * 0.0003 +
    usage['output_tokens'] * 0.015
) / 1000
```

## 版本要求

- **langchain-core >= 0.3.9** - 支持 input_token_details 和 output_token_details
- **langchain-openai >= 0.1.0** - 完整的 token 详情支持
- **langchain-anthropic >= 0.1.0** - 缓存 token 支持

## 常见问题

### Q: 为什么 Anthropic 的 input_tokens 和 response_metadata 中的不一样？
A: Anthropic 的 API 返回的 input_tokens 不包含缓存 token，LangChain 在 usage_metadata 中已规范化为包含缓存的总数。

### Q: 如何区分缓存创建和缓存读取？
A: 
- `cache_creation`: 第一次调用时，创建缓存消耗的 token
- `cache_read`: 后续调用时，从缓存读取的 token

### Q: 推理 token 是什么？
A: OpenAI o1 模型的思维链过程中生成的 token，不作为模型输出返回，但计入成本。

### Q: 如何在流式处理中获取完整的 token 统计？
A: 使用 `add_usage()` 函数合并每个 chunk 的 usage_metadata。

### Q: response_metadata 和 usage_metadata 的区别？
A: 
- `usage_metadata`: 标准化的 TypedDict，跨 provider 一致
- `response_metadata`: 原始 provider 数据，差异大，不推荐直接使用

## 源码位置

| 文件 | 位置 | 说明 |
|------|------|------|
| UsageMetadata 定义 | langchain_core/messages/ai.py | 第 104-158 行 |
| InputTokenDetails | langchain_core/messages/ai.py | 第 38-72 行 |
| OutputTokenDetails | langchain_core/messages/ai.py | 第 74-102 行 |
| ChatOpenAI 转换 | langchain_openai/chat_models/base.py | 第 3623-3708 行 |
| ChatAnthropic 转换 | langchain_anthropic/chat_models.py | 第 2082-2122 行 |
| add_usage 函数 | langchain_core/messages/ai.py | 第 693-749 行 |
| subtract_usage 函数 | langchain_core/messages/ai.py | 第 752-812 行 |

## 最佳实践

1. **优先使用 usage_metadata** - 标准化、跨 provider 一致
2. **检查 None** - 某些情况下 usage_metadata 可能为 None
3. **使用 get() 访问可选字段** - input_token_details 和 output_token_details 是可选的
4. **流式处理用 add_usage()** - 正确合并 token 统计
5. **避免直接访问 response_metadata** - 除非需要 provider 特定的信息
