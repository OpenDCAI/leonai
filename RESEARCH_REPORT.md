# LangChain Token Usage 数据结构研究报告

## 执行摘要

本研究深入分析了 LangChain 的 ChatModel（ChatOpenAI 和 ChatAnthropic）在 response_metadata 中返回的 token usage 数据的完整结构。研究发现 LangChain 已经完全规范化了 token 使用统计，提供了跨 provider 的一致接口。

### 关键发现

1. **LangChain 的两层设计**
   - `usage_metadata`: 标准化的 token 使用统计（TypedDict）
   - `response_metadata`: 原始 provider 响应元数据（Dict）

2. **完整的 token 分项支持**
   - 输入分项：音频、缓存创建、缓存读取、service tier
   - 输出分项：音频、推理、service tier

3. **Provider 差异已妥善处理**
   - OpenAI: 支持缓存、推理、service tier
   - Anthropic: 支持缓存、缓存创建、缓存 TTL

4. **关键差异**
   - OpenAI 的 `prompt_tokens` 包含缓存 token
   - Anthropic 的 `input_tokens` 不包含缓存 token（LangChain 已规范化）

## 研究方法

### 数据来源

1. **LangChain 源码分析**
   - langchain_core/messages/ai.py: UsageMetadata 定义
   - langchain_openai/chat_models/base.py: ChatOpenAI 转换逻辑
   - langchain_anthropic/chat_models.py: ChatAnthropic 转换逻辑

2. **官方文档**
   - LangChain Response metadata 文档
   - LangChain Token usage tracking 文档

3. **实际测试**
   - ChatOpenAI 的 token 使用验证
   - ChatAnthropic 的 token 使用验证

### 分析范围

- langchain-core >= 0.3.9
- langchain-openai 最新版本
- langchain-anthropic 最新版本

## 研究成果

### 文档清单

| 文档 | 行数 | 用途 |
|------|------|------|
| LANGCHAIN_TOKEN_USAGE_RESEARCH.md | 417 | 详细技术研究 |
| LANGCHAIN_TOKEN_USAGE_EXAMPLES.md | 438 | 实战代码示例 |
| LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md | 206 | 快速参考卡片 |
| LANGCHAIN_TOKEN_USAGE_SUMMARY.md | 265 | 研究总结 |
| LANGCHAIN_TOKEN_USAGE_INDEX.md | 161 | 文档导航 |
| **总计** | **1487** | - |

### 核心发现详解

#### 1. UsageMetadata 结构

```python
class UsageMetadata(TypedDict):
    # 必需字段
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # 可选字段
    input_token_details: InputTokenDetails  # 可选
    output_token_details: OutputTokenDetails  # 可选
```

#### 2. InputTokenDetails 字段

- `audio`: 音频输入 token
- `cache_creation`: 缓存创建时消耗的 token
- `cache_read`: 从缓存读取的 token
- `priority_*`, `flex_*`: OpenAI service tier
- `ephemeral_*`: Anthropic 缓存 TTL

#### 3. OutputTokenDetails 字段

- `audio`: 音频输出 token
- `reasoning`: 推理 token（o1 模型）
- `priority_*`, `flex_*`: OpenAI service tier

#### 4. ChatOpenAI 的转换规则

| 源字段 | 目标字段 | 说明 |
|--------|---------|------|
| prompt_tokens | input_tokens | 已包含缓存 |
| completion_tokens | output_tokens | - |
| cached_tokens | cache_read | 缓存命中 |
| reasoning_tokens | reasoning | o1 推理 |
| audio_tokens | audio | 音频 |

#### 5. ChatAnthropic 的转换规则

| 源字段 | 目标字段 | 说明 |
|--------|---------|------|
| input_tokens | 基础输入 | 不包含缓存 |
| cache_read_input_tokens | cache_read | 缓存命中 |
| cache_creation_input_tokens | cache_creation | 缓存创建 |
| output_tokens | output_tokens | - |
| ephemeral_*_input_tokens | 直接保留 | 缓存 TTL |

**关键差异：** Anthropic 的 `input_tokens` 不包含缓存，LangChain 在 `usage_metadata` 中已规范化为包含缓存的总数。

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
from langchain_core.messages.ai import add_usage

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

## 最佳实践

1. **优先使用 `usage_metadata`** - 标准化、跨 provider 一致
2. **检查 None** - 某些情况下 usage_metadata 可能为 None
3. **使用 get() 访问可选字段** - input_token_details 和 output_token_details 是可选的
4. **流式处理用 add_usage()** - 正确合并 token 统计
5. **避免直接访问 response_metadata** - 除非需要 provider 特定的信息
6. **支持缓存统计** - 对成本优化很重要
7. **支持推理 token** - o1 模型的成本计算需要

## 版本要求

- langchain-core >= 0.3.9
- langchain-openai >= 0.1.0
- langchain-anthropic >= 0.1.0

## 源码参考

| 组件 | 文件 | 行号 |
|------|------|------|
| UsageMetadata | langchain_core/messages/ai.py | 104-158 |
| InputTokenDetails | langchain_core/messages/ai.py | 38-72 |
| OutputTokenDetails | langchain_core/messages/ai.py | 74-102 |
| ChatOpenAI 转换 | langchain_openai/chat_models/base.py | 3623-3708 |
| ChatAnthropic 转换 | langchain_anthropic/chat_models.py | 2082-2122 |
| add_usage 函数 | langchain_core/messages/ai.py | 693-749 |
| subtract_usage 函数 | langchain_core/messages/ai.py | 752-812 |

## 结论

LangChain 已经完全规范化了 token 使用统计，提供了跨 provider 的一致接口。通过 `UsageMetadata` 和详细的分项字段，可以精确追踪 token 使用情况，包括缓存、推理等高级特性。Leon 的 TokenMonitor 应该优先使用这些标准化接口，同时处理 provider 之间的差异。

## 后续工作

1. 在 Leon 中实现 TokenMonitor，集成本研究的发现
2. 支持缓存 token 统计和成本优化
3. 支持推理 token 统计（o1 模型）
4. 定期更新文档以跟踪 LangChain 的版本更新

## 附录

### 相关资源

- [LangChain Response metadata](https://python.langchain.com/docs/how_to/response_metadata/)
- [LangChain Token usage tracking](https://python.langchain.com/docs/how_to/chat_token_usage_tracking/)
- [langchain-core GitHub](https://github.com/langchain-ai/langchain)
- [langchain-openai GitHub](https://github.com/langchain-ai/langchain-openai)
- [langchain-anthropic GitHub](https://github.com/langchain-ai/langchain-anthropic)

### 研究时间线

- 2026-02-06: 完成 LangChain token usage 数据结构研究
  - 分析 UsageMetadata 完整结构
  - 研究 ChatOpenAI 的 token 映射逻辑
  - 研究 ChatAnthropic 的 token 映射逻辑
  - 对比 OpenAI 和 Anthropic 的差异
  - 提出 Leon TokenMonitor 实现建议
  - 生成 5 份研究文档（共 1487 行）

---

**研究者：** 邵云（Clawebot/moltbot 技术研究员）
**研究日期：** 2026-02-06
**文档版本：** 1.0
