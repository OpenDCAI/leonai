# LangChain Token Usage 研究总结

## 研究成果

本研究深入分析了 LangChain 的 ChatModel（ChatOpenAI 和 ChatAnthropic）在 response_metadata 中返回的 token usage 数据的完整结构。

### 研究文档清单

1. **LANGCHAIN_TOKEN_USAGE_RESEARCH.md** - 详细的技术研究文档
   - UsageMetadata 完整结构定义
   - ChatOpenAI 的 token 映射逻辑
   - ChatAnthropic 的 token 映射逻辑
   - response_metadata 结构对比
   - 规范化策略分析

2. **LANGCHAIN_TOKEN_USAGE_EXAMPLES.md** - 实战代码示例
   - 基础使用示例（OpenAI 和 Anthropic）
   - 流式处理中的 token 统计
   - 缓存 token 统计
   - 推理 token 统计（o1 模型）
   - 对比分析工具
   - Leon TokenMonitor 集成示例

3. **LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md** - 快速参考卡片
   - 核心数据结构速查
   - Provider 差异速查表
   - 常见操作代码片段
   - 成本计算示例
   - 常见问题解答

## 核心发现

### 1. LangChain 的两层设计

```
AIMessage
├── usage_metadata (标准化)
│   ├── input_tokens: int
│   ├── output_tokens: int
│   ├── total_tokens: int
│   ├── input_token_details: InputTokenDetails (可选)
│   └── output_token_details: OutputTokenDetails (可选)
│
└── response_metadata (原始数据)
    └── Provider 特定的原始数据
```

### 2. UsageMetadata 的完整字段

**必需字段：**
- `input_tokens`: 输入 token 总数
- `output_tokens`: 输出 token 总数
- `total_tokens`: 总 token 数

**可选字段：**
- `input_token_details`: 输入 token 详细分项
  - `audio`: 音频输入 token
  - `cache_creation`: 缓存创建时消耗的 token
  - `cache_read`: 从缓存读取的 token
  - `priority_*`, `flex_*`: OpenAI service tier
  - `ephemeral_*`: Anthropic 缓存 TTL

- `output_token_details`: 输出 token 详细分项
  - `audio`: 音频输出 token
  - `reasoning`: 推理 token（o1 模型）
  - `priority_*`, `flex_*`: OpenAI service tier

### 3. ChatOpenAI 的 Token 映射

**源数据字段：**
```python
{
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "prompt_tokens_details": {
        "audio_tokens": int,
        "cached_tokens": int,  # 缓存命中
    },
    "completion_tokens_details": {
        "audio_tokens": int,
        "reasoning_tokens": int,  # o1 推理
    }
}
```

**转换规则：**
- `prompt_tokens` → `input_tokens`（已包含缓存）
- `completion_tokens` → `output_tokens`
- `cached_tokens` → `cache_read`
- `reasoning_tokens` → `reasoning`
- Service tier 支持：添加 `priority_*` 或 `flex_*` 前缀

### 4. ChatAnthropic 的 Token 映射

**源数据字段：**
```python
{
    "input_tokens": int,  # 不包含缓存
    "output_tokens": int,
    "cache_read_input_tokens": int,
    "cache_creation_input_tokens": int,
    "cache_creation": {
        "ephemeral_5m_input_tokens": int,
        "ephemeral_1h_input_tokens": int,
    }
}
```

**转换规则：**
- `input_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens` → `input_tokens`（规范化）
- `output_tokens` → `output_tokens`
- `cache_read_input_tokens` → `cache_read`
- `cache_creation_input_tokens` → `cache_creation`
- `ephemeral_*_input_tokens` → 直接保留

**关键差异：**
- Anthropic 的 `input_tokens` 不包含缓存 token
- LangChain 在 `usage_metadata` 中已规范化为包含缓存的总数
- 这与 OpenAI 的行为不同

### 5. 规范化策略

| 方面 | 策略 |
|------|------|
| **标准化** | ✅ 完全规范化到 `UsageMetadata` |
| **透传** | ✅ 原始数据保留在 `response_metadata` |
| **缓存支持** | ✅ 通过 `input_token_details` 支持 |
| **推理支持** | ✅ 通过 `output_token_details` 支持 |
| **Provider 差异处理** | ✅ 在转换函数中处理 |

## 关键差异对比

### OpenAI vs Anthropic

| 特性 | OpenAI | Anthropic |
|------|--------|-----------|
| **缓存 token 字段** | `cached_tokens` | `cache_read_input_tokens` |
| **缓存创建字段** | 无 | `cache_creation_input_tokens` |
| **推理 token 字段** | `reasoning_tokens` (o1) | 无 |
| **input_tokens 包含缓存** | ✅ 是 | ❌ 否 |
| **缓存 TTL 信息** | 无 | ✅ `ephemeral_*` |
| **Service Tier** | ✅ priority/flex | ❌ |

## 统一接口

### 推荐的访问方式

```python
# 基础 token 数
input_tokens = message.usage_metadata['input_tokens']
output_tokens = message.usage_metadata['output_tokens']
total_tokens = message.usage_metadata['total_tokens']

# 缓存统计
input_details = message.usage_metadata.get('input_token_details', {})
cache_read = input_details.get('cache_read', 0)
cache_creation = input_details.get('cache_creation', 0)

# 推理 token
output_details = message.usage_metadata.get('output_token_details', {})
reasoning = output_details.get('reasoning', 0)
```

### 流式处理

```python
from langchain_core.messages.ai import add_usage

total_usage = None
for chunk in llm.stream(messages):
    if chunk.usage_metadata:
        total_usage = add_usage(total_usage, chunk.usage_metadata)
```

## 对 Leon 的启示

### TokenMonitor 实现建议

1. **优先使用 `usage_metadata`**
   - 标准化、跨 provider 一致
   - 避免直接访问 `response_metadata`

2. **支持详细分项统计**
   - `input_token_details`: 缓存、音频等
   - `output_token_details`: 推理、音频等

3. **处理 Provider 差异**
   - Anthropic 的缓存 token 计算差异
   - OpenAI 的 service tier 和推理 token

4. **流式处理支持**
   - 使用 `add_usage()` 合并 token 统计
   - 支持 `subtract_usage()` 进行预算计算

5. **成本计算**
   - 支持不同 provider 的定价模型
   - 缓存 token 的成本优惠
   - 推理 token 的成本溢价

### 代码集成示例

```python
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import add_usage, subtract_usage

class TokenMonitor:
    def __init__(self):
        self.total_usage = None
    
    def track_message(self, message: AIMessage) -> None:
        """追踪单个消息的 token 使用"""
        if message.usage_metadata:
            self.total_usage = add_usage(self.total_usage, message.usage_metadata)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self.total_usage:
            return {}
        
        usage = self.total_usage
        input_details = usage.get('input_token_details', {})
        output_details = usage.get('output_token_details', {})
        
        return {
            'input_tokens': usage['input_tokens'],
            'output_tokens': usage['output_tokens'],
            'total_tokens': usage['total_tokens'],
            'cache_read': input_details.get('cache_read', 0),
            'cache_creation': input_details.get('cache_creation', 0),
            'reasoning': output_details.get('reasoning', 0),
        }
```

## 版本信息

- **langchain-core**: 0.3.9+（引入 `input_token_details` 和 `output_token_details`）
- **langchain-openai**: 最新版本支持完整的 token 详情
- **langchain-anthropic**: 最新版本支持缓存 token 和 TTL 信息

## 源码参考

| 组件 | 文件 | 位置 |
|------|------|------|
| UsageMetadata | langchain_core/messages/ai.py | 104-158 |
| InputTokenDetails | langchain_core/messages/ai.py | 38-72 |
| OutputTokenDetails | langchain_core/messages/ai.py | 74-102 |
| ChatOpenAI 转换 | langchain_openai/chat_models/base.py | 3623-3708 |
| ChatAnthropic 转换 | langchain_anthropic/chat_models.py | 2082-2122 |
| add_usage | langchain_core/messages/ai.py | 693-749 |
| subtract_usage | langchain_core/messages/ai.py | 752-812 |

## 最佳实践

1. **优先使用 `usage_metadata`** - 标准化、跨 provider 一致
2. **检查 None** - 某些情况下 usage_metadata 可能为 None
3. **使用 get() 访问可选字段** - input_token_details 和 output_token_details 是可选的
4. **流式处理用 add_usage()** - 正确合并 token 统计
5. **避免直接访问 response_metadata** - 除非需要 provider 特定的信息
6. **支持缓存统计** - 对成本优化很重要
7. **支持推理 token** - o1 模型的成本计算需要

## 总结

LangChain 已经完全规范化了 token 使用统计，提供了跨 provider 的一致接口。通过 `UsageMetadata` 和详细的分项字段，可以精确追踪 token 使用情况，包括缓存、推理等高级特性。Leon 的 TokenMonitor 应该优先使用这些标准化接口，同时处理 provider 之间的差异。
