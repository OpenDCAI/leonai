# OpenCode Prompt Caching 研究总结

**研究时间**: 2026-02-07  
**研究员**: 邵云  
**项目**: OpenCode (TypeScript/Node.js)  
**文档**: 完整技术分析 + 代码示例

---

## 核心发现

### 1. 架构设计

OpenCode 采用**分层缓存架构**：

```
消息输入 (llm.ts)
    ↓
消息规范化 (transform.ts)
    ├─ normalizeMessages()      # 模型特定规范化
    ├─ applyCaching()           # 缓存标记注入
    └─ unsupportedParts()       # 内容过滤
    ↓
模型选项配置 (transform.ts)
    └─ options()                # promptCacheKey 设置
    ↓
API 调用 (ai SDK)
    └─ streamText()
    ↓
响应解析 (anthropic.ts, openai.ts)
    ├─ 缓存使用统计提取
    └─ 成本计算
```

**关键特点**：
- 缓存逻辑集中在 ProviderTransform 层
- 支持 5 种 provider 的缓存（Anthropic、OpenAI、Bedrock、OpenRouter、Copilot）
- 成本模型内置缓存读写价格
- 自动缓存标记放置，无需手动干预

---

## 2. 多模型缓存差异

### Anthropic (显式缓存)

```typescript
// 在消息上放置 cache_control
msg.providerOptions = {
  anthropic: {
    cacheControl: { type: "ephemeral" }
  }
}

// 缓存类型: ephemeral (5m/1h)
// 成本: 写入 1.25x input, 读取 0.1x input
```

**Breakpoint 位置**：
- 前 2 个 system 消息
- 最后 2 个消息

### OpenAI (隐式缓存)

```typescript
// 在模型级别设置缓存键
result["promptCacheKey"] = input.sessionID

// 缓存自动应用于:
// - 所有 system 消息
// - 前面的 user/assistant 消息
// - 最后一条消息自动排除
```

**无需显式 breakpoint**：OpenAI 自动处理

### 成本对比

| 操作 | Anthropic | OpenAI |
|------|-----------|--------|
| 缓存写入 | 1.25x input | 无 |
| 缓存读取 | 0.1x input | 0.1x input |
| 配置方式 | 消息级 | 模型级 |
| TTL | 5m/1h | 无限制 |

---

## 3. 缓存标记放置策略

### 关键代码 (transform.ts L171-209)

```typescript
function applyCaching(msgs: ModelMessage[], providerID: string): ModelMessage[] {
  // 只在前 2 个 system + 最后 2 个消息上放置标记
  const system = msgs.filter((msg) => msg.role === "system").slice(0, 2)
  const final = msgs.filter((msg) => msg.role !== "system").slice(-2)

  const providerOptions = {
    anthropic: { cacheControl: { type: "ephemeral" } },
    openrouter: { cacheControl: { type: "ephemeral" } },
    bedrock: { cachePoint: { type: "default" } },
    openaiCompatible: { cache_control: { type: "ephemeral" } },
    copilot: { copilot_cache_control: { type: "ephemeral" } },
  }

  for (const msg of unique([...system, ...final])) {
    // Anthropic/Bedrock: 消息级别
    // OpenAI/OpenRouter: 内容级别
    msg.providerOptions = mergeDeep(msg.providerOptions ?? {}, providerOptions)
  }

  return msgs
}
```

**为什么只在前 2 个 + 最后 2 个？**
- 保护系统提示（缓存稳定性）
- 保护最近对话（缓存命中率）
- 减少缓存标记数量（成本优化）

---

## 4. OpenAI 的 promptCacheKey 机制

### 关键代码 (transform.ts L620-622)

```typescript
if (input.model.providerID === "openai" || input.providerOptions?.setCacheKey) {
  result["promptCacheKey"] = input.sessionID
}
```

**工作原理**：
1. 设置 `promptCacheKey` = sessionID
2. OpenAI 自动识别相同 sessionID 的请求
3. 自动应用缓存到 system 消息 + 前面的消息
4. 最后一条消息（通常是用户输入）不被缓存

**与 Anthropic 的区别**：
- Anthropic: 需要显式标记每条消息
- OpenAI: 只需设置一个 sessionID，自动处理

---

## 5. 缓存成本模型

### 模型定义 (models.ts)

```typescript
const model = {
  cost: {
    input: 0.003,           // 基础输入成本
    output: 0.015,          // 基础输出成本
    cache_read: 0.0003,     // 缓存读取成本 (90% 折扣)
    cache_write: 0.00375,   // 缓存写入成本 (25% 溢价)
  }
}
```

### 成本计算示例

**第一次请求** (缓存写入):
```
1000 input tokens + 500 output tokens
= 1000 * 0.003 + 500 * 0.015 + 1000 * 0.00375
= $0.003 + $0.0075 + $0.00375
= $0.01425
```

**第二次请求** (缓存命中):
```
100 input tokens + 500 output tokens + 1000 cached tokens
= 100 * 0.003 + 500 * 0.015 + 1000 * 0.0003
= $0.0003 + $0.0075 + $0.0003
= $0.0081 (节省 43%)
```

---

## 6. 缓存使用统计追踪

### Anthropic 统计 (anthropic.ts L5-17)

```typescript
type Usage = {
  cache_creation?: {
    ephemeral_5m_input_tokens?: number
    ephemeral_1h_input_tokens?: number
  }
  cache_creation_input_tokens?: number
  cache_read_input_tokens?: number
  input_tokens?: number
  output_tokens?: number
}
```

### OpenAI 统计 (openai.ts L3-13)

```typescript
type Usage = {
  input_tokens?: number
  input_tokens_details?: {
    cached_tokens?: number
  }
  output_tokens?: number
}
```

### 统计规范化

两种 provider 都规范化为统一格式：
```typescript
{
  inputTokens: number
  outputTokens: number
  cacheReadTokens?: number
  cacheWrite5mTokens?: number
  cacheWrite1hTokens?: number
}
```

---

## 7. 不支持缓存的 Provider 降级

### 检测机制

```typescript
const providerOptions = {
  anthropic: { ... },
  openrouter: { ... },
  bedrock: { ... },
  openaiCompatible: { ... },
  copilot: { ... },
  // Google、Mistral 等不在此列表中
}
```

### 降级行为

1. **静默跳过**: 不添加任何缓存标记
2. **无错误**: 消息正常发送
3. **成本计算**: 使用标准 input/output 成本

**不支持的 provider**：
- Google Gemini
- Mistral
- 其他未在 providerOptions 中定义的 provider

---

## 8. 消息结构优化

### 系统提示维持 2 部分结构 (llm.ts L82-97)

```typescript
// 维持 2 部分结构以支持缓存
const header = system[0]
const original = clone(system)

await Plugin.trigger("experimental.chat.system.transform", ...)

if (system.length === 0) {
  system.push(...original)
}

// 如果 header 未变，重新组织为 2 部分结构
if (system.length > 2 && system[0] === header) {
  const rest = system.slice(1)
  system.length = 0
  system.push(header, rest.join("\n"))
}
```

**目的**：
- 保持系统提示稳定性
- 支持缓存 breakpoint 正确放置
- 避免频繁缓存失效

---

## 9. 关键文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `/packages/opencode/src/provider/transform.ts` | 171-209 | 缓存标记注入 (applyCaching) |
| `/packages/opencode/src/provider/transform.ts` | 620-670 | 模型级缓存配置 (options) |
| `/packages/opencode/src/session/llm.ts` | 82-97 | 系统提示结构优化 |
| `/packages/opencode/src/provider/models.ts` | 36-50 | 缓存成本定义 |
| `/packages/opencode/src/provider/provider.ts` | 570-587 | 模型元数据 + 成本计算 |
| `/packages/console/app/src/routes/zen/util/provider/anthropic.ts` | 139-180 | Anthropic 缓存解析 |
| `/packages/console/app/src/routes/zen/util/provider/openai.ts` | 3-62 | OpenAI 缓存解析 |
| `/packages/opencode/src/session/message.ts` | 170-180 | 缓存统计存储 |
| `/packages/opencode/test/provider/transform.test.ts` | 6-1327 | 缓存测试用例 |

---

## 10. 与 Leon 的对比

### 架构对比

| 维度 | OpenCode | Leon |
|------|----------|------|
| 缓存实现 | 分散在 provider 层 | 集中在 middleware 层 |
| 配置方式 | 模型级 + 消息级 | 中间件配置 |
| 多模型支持 | provider-specific | 统一接口 |
| 成本追踪 | 消息元数据 | Monitor middleware |
| 降级策略 | 静默跳过 | 可配置 |

### 可借鉴的设计

1. **分层抽象**: 缓存逻辑集中在一个层
2. **Provider 差异处理**: 通过 provider-specific 配置
3. **成本透明**: 缓存成本在模型定义中明确
4. **自动管理**: 缓存标记自动放置
5. **统计规范化**: 不同 provider 的统计统一格式

---

## 11. 实现建议

### 对于 Leon 的参考

1. **创建 PromptCachingMiddleware**
   - 集中处理缓存标记注入
   - 支持 provider-specific 配置
   - 自动检测 provider 能力

2. **成本模型集成**
   - 在 TokenMonitor 中追踪缓存成本
   - 支持缓存读写成本分别计算
   - 提供缓存效率报告

3. **消息结构优化**
   - 维持系统提示稳定性
   - 自动优化 breakpoint 位置
   - 支持缓存失效检测

4. **降级策略**
   - 不支持的 provider 静默跳过
   - 提供配置选项启用/禁用缓存
   - 记录缓存相关的日志

---

## 12. 常见问题解答

### Q: 为什么 Anthropic 需要显式标记，OpenAI 不需要？

**A**: 这是两个 API 的设计差异：
- Anthropic: 需要在每条消息上显式标记 `cache_control`
- OpenAI: 通过 `promptCacheKey` 自动识别和缓存

### Q: 缓存写入成本为什么比输入成本高？

**A**: Anthropic 的定价策略：
- 缓存写入需要额外的处理成本（1.25x input）
- 缓存读取成本极低（0.1x input）
- 长期来看，多次读取会抵消写入成本

### Q: 如何确保缓存命中？

**A**: 
1. 保持系统提示不变
2. 保持消息顺序不变
3. 使用相同的 sessionID (OpenAI) 或 cache_control (Anthropic)
4. 在 TTL 内重复使用 (Anthropic: 5m/1h)

### Q: 缓存大小有限制吗？

**A**: 缓存大小受上下文窗口限制：
- Claude 3.5 Sonnet: 200K tokens
- GPT-4: 128K tokens
- 缓存内容不能超过上下文限制

---

## 13. 研究成果

### 文档清单

1. **OPENCODE_PROMPT_CACHING_ANALYSIS.md** (10 章)
   - 完整的架构分析
   - 核心实现细节
   - 多模型缓存差异
   - 缓存策略配置
   - 不支持模型降级
   - 实现对比
   - 关键代码路径
   - 测试覆盖
   - 配置最佳实践
   - 已知限制

2. **OPENCODE_CACHING_CODE_EXAMPLES.md** (8 章)
   - 完整消息处理流程
   - Anthropic 缓存实现
   - OpenAI 缓存实现
   - 成本计算示例
   - 测试用例
   - 实际使用场景
   - 调试技巧
   - 常见问题

3. **OPENCODE_CACHING_SUMMARY.md** (本文档)
   - 核心发现总结
   - 快速参考

### 关键代码片段

- applyCaching() 函数 (L171-209)
- options() 函数 (L620-670)
- 系统提示优化 (L82-97)
- Anthropic 缓存解析 (L139-180)
- OpenAI 缓存解析 (L3-62)

---

## 14. 后续研究方向

1. **缓存效率分析**
   - 不同场景下的缓存命中率
   - 成本节省的实际数据

2. **多 Agent 缓存协调**
   - 跨 Agent 的缓存共享
   - 缓存键的统一管理

3. **缓存失效检测**
   - 自动检测缓存失效原因
   - 提供缓存优化建议

4. **Provider 扩展**
   - 添加 Google Gemini 缓存支持
   - 添加 Mistral 缓存支持

---

**研究完成时间**: 2026-02-07  
**文档位置**: `/Users/apple/Desktop/project/v1/文稿/project/leon/`

