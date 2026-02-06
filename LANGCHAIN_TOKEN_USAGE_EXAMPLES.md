# LangChain Token Usage 实战示例

## 1. 基础使用示例

### 1.1 ChatOpenAI 的 token 使用

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# 简单调用
response = llm.invoke([HumanMessage(content="Hello, world!")])

# 访问 usage_metadata
print("=== Usage Metadata ===")
print(f"Input tokens: {response.usage_metadata['input_tokens']}")
print(f"Output tokens: {response.usage_metadata['output_tokens']}")
print(f"Total tokens: {response.usage_metadata['total_tokens']}")

# 访问详细分项
if input_details := response.usage_metadata.get('input_token_details'):
    print(f"\nInput Token Details:")
    for key, value in input_details.items():
        print(f"  {key}: {value}")

if output_details := response.usage_metadata.get('output_token_details'):
    print(f"\nOutput Token Details:")
    for key, value in output_details.items():
        print(f"  {key}: {value}")

# 原始 response_metadata（不推荐直接使用）
print("\n=== Response Metadata ===")
print(response.response_metadata)
```

**输出示例：**
```
=== Usage Metadata ===
Input tokens: 17
Output tokens: 164
Total tokens: 181

Input Token Details:
  audio: None
  cache_read: 0

Output Token Details:
  audio: None
  reasoning: 0

=== Response Metadata ===
{
    'token_usage': {
        'completion_tokens': 164,
        'prompt_tokens': 17,
        'total_tokens': 181,
        'prompt_tokens_details': {
            'audio_tokens': 0,
            'cached_tokens': 0
        },
        'completion_tokens_details': {
            'audio_tokens': 0,
            'reasoning_tokens': 0
        }
    },
    'model_name': 'gpt-4-turbo',
    'system_fingerprint': 'fp_76f018034d',
    'finish_reason': 'stop',
    'logprobs': None
}
```

### 1.2 ChatAnthropic 的 token 使用

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

response = llm.invoke([HumanMessage(content="Hello, world!")])

# 访问 usage_metadata
print("=== Usage Metadata ===")
print(f"Input tokens: {response.usage_metadata['input_tokens']}")
print(f"Output tokens: {response.usage_metadata['output_tokens']}")
print(f"Total tokens: {response.usage_metadata['total_tokens']}")

# 访问详细分项
if input_details := response.usage_metadata.get('input_token_details'):
    print(f"\nInput Token Details:")
    for key, value in input_details.items():
        print(f"  {key}: {value}")

# 原始 response_metadata
print("\n=== Response Metadata ===")
print(response.response_metadata)
```

**输出示例：**
```
=== Usage Metadata ===
Input tokens: 120  # 包含缓存 token
Output tokens: 50
Total tokens: 170

Input Token Details:
  cache_read: 20
  cache_creation: 10
  ephemeral_5m_input_tokens: 5
  ephemeral_1h_input_tokens: 5

=== Response Metadata ===
{
    'model': 'claude-3-5-sonnet-20241022',
    'stop_reason': 'end_turn',
    'usage': {
        'input_tokens': 100,  # 不包含缓存 token
        'output_tokens': 50,
        'cache_read_input_tokens': 20,
        'cache_creation_input_tokens': 10,
        'cache_creation': {
            'ephemeral_5m_input_tokens': 5,
            'ephemeral_1h_input_tokens': 5
        }
    }
}
```

## 2. 流式处理中的 token 统计

### 2.1 OpenAI 流式处理

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.messages.ai import add_usage

llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# 流式处理
total_usage = None
chunk_count = 0

for chunk in llm.stream([HumanMessage(content="Tell me a story")]):
    chunk_count += 1
    
    # 每个 chunk 可能包含 usage_metadata
    if chunk.usage_metadata:
        print(f"Chunk {chunk_count} usage: {chunk.usage_metadata}")
        total_usage = add_usage(total_usage, chunk.usage_metadata)

print(f"\n=== Total Usage ===")
print(f"Total chunks: {chunk_count}")
print(f"Total input tokens: {total_usage['input_tokens']}")
print(f"Total output tokens: {total_usage['output_tokens']}")
print(f"Total tokens: {total_usage['total_tokens']}")
```

### 2.2 Anthropic 流式处理

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.messages.ai import add_usage

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

total_usage = None
chunk_count = 0

for chunk in llm.stream([HumanMessage(content="Tell me a story")]):
    chunk_count += 1
    
    if chunk.usage_metadata:
        print(f"Chunk {chunk_count} usage: {chunk.usage_metadata}")
        total_usage = add_usage(total_usage, chunk.usage_metadata)

print(f"\n=== Total Usage ===")
print(f"Total chunks: {chunk_count}")
print(f"Total input tokens: {total_usage['input_tokens']}")
print(f"Total output tokens: {total_usage['output_tokens']}")
print(f"Total tokens: {total_usage['total_tokens']}")

# 访问缓存统计
if input_details := total_usage.get('input_token_details'):
    cache_read = input_details.get('cache_read', 0)
    cache_creation = input_details.get('cache_creation', 0)
    print(f"\nCache Statistics:")
    print(f"  Cache read tokens: {cache_read}")
    print(f"  Cache creation tokens: {cache_creation}")
    print(f"  Cache hit rate: {cache_read / (cache_read + cache_creation) * 100:.1f}%")
```

## 3. 缓存 token 统计

### 3.1 OpenAI 缓存统计

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# 第一次调用（缓存未命中）
response1 = llm.invoke([HumanMessage(content="Explain quantum computing")])
print("=== First Call (Cache Miss) ===")
print(f"Input tokens: {response1.usage_metadata['input_tokens']}")
print(f"Output tokens: {response1.usage_metadata['output_tokens']}")

# 第二次调用相同内容（缓存命中）
response2 = llm.invoke([HumanMessage(content="Explain quantum computing")])
print("\n=== Second Call (Cache Hit) ===")
print(f"Input tokens: {response2.usage_metadata['input_tokens']}")
print(f"Output tokens: {response2.usage_metadata['output_tokens']}")

# 比较缓存效果
input_details1 = response1.usage_metadata.get('input_token_details', {})
input_details2 = response2.usage_metadata.get('input_token_details', {})

print("\n=== Cache Comparison ===")
print(f"First call cache_read: {input_details1.get('cache_read', 0)}")
print(f"Second call cache_read: {input_details2.get('cache_read', 0)}")

# 计算节省的 token
saved_tokens = input_details2.get('cache_read', 0)
print(f"Tokens saved by cache: {saved_tokens}")
```

### 3.2 Anthropic 缓存统计

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# 第一次调用（缓存未命中）
response1 = llm.invoke([HumanMessage(content="Explain quantum computing")])
print("=== First Call (Cache Miss) ===")
usage1 = response1.usage_metadata
print(f"Input tokens (total): {usage1['input_tokens']}")
print(f"Output tokens: {usage1['output_tokens']}")

input_details1 = usage1.get('input_token_details', {})
print(f"  - Base input: {usage1['input_tokens'] - input_details1.get('cache_read', 0) - input_details1.get('cache_creation', 0)}")
print(f"  - Cache creation: {input_details1.get('cache_creation', 0)}")
print(f"  - Cache read: {input_details1.get('cache_read', 0)}")

# 第二次调用相同内容（缓存命中）
response2 = llm.invoke([HumanMessage(content="Explain quantum computing")])
print("\n=== Second Call (Cache Hit) ===")
usage2 = response2.usage_metadata
print(f"Input tokens (total): {usage2['input_tokens']}")
print(f"Output tokens: {usage2['output_tokens']}")

input_details2 = usage2.get('input_token_details', {})
print(f"  - Base input: {usage2['input_tokens'] - input_details2.get('cache_read', 0) - input_details2.get('cache_creation', 0)}")
print(f"  - Cache creation: {input_details2.get('cache_creation', 0)}")
print(f"  - Cache read: {input_details2.get('cache_read', 0)}")

# 计算节省的成本
# Anthropic 缓存读取成本是普通 token 的 10%
base_cost_per_token = 0.003  # $0.003 per 1K tokens
cache_read_cost_per_token = base_cost_per_token * 0.1

saved_cost = input_details2.get('cache_read', 0) * cache_read_cost_per_token / 1000
print(f"\n=== Cost Savings ===")
print(f"Tokens saved by cache: {input_details2.get('cache_read', 0)}")
print(f"Estimated cost savings: ${saved_cost:.6f}")
```

## 4. 推理 token 统计（OpenAI o1）

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="o1", temperature=1)  # o1 模型

response = llm.invoke([HumanMessage(content="Solve this complex math problem: ...")])

print("=== o1 Model Token Usage ===")
usage = response.usage_metadata
print(f"Input tokens: {usage['input_tokens']}")
print(f"Output tokens: {usage['output_tokens']}")
print(f"Total tokens: {usage['total_tokens']}")

# 访问推理 token
output_details = usage.get('output_token_details', {})
reasoning_tokens = output_details.get('reasoning', 0)
print(f"\nReasoning tokens: {reasoning_tokens}")
print(f"Actual output tokens: {usage['output_tokens'] - reasoning_tokens}")

# 推理 token 的成本通常更高
reasoning_cost_multiplier = 2  # 假设推理 token 成本是普通 token 的 2 倍
base_cost_per_token = 0.015  # $0.015 per 1K tokens

total_cost = (
    (usage['input_tokens'] * base_cost_per_token) +
    ((usage['output_tokens'] - reasoning_tokens) * base_cost_per_token) +
    (reasoning_tokens * base_cost_per_token * reasoning_cost_multiplier)
) / 1000

print(f"\nEstimated cost: ${total_cost:.6f}")
```

## 5. 对比分析工具

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

def compare_providers(prompt: str):
    """对比 OpenAI 和 Anthropic 的 token 使用"""
    
    # OpenAI
    openai_llm = ChatOpenAI(model="gpt-4-turbo")
    openai_response = openai_llm.invoke([HumanMessage(content=prompt)])
    openai_usage = openai_response.usage_metadata
    
    # Anthropic
    anthropic_llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    anthropic_response = anthropic_llm.invoke([HumanMessage(content=prompt)])
    anthropic_usage = anthropic_response.usage_metadata
    
    # 对比
    print("=== Token Usage Comparison ===")
    print(f"{'Metric':<20} {'OpenAI':<15} {'Anthropic':<15}")
    print("-" * 50)
    print(f"{'Input tokens':<20} {openai_usage['input_tokens']:<15} {anthropic_usage['input_tokens']:<15}")
    print(f"{'Output tokens':<20} {openai_usage['output_tokens']:<15} {anthropic_usage['output_tokens']:<15}")
    print(f"{'Total tokens':<20} {openai_usage['total_tokens']:<15} {anthropic_usage['total_tokens']:<15}")
    
    # 缓存统计
    openai_cache = openai_usage.get('input_token_details', {}).get('cache_read', 0)
    anthropic_cache = anthropic_usage.get('input_token_details', {}).get('cache_read', 0)
    print(f"{'Cache read tokens':<20} {openai_cache:<15} {anthropic_cache:<15}")
    
    # 成本估算（简化）
    openai_cost = (openai_usage['input_tokens'] * 0.003 + openai_usage['output_tokens'] * 0.006) / 1000
    anthropic_cost = (anthropic_usage['input_tokens'] * 0.003 + anthropic_usage['output_tokens'] * 0.015) / 1000
    
    print(f"\n{'Estimated Cost':<20} ${openai_cost:<14.6f} ${anthropic_cost:<14.6f}")
    print(f"{'Cost Difference':<20} {(anthropic_cost - openai_cost) / openai_cost * 100:+.1f}%")

# 使用
compare_providers("Explain the theory of relativity in detail")
```

## 6. Leon TokenMonitor 集成示例

```python
from langchain_core.messages import AIMessage
from typing import Optional

class TokenUsageAnalyzer:
    """Token 使用分析工具"""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_creation_tokens = 0
        self.reasoning_tokens = 0
    
    def process_message(self, message: AIMessage) -> None:
        """处理单个消息的 token 使用"""
        if not message.usage_metadata:
            return
        
        usage = message.usage_metadata
        
        # 基础统计
        self.total_input_tokens += usage['input_tokens']
        self.total_output_tokens += usage['output_tokens']
        
        # 详细分项
        input_details = usage.get('input_token_details', {})
        self.cache_read_tokens += input_details.get('cache_read', 0)
        self.cache_creation_tokens += input_details.get('cache_creation', 0)
        
        output_details = usage.get('output_token_details', {})
        self.reasoning_tokens += output_details.get('reasoning', 0)
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'cache_read_tokens': self.cache_read_tokens,
            'cache_creation_tokens': self.cache_creation_tokens,
            'reasoning_tokens': self.reasoning_tokens,
            'cache_efficiency': (
                self.cache_read_tokens / (self.cache_read_tokens + self.cache_creation_tokens)
                if (self.cache_read_tokens + self.cache_creation_tokens) > 0
                else 0
            ),
        }
    
    def print_report(self) -> None:
        """打印统计报告"""
        summary = self.get_summary()
        print("=== Token Usage Report ===")
        print(f"Total input tokens: {summary['total_input_tokens']}")
        print(f"Total output tokens: {summary['total_output_tokens']}")
        print(f"Total tokens: {summary['total_tokens']}")
        print(f"\nCache Statistics:")
        print(f"  Cache read tokens: {summary['cache_read_tokens']}")
        print(f"  Cache creation tokens: {summary['cache_creation_tokens']}")
        print(f"  Cache efficiency: {summary['cache_efficiency']:.1%}")
        print(f"\nReasoning tokens: {summary['reasoning_tokens']}")

# 使用
analyzer = TokenUsageAnalyzer()

# 处理多个消息
for message in messages:
    analyzer.process_message(message)

analyzer.print_report()
```

## 7. 关键差异总结表

| 特性 | OpenAI | Anthropic | LangChain 标准化 |
|------|--------|-----------|-----------------|
| **缓存 token 字段** | `cached_tokens` | `cache_read_input_tokens` | `cache_read` |
| **缓存创建字段** | 无 | `cache_creation_input_tokens` | `cache_creation` |
| **推理 token 字段** | `reasoning_tokens` | 无 | `reasoning` |
| **input_tokens 包含缓存** | ✅ 是 | ❌ 否 | ✅ 是（已规范化） |
| **缓存 TTL 信息** | 无 | `ephemeral_*_input_tokens` | 直接保留 |
| **Service Tier** | `priority_*`, `flex_*` | 无 | 直接保留 |

