# LangChain Prompt Caching 研究总结

**研究时间**: 2026-02-07  
**研究员**: 邵云  
**研究范围**: LangChain 1.2.6 + langchain_anthropic 1.3.1 + langchain_openai 1.1.7

---

## 核心发现

### 1. LangChain 的三层缓存体系

```
应用层缓存 (BaseCache)
    ↓ 整个 completion 缓存
中间件层 (AgentMiddleware)
    ↓ Provider 特定标记注入
API 层缓存 (Native Caching)
    ↓ Provider 原生缓存机制
```

### 2. Provider 缓存机制差异

| 特性 | Anthropic | OpenAI | Gemini |
|------|-----------|--------|--------|
| **缓存类型** | 显式 | 自动 | 隐式/显式 |
| **触发方式** | cache_control 标记 | 前缀匹配 | 自动/API |
| **最小长度** | 1024 tokens | 1024 tokens | 1024/4096 tokens |
| **TTL** | 5m/1h | 无限 | 1h |
| **成本折扣** | 90% | 90% | 90% |
| **LangChain 支持** | ✅ 完整 | ⚠️ 自动 | ⚠️ 隐式 |

### 3. Leon 当前状态

**已实现**:
- ✅ Anthropic 缓存（完整支持）
- ✅ TTL 配置（5m/1h）
- ✅ 消息数阈值
- ✅ 模型类型检查

**缺失**:
- ❌ OpenAI 显式控制
- ❌ Gemini 显式控制
- ❌ 缓存统计监控
- ❌ 多 Agent 缓存共享
- ❌ 灵活的消息选择策略

### 4. 与 OpenCode 的对比

**OpenCode 优势**:
- 支持 5 个 provider（Anthropic、OpenAI、Bedrock、OpenRouter、Copilot）
- 灵活的消息选择策略（system + final 2 messages）
- 代码简洁（~40 行，结构清晰）
- 易于扩展

**Leon 优势**:
- 官方 LangChain 支持
- 严格的错误处理
- TTL 可配置
- 与 Leon 架构深度集成

---

## 技术深度分析

### Anthropic 实现细节

**cache_control 注入流程**:

```python
# 1. 中间件层：注入到 model_settings
new_model_settings = {
    **model_settings,
    "cache_control": {"type": "ephemeral", "ttl": "5m"},
}

# 2. ChatAnthropic 层：应用到消息
cache_control = kwargs.pop("cache_control", None)
if cache_control and formatted_messages:
    # 从后向前遍历，找到第一个合法块
    for formatted_message in reversed(formatted_messages):
        for block in reversed(content):
            if not _is_code_execution_related_block(block):
                block["cache_control"] = cache_control
                break

# 3. API 层：Anthropic 识别并缓存
```

**关键限制**:
- 最多 4 个 cache_control 标记
- 不能在 code_execution 块上应用
- TTL 固定为 5m 或 1h

### OpenAI 自动缓存

**工作原理**:
- 自动识别重复前缀
- 前缀长度 ≥ 1024 tokens 时启用
- 无需代码改动
- 通过 response_metadata 获取统计

**获取统计**:
```python
usage = response.response_metadata.get("usage", {})
cache_creation_input_tokens = usage.get("cache_creation_input_tokens", 0)
cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)
```

### Gemini 隐式缓存

**特点**:
- 默认启用
- 自动缓存重复内容
- 支持显式缓存 API（cached_content）
- 最小 token 要求：1024 (2.5 Flash) / 4096 (1.5 Pro)

---

## 成本分析

### 缓存创建成本

```
成本 = tokens × 原价 × 1.25

示例 (Anthropic):
- 10,000 tokens × $3/1M × 1.25 = $0.0375
- 额外成本: 25%
```

### 缓存读取成本

```
成本 = tokens × 原价 × 0.1

示例 (Anthropic):
- 10,000 tokens × $3/1M × 0.1 = $0.003
- 节省: 90%
```

### ROI 计算

```
缓存命中率 = 80%
平均前缀长度 = 10,000 tokens
调用次数 = 100

总成本（无缓存）:
  100 × 10,000 × $3/1M = $3

总成本（有缓存）:
  创建: 1 × 10,000 × $3/1M × 1.25 = $0.0375
  读取: 99 × 10,000 × $3/1M × 0.1 = $0.297
  总计: $0.3345

节省: $3 - $0.3345 = $2.6655 (89% 节省)
```

---

## 实现建议

### 短期 (P1) - 2 周

**目标**: 支持 OpenAI 和 Gemini

```python
class MultiProviderPromptCachingMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        provider = self._detect_provider(request.model)
        
        if provider == "anthropic":
            return self._handle_anthropic(request, handler)
        elif provider == "openai":
            # 自动缓存，无需处理
            return handler(request)
        elif provider == "gemini":
            # 隐式缓存，无需处理
            return handler(request)
        
        return handler(request)
```

**工作量**: ~6 小时

### 中期 (P2) - 4 周

**目标**: 缓存统计和灵活策略

```python
class CacheMonitor(BaseMonitor):
    def get_hit_rate(self) -> float:
        return self.cache_hits / self.total_requests
    
    def get_cost_savings(self) -> dict:
        # 计算成本节省
        pass

class CachingStrategy:
    def select_cacheable_messages(self, messages):
        # 灵活的消息选择
        pass
```

**工作量**: ~10 小时

### 长期 (P3) - 8 周+

**目标**: 多 Agent 缓存共享和社区贡献

```python
class SharedCacheMiddleware:
    def __init__(self, backend: SharedCacheBackend):
        self.backend = backend
    
    def wrap_model_call(self, request, handler):
        # 多 Agent 间的缓存共享
        pass
```

**工作量**: ~12 小时

---

## 最佳实践

### 1. 消息组织

```python
# ✅ 好的做法：静态内容在前
messages = [
    SystemMessage(content="System prompt..."),  # 缓存
    SystemMessage(content="Tools..."),          # 缓存
    HumanMessage(content="Question 1"),         # 变化
    AIMessage(content="Answer 1"),
    HumanMessage(content="Question 2"),         # 变化
]
```

### 2. 缓存粒度

```python
# ✅ 推荐：缓存 system + 最后 2 条消息
cacheable = system_messages + messages[-2:]

# ❌ 不推荐：缓存整个历史
cacheable = all_messages
```

### 3. TTL 选择

```python
# 5 分钟：开发测试
PromptCachingMiddleware(ttl="5m")

# 1 小时：生产环境
PromptCachingMiddleware(ttl="1h")
```

---

## 总结

### 核心洞察

1. **LangChain 的缓存体系完整但不统一**: 各 provider 差异大，需要自定义中间件
2. **Anthropic 实现最完善**: 显式 cache_control，LangChain 有完整支持
3. **OpenAI 和 Gemini 自动缓存**: 无需显式配置，但无法精细控制
4. **Leon 仅支持 Anthropic**: 需要扩展以支持其他 provider
5. **成本节省潜力巨大**: 缓存命中时可节省 80-90% 成本

### 建议行动

1. **立即** (P1): 在 Leon 中添加 OpenAI 和 Gemini 支持
2. **短期** (P2): 实现缓存统计和灵活策略
3. **中期** (P3): 支持多 Agent 缓存共享
4. **长期**: 向 LangChain 社区贡献统一缓存抽象

### 预期收益

- **成本**: 缓存命中时节省 80-90%
- **性能**: 缓存读取延迟降低 50-80%
- **用户体验**: 更快的响应时间
- **可维护性**: 统一的缓存接口

