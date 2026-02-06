# LangChain Token Usage 研究索引

## 文档导航

### 快速开始
- **新手入门** → 阅读 `LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md`
- **深入理解** → 阅读 `LANGCHAIN_TOKEN_USAGE_RESEARCH.md`
- **实战代码** → 阅读 `LANGCHAIN_TOKEN_USAGE_EXAMPLES.md`
- **研究总结** → 阅读 `LANGCHAIN_TOKEN_USAGE_SUMMARY.md`

### 按场景查找

#### 场景 1: 我想快速了解 token 使用的基本概念
**推荐阅读：** `LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md`
- 核心数据结构
- Provider 差异速查表
- 常见操作代码片段

#### 场景 2: 我想深入理解 LangChain 的 token 规范化机制
**推荐阅读：** `LANGCHAIN_TOKEN_USAGE_RESEARCH.md`
- UsageMetadata 完整结构定义
- ChatOpenAI 的转换逻辑
- ChatAnthropic 的转换逻辑
- 规范化策略分析

#### 场景 3: 我想看具体的代码示例
**推荐阅读：** `LANGCHAIN_TOKEN_USAGE_EXAMPLES.md`
- 基础使用示例
- 流式处理示例
- 缓存统计示例
- 推理 token 示例
- Leon 集成示例

#### 场景 4: 我想了解 OpenAI 和 Anthropic 的差异
**推荐阅读：** `LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md` 的 Provider 差异速查表
或 `LANGCHAIN_TOKEN_USAGE_RESEARCH.md` 的详细对比

#### 场景 5: 我想在 Leon 中实现 TokenMonitor
**推荐阅读：** 
1. `LANGCHAIN_TOKEN_USAGE_SUMMARY.md` 的"对 Leon 的启示"部分
2. `LANGCHAIN_TOKEN_USAGE_EXAMPLES.md` 的"Leon TokenMonitor 集成示例"

#### 场景 6: 我想计算 token 成本
**推荐阅读：** `LANGCHAIN_TOKEN_USAGE_QUICK_REFERENCE.md` 的"成本计算示例"
或 `LANGCHAIN_TOKEN_USAGE_EXAMPLES.md` 的"对比分析工具"

## 关键概念速查

### UsageMetadata 字段
```
input_tokens          → 输入 token 总数
output_tokens         → 输出 token 总数
total_tokens          → 总 token 数
input_token_details   → 输入详细分项（可选）
  ├── audio           → 音频输入 token
  ├── cache_creation  → 缓存创建 token
  ├── cache_read      → 缓存读取 token
  └── ...
output_token_details  → 输出详细分项（可选）
  ├── audio           → 音频输出 token
  ├── reasoning       → 推理 token
  └── ...
```

### Provider 差异
```
OpenAI:
  ✅ 缓存支持（cached_tokens）
  ✅ 推理支持（reasoning_tokens）
  ✅ Service tier 支持
  ✅ input_tokens 包含缓存

Anthropic:
  ✅ 缓存支持（cache_read_input_tokens）
  ✅ 缓存创建支持（cache_creation_input_tokens）
  ✅ 缓存 TTL 支持（ephemeral_*）
  ❌ input_tokens 不包含缓存（需手动加回）
```

## 源码位置速查

| 组件 | 文件 | 行号 |
|------|------|------|
| UsageMetadata | langchain_core/messages/ai.py | 104-158 |
| InputTokenDetails | langchain_core/messages/ai.py | 38-72 |
| OutputTokenDetails | langchain_core/messages/ai.py | 74-102 |
| ChatOpenAI 转换 | langchain_openai/chat_models/base.py | 3623-3708 |
| ChatAnthropic 转换 | langchain_anthropic/chat_models.py | 2082-2122 |
| add_usage 函数 | langchain_core/messages/ai.py | 693-749 |
| subtract_usage 函数 | langchain_core/messages/ai.py | 752-812 |

## 常见问题速查

### Q: 应该使用 usage_metadata 还是 response_metadata？
A: 优先使用 `usage_metadata`，它是标准化的、跨 provider 一致的。
   只在需要 provider 特定信息时才使用 `response_metadata`。

### Q: Anthropic 的 input_tokens 为什么和 response_metadata 中的不一样？
A: Anthropic API 返回的 input_tokens 不包含缓存 token，
   LangChain 在 usage_metadata 中已规范化为包含缓存的总数。

### Q: 如何在流式处理中获取完整的 token 统计？
A: 使用 `add_usage()` 函数合并每个 chunk 的 usage_metadata。

### Q: 推理 token 是什么？
A: OpenAI o1 模型的思维链过程中生成的 token，
   不作为模型输出返回，但计入成本。

### Q: 如何计算缓存节省的成本？
A: 使用 `input_token_details['cache_read']` 乘以缓存 token 的成本率。
   Anthropic 缓存读取成本是普通 token 的 10%。

## 最佳实践清单

- [ ] 优先使用 `usage_metadata` 而不是 `response_metadata`
- [ ] 检查 `usage_metadata` 是否为 None
- [ ] 使用 `get()` 访问可选字段（input_token_details、output_token_details）
- [ ] 流式处理时使用 `add_usage()` 合并 token 统计
- [ ] 支持缓存 token 统计（对成本优化很重要）
- [ ] 支持推理 token 统计（o1 模型的成本计算需要）
- [ ] 处理 Anthropic 的缓存 token 计算差异
- [ ] 支持 OpenAI 的 service tier 和推理 token

## 版本要求

- langchain-core >= 0.3.9
- langchain-openai >= 0.1.0
- langchain-anthropic >= 0.1.0

## 研究时间线

- 2026-02-06: 完成 LangChain token usage 数据结构研究
  - 分析 UsageMetadata 完整结构
  - 研究 ChatOpenAI 的 token 映射逻辑
  - 研究 ChatAnthropic 的 token 映射逻辑
  - 对比 OpenAI 和 Anthropic 的差异
  - 提出 Leon TokenMonitor 实现建议

## 相关资源

### LangChain 官方文档
- [Response metadata](https://python.langchain.com/docs/how_to/response_metadata/)
- [How to track token usage in ChatModels](https://python.langchain.com/docs/how_to/chat_token_usage_tracking/)

### 源码仓库
- [langchain-core](https://github.com/langchain-ai/langchain)
- [langchain-openai](https://github.com/langchain-ai/langchain-openai)
- [langchain-anthropic](https://github.com/langchain-ai/langchain-anthropic)

## 文档维护

本研究文档基于以下版本的源码分析：
- langchain-core: 0.3.9+
- langchain-openai: 最新版本
- langchain-anthropic: 最新版本

如果 LangChain 版本更新，请重新验证文档中的源码位置和 API 签名。

## 联系方式

如有问题或建议，请参考 Leon 项目的贡献指南。
