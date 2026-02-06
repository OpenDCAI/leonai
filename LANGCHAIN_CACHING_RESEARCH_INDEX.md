# LangChain Prompt Caching 研究索引

**研究时间**: 2026-02-07  
**研究员**: 邵云  
**研究范围**: LangChain 1.2.6 + langchain_anthropic 1.3.1 + langchain_openai 1.1.7

---

## 研究成果

本研究深入分析了 LangChain 框架的 Prompt Caching 实现，包括：

1. **架构分析**: LangChain 的三层缓存体系
2. **Provider 对比**: Anthropic、OpenAI、Gemini 的缓存机制差异
3. **Leon 现状**: 当前实现的能力和局限
4. **OpenCode 对比**: 与 OpenCode 实现的对比分析
5. **实现建议**: P1/P2/P3 的详细实施路线图
6. **最佳实践**: 消息组织、缓存粒度、TTL 选择等

---

## 核心发现速查

### 三层缓存体系

```
应用层缓存 (BaseCache)
    ↓ 整个 completion 缓存
中间件层 (AgentMiddleware)
    ↓ Provider 特定标记注入
API 层缓存 (Native Caching)
    ↓ Provider 原生缓存机制
```

### Provider 对比表

| 特性 | Anthropic | OpenAI | Gemini |
|------|-----------|--------|--------|
| **缓存类型** | 显式 | 自动 | 隐式/显式 |
| **触发方式** | cache_control 标记 | 前缀匹配 | 自动/API |
| **最小长度** | 1024 tokens | 1024 tokens | 1024/4096 tokens |
| **TTL** | 5m/1h | 无限 | 1h |
| **成本折扣** | 90% | 90% | 90% |
| **LangChain 支持** | ✅ 完整 | ⚠️ 自动 | ⚠️ 隐式 |

### Leon 能力矩阵

```
✅ Anthropic 缓存
   ├─ cache_control 标记注入
   ├─ TTL 配置 (5m/1h)
   └─ 消息数阈值

❌ OpenAI 缓存
   ├─ 自动缓存（无需配置）
   └─ 无显式控制

❌ Gemini 缓存
   ├─ 隐式缓存（无需配置）
   └─ 无显式控制

❌ 缓存统计
   ├─ 无监控
   └─ 无指标收集

❌ 多 Agent 缓存
   ├─ 无共享机制
   └─ 无协调策略
```

---

## 关键代码位置

### Leon 项目

| 文件 | 功能 |
|------|------|
| `middleware/prompt_caching.py` | PromptCachingMiddleware 实现 |
| `agent.py` (行 ~200) | 中间件集成 |
| `middleware/task/subagent.py` | SubAgent 初始化 |

### LangChain 源代码

| 文件 | 行号 | 功能 |
|------|------|------|
| `langchain_anthropic/chat_models.py` | 1070-1107 | cache_control 应用逻辑 |
| `langchain_anthropic/middleware/prompt_caching.py` | - | AnthropicPromptCachingMiddleware |
| `langchain.chat_models` | - | init_chat_model 统一初始化 |

### OpenCode 参考

| 文件 | 行号 | 功能 |
|------|------|------|
| `provider/transform.ts` | 171-209 | applyCaching 函数 |

---

## 成本分析

### 缓存创建成本

```
成本 = tokens × 原价 × 1.25 (25% 溢价)

示例 (Anthropic):
- 10,000 tokens × $3/1M × 1.25 = $0.0375
```

### 缓存读取成本

```
成本 = tokens × 原价 × 0.1 (90% 折扣)

示例 (Anthropic):
- 10,000 tokens × $3/1M × 0.1 = $0.003
```

### ROI 示例

```
缓存命中率: 80%
平均前缀长度: 10,000 tokens
调用次数: 100

无缓存成本: $3
有缓存成本: $0.3345
节省: $2.6655 (89% 节省)
```

---

## 实现路线图

### P1 (Week 1) - 基础支持扩展

**目标**: 支持 OpenAI 和 Gemini

**工作量**: 6 小时

**交付物**:
- MultiProviderPromptCachingMiddleware
- CacheMonitor
- 单元测试

### P2 (Week 2-3) - 高级功能

**目标**: 缓存策略优化和多 Agent 协调

**工作量**: 10 小时

**交付物**:
- CachingStrategy 抽象
- SharedCacheMiddleware
- 集成测试

### P3 (Week 4+) - 社区贡献

**目标**: 向 LangChain 社区贡献改进

**工作量**: 12 小时

**交付物**:
- LangChain PR
- leon-prompt-caching 扩展包

---

## 最佳实践

### 消息组织

```python
# ✅ 好的做法：静态内容在前
messages = [
    SystemMessage(content="System prompt..."),  # 缓存
    SystemMessage(content="Tools..."),          # 缓存
    HumanMessage(content="Question 1"),         # 变化
    AIMessage(content="Answer 1"),
    HumanMessage(content="Question 2"),         # 变化
]

# ❌ 不好的做法：变化内容在前
messages = [
    HumanMessage(content="Question 1"),  # 变化，难以缓存
    SystemMessage(content="System..."),
]
```

### 缓存粒度

```python
# ✅ 推荐：缓存 system + 最后 2 条消息
cacheable = system_messages + messages[-2:]

# ❌ 不推荐：缓存整个历史
cacheable = all_messages  # 缓存命中率低
```

### TTL 选择

```python
# 5 分钟：开发测试
PromptCachingMiddleware(ttl="5m")

# 1 小时：生产环境
PromptCachingMiddleware(ttl="1h")
```

---

## 常见问题

### Q: 为什么 OpenAI 没有缓存命中？
A: 检查：
1. 前缀长度是否 ≥ 1024 tokens
2. 前缀是否完全相同（包括空格）
3. 是否在同一 API key 下
4. 是否使用同一模型

### Q: Anthropic 缓存为什么没有生效？
A: 检查：
1. 是否使用了 ChatAnthropic 模型
2. cache_control 是否正确注入
3. 消息数是否满足 min_messages_to_cache
4. 是否在 TTL 内

### Q: 如何在多 Agent 间共享缓存？
A: 当前 LangChain 不支持，需要：
1. 使用相同的 API key
2. 使用相同的模型
3. 确保消息前缀相同
4. 在 TTL 内调用

---

## 参考资源

### 官方文档
- [Anthropic Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching)
- [Google Gemini Context Caching](https://ai.google.dev/gemini-api/docs/caching)
- [LangChain Anthropic Integration](https://python.langchain.com/docs/integrations/chat/anthropic/)

### 本地资源
- Leon 项目: `/Users/apple/Desktop/project/v1/文稿/project/leon/`
- 研究文档: `LANGCHAIN_CACHING_RESEARCH_SUMMARY.md`

---

## 总结

### 核心洞察

1. **LangChain 的缓存体系完整但不统一**: 各 provider 差异大
2. **Anthropic 实现最完善**: 显式 cache_control，LangChain 完整支持
3. **OpenAI 和 Gemini 自动缓存**: 无需显式配置
4. **Leon 仅支持 Anthropic**: 需要扩展
5. **成本节省潜力巨大**: 缓存命中时可节省 80-90%

### 建议行动

1. **立即** (P1): 添加 OpenAI 和 Gemini 支持
2. **短期** (P2): 实现缓存统计和灵活策略
3. **中期** (P3): 支持多 Agent 缓存共享
4. **长期**: 向 LangChain 社区贡献改进

### 预期收益

- **成本**: 缓存命中时节省 80-90%
- **性能**: 缓存读取延迟降低 50-80%
- **用户体验**: 更快的响应时间
- **可维护性**: 统一的缓存接口

