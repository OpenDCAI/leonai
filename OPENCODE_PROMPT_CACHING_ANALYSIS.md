# OpenCode Prompt Caching 实现技术分析

**研究时间**: 2026-02-07  
**研究员**: 邵云  
**项目**: OpenCode (TypeScript/Node.js)  
**重点**: Prompt Caching 架构、多模型支持、缓存策略

---

## 1. 架构概览

OpenCode 的 Prompt Caching 实现采用**分层设计**：

```
LLM 层 (llm.ts)
    ↓
ProviderTransform 层 (transform.ts)
    ├─ applyCaching() → 消息级缓存标记
    ├─ options() → 模型级缓存配置
    └─ message() → 消息转换 + 缓存控制注入
    ↓
Provider 层 (provider.ts, anthropic.ts, openai.ts)
    ├─ 模型成本定义 (cache_read, cache_write)
    ├─ 缓存使用统计 (cache_creation_input_tokens, cache_read_input_tokens)
    └─ 缓存响应解析
    ↓
AI SDK (ai 库)
    └─ 底层 API 调用
```

**关键特点**：
- 缓存控制在 **ProviderTransform** 层统一处理
- 支持多种缓存类型：Anthropic ephemeral、OpenAI prompt cache、Bedrock cachePoint
- 成本模型内置缓存读写价格
- 缓存使用情况通过 response metadata 追踪

---

## 2. 核心实现细节

### 2.1 缓存控制标记放置 (applyCaching)

**文件**: `/packages/opencode/src/provider/transform.ts` (L171-209)

```typescript
function applyCaching(msgs: ModelMessage[], providerID: string): ModelMessage[] {
  const system = msgs.filter((msg) => msg.role === "system").slice(0, 2)
  const final = msgs.filter((msg) => msg.role !== "system").slice(-2)

  const providerOptions = {
    anthropic: {
      cacheControl: { type: "ephemeral" },
    },
    openrouter: {
      cacheControl: { type: "ephemeral" },
    },
    bedrock: {
      cachePoint: { type: "default" },
    },
    openaiCompatible: {
      cache_control: { type: "ephemeral" },
    },
    copilot: {
      copilot_cache_control: { type: "ephemeral" },
    },
  }

  // 在前 2 个 system 消息 + 最后 2 个消息上放置缓存标记
  for (const msg of unique([...system, ...final])) {
    const useMessageLevelOptions = providerID === "anthropic" || providerID.includes("bedrock")
    const shouldUseContentOptions = !useMessageLevelOptions && Array.isArray(msg.content) && msg.content.length > 0

    if (shouldUseContentOptions) {
      // 对于 OpenAI 等，在最后一个 content part 上放置缓存标记
      const lastContent = msg.content[msg.content.length - 1]
      if (lastContent && typeof lastContent === "object") {
        lastContent.providerOptions = mergeDeep(lastContent.providerOptions ?? {}, providerOptions)
        continue
      }
    }

    // 对于 Anthropic/Bedrock，在消息级别放置缓存标记
    msg.providerOptions = mergeDeep(msg.providerOptions ?? {}, providerOptions)
  }

  return msgs
}
```

**缓存标记放置策略**：
- **Anthropic/Bedrock**: 消息级别 (`msg.providerOptions`)
- **OpenAI/OpenRouter**: 内容级别 (`msg.content[].providerOptions`)
- **Copilot**: 消息级别 (特殊字段)

**Breakpoint 位置**：
- 前 2 个 system 消息
- 最后 2 个消息（user/assistant）
- 目的：保护系统提示和最近的对话上下文

---

### 2.2 OpenAI 的 promptCacheKey 配置

**文件**: `/packages/opencode/src/provider/transform.ts` (L620-670)

```typescript
export function options(input: {
  model: Provider.Model
  sessionID: string
  providerOptions?: Record<string, unknown>
}): Record<string, any> {
  const result: Record<string, any> = {}

  // OpenAI 自动启用缓存
  if (input.model.providerID === "openai" || input.providerOptions?.setCacheKey) {
    result["promptCacheKey"] = input.sessionID
  }

  // GPT-5 系列特殊处理
  if (input.model.api.id.includes("gpt-5")) {
    if (input.model.providerID.startsWith("opencode")) {
      result["promptCacheKey"] = input.sessionID
      result["include"] = ["reasoning.encrypted_content"]
      result["reasoningSummary"] = "auto"
    }
  }

  // Venice 模型
  if (input.model.providerID === "venice") {
    result["promptCacheKey"] = input.sessionID
  }

  return result
}
```

**OpenAI 缓存机制**：
- 使用 `promptCacheKey` 作为缓存键（通常是 sessionID）
- **不需要显式标记** breakpoint（OpenAI 自动处理）
- 缓存自动应用于：
  - 系统消息
  - 前面的用户消息
  - 前面的助手消息
- 最后一条消息（通常是用户输入）**不被缓存**

**与 Anthropic 的区别**：
| 特性 | Anthropic | OpenAI |
|------|-----------|--------|
| 缓存标记 | 显式 `cache_control` | 隐式 `promptCacheKey` |
| Breakpoint 位置 | 手动指定 | 自动（最后一条消息前） |
| 缓存类型 | ephemeral (5m/1h) | 自动 |
| 配置方式 | 消息级别 | 模型级别 |

---

### 2.3 多模型缓存差异处理

**文件**: `/packages/opencode/src/provider/transform.ts` (L171-209)

```typescript
// 不同 provider 的缓存字段名称
const providerOptions = {
  anthropic: {
    cacheControl: { type: "ephemeral" },  // Anthropic API
  },
  openrouter: {
    cacheControl: { type: "ephemeral" },  // OpenRouter 代理 Anthropic
  },
  bedrock: {
    cachePoint: { type: "default" },      // AWS Bedrock
  },
  openaiCompatible: {
    cache_control: { type: "ephemeral" }, // OpenAI 兼容 API
  },
  copilot: {
    copilot_cache_control: { type: "ephemeral" }, // GitHub Copilot
  },
}
```

**缓存配置矩阵**：

| Provider | 字段名 | 类型 | 位置 | 支持 |
|----------|--------|------|------|------|
| Anthropic | `cacheControl` | `{ type: "ephemeral" }` | 消息级 | ✅ |
| OpenAI | `promptCacheKey` | sessionID | 模型级 | ✅ |
| Bedrock | `cachePoint` | `{ type: "default" }` | 消息级 | ✅ |
| OpenRouter | `cacheControl` | `{ type: "ephemeral" }` | 内容级 | ✅ |
| Copilot | `copilot_cache_control` | `{ type: "ephemeral" }` | 消息级 | ✅ |
| Google | 无 | - | - | ❌ |
| Mistral | 无 | - | - | ❌ |

---

### 2.4 缓存成本模型

**文件**: `/packages/opencode/src/provider/models.ts` (L36-50)

```typescript
export const Model = z.object({
  cost: z.object({
    input: z.number(),
    output: z.number(),
    cache_read: z.number().optional(),      // 缓存读取成本
    cache_write: z.number().optional(),     // 缓存写入成本
    context_over_200k: z.object({
      input: z.number(),
      output: z.number(),
      cache_read: z.number().optional(),
      cache_write: z.number().optional(),
    }).optional(),
  }).optional(),
})
```

**文件**: `/packages/opencode/src/provider/provider.ts` (L570-587)

```typescript
export const Model = z.object({
  cost: z.object({
    input: z.number(),
    output: z.number(),
    cache: z.object({
      read: z.number(),
      write: z.number(),
    }),
    experimentalOver200K: z.object({
      input: z.number(),
      output: z.number(),
      cache: z.object({
        read: z.number(),
        write: z.number(),
      }),
    }).optional(),
  }),
})
```

**成本计算示例** (Claude 3.5 Sonnet):
```
input: $0.003 / 1K tokens
output: $0.015 / 1K tokens
cache.read: $0.0003 / 1K tokens    (比 input 便宜 90%)
cache.write: $0.00375 / 1K tokens  (比 input 贵 25%)
```

**成本转换逻辑** (L619-649):
```typescript
function fromModelsDevModel(provider: ModelsDev.Provider, model: ModelsDev.Model): Model {
  return {
    cost: {
      input: model.cost?.input ?? 0,
      output: model.cost?.output ?? 0,
      cache: {
        read: model.cost?.cache_read ?? 0,
        write: model.cost?.cache_write ?? 0,
      },
      experimentalOver200K: model.cost?.context_over_200k ? {
        cache: {
          read: model.cost.context_over_200k.cache_read ?? 0,
          write: model.cost.context_over_200k.cache_write ?? 0,
        },
        input: model.cost.context_over_200k.input,
        output: model.cost.context_over_200k.output,
      } : undefined,
    },
  }
}
```

---

### 2.5 缓存使用统计追踪

**文件**: `/packages/opencode/src/session/message.ts` (L170-180)

```typescript
export const Info = z.object({
  metadata: z.object({
    usage: z.object({
      tokens: z.object({
        input: z.number(),
        output: z.number(),
        reasoning: z.number(),
        cache: z.object({
          read: z.number(),
          write: z.number(),
        }),
      }),
    }).optional(),
  }).optional(),
})
```

**Anthropic 缓存统计** (anthropic.ts L5-17):
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

**统计规范化** (anthropic.ts L172-179):
```typescript
normalizeUsage: (usage: Usage) => ({
  inputTokens: usage.input_tokens ?? 0,
  outputTokens: usage.output_tokens ?? 0,
  reasoningTokens: undefined,
  cacheReadTokens: usage.cache_read_input_tokens ?? undefined,
  cacheWrite5mTokens: usage.cache_creation?.ephemeral_5m_input_tokens ?? undefined,
  cacheWrite1hTokens: usage.cache_creation?.ephemeral_1h_input_tokens ?? undefined,
})
```

**OpenAI 缓存统计** (openai.ts L3-13):
```typescript
type Usage = {
  input_tokens?: number
  input_tokens_details?: {
    cached_tokens?: number  // 缓存读取的 tokens
  }
  output_tokens?: number
}
```

**统计规范化** (openai.ts L48-61):
```typescript
normalizeUsage: (usage: Usage) => {
  const inputTokens = usage.input_tokens ?? 0
  const cacheReadTokens = usage.input_tokens_details?.cached_tokens ?? undefined
  return {
    inputTokens: inputTokens - (cacheReadTokens ?? 0),  // 扣除缓存读取
    outputTokens: outputTokens,
    cacheReadTokens,
    cacheWrite5mTokens: undefined,
    cacheWrite1hTokens: undefined,
  }
}
```

---

## 3. 缓存策略配置

### 3.1 消息结构优化

**文件**: `/packages/opencode/src/session/llm.ts` (L82-97)

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
- 保持系统提示的稳定性
- 支持缓存 breakpoint 的正确放置
- 避免频繁的缓存失效

### 3.2 缓存启用条件

**文件**: `/packages/opencode/test/provider/transform.test.ts` (L41-85)

```typescript
// 测试用例展示缓存启用逻辑

// 1. OpenAI 自动启用
test("should set promptCacheKey for openai provider regardless of setCacheKey", () => {
  const openaiModel = { providerID: "openai", ... }
  const result = ProviderTransform.options({ model: openaiModel, sessionID, providerOptions: {} })
  expect(result.promptCacheKey).toBe(sessionID)
})

// 2. 其他 provider 需要显式启用
test("should set promptCacheKey when providerOptions.setCacheKey is true", () => {
  const result = ProviderTransform.options({
    model: mockModel,
    sessionID,
    providerOptions: { setCacheKey: true },
  })
  expect(result.promptCacheKey).toBe(sessionID)
})

// 3. Bedrock 自动添加 cachePoint
test("adds cachePoint", () => {
  const model = { providerID: "amazon-bedrock", ... }
  const result = ProviderTransform.message(msgs, model, {})
  expect(result[0].providerOptions?.bedrock).toEqual(
    expect.objectContaining({
      cachePoint: { type: "default" },
    })
  )
})
```

---

## 4. 不支持缓存的模型降级策略

### 4.1 检测机制

**文件**: `/packages/opencode/src/provider/transform.ts` (L171-209)

```typescript
function applyCaching(msgs: ModelMessage[], providerID: string): ModelMessage[] {
  const providerOptions = {
    anthropic: { cacheControl: { type: "ephemeral" } },
    openrouter: { cacheControl: { type: "ephemeral" } },
    bedrock: { cachePoint: { type: "default" } },
    openaiCompatible: { cache_control: { type: "ephemeral" } },
    copilot: { copilot_cache_control: { type: "ephemeral" } },
    // Google、Mistral 等不在此列表中 → 不添加缓存标记
  }

  // 只有在 providerOptions 中有定义的 provider 才会添加缓存标记
  for (const msg of unique([...system, ...final])) {
    // ...
  }
}
```

### 4.2 降级行为

**不支持缓存的 provider**：
- Google (Gemini)
- Mistral
- 其他未在 `providerOptions` 中定义的 provider

**降级策略**：
1. **静默跳过**: 不添加任何缓存标记
2. **无错误**: 消息正常发送，只是没有缓存优化
3. **成本计算**: 使用标准 input/output 成本，不计算缓存成本

---

## 5. 实现对比：Anthropic vs OpenAI

### 5.1 Anthropic 缓存实现

**显式缓存标记**：
```typescript
// 在消息上放置 cache_control
msg.providerOptions = {
  anthropic: {
    cacheControl: { type: "ephemeral" }
  }
}
```

**缓存类型**：
- `ephemeral`: 5 分钟或 1 小时缓存
- 需要在 API 请求中显式指定

**成本结构**：
```
cache_creation_input_tokens: 写入成本 (1.25x input)
cache_read_input_tokens: 读取成本 (0.1x input)
```

**Bedrock 特殊处理** (anthropic.ts L20-22):
```typescript
const isBedrockModelArn = providerModel.startsWith("arn:aws:bedrock:")
const isBedrockModelID = providerModel.startsWith("global.anthropic.")
const isBedrock = isBedrockModelArn || isBedrockModelID
```

### 5.2 OpenAI 缓存实现

**隐式缓存配置**：
```typescript
// 在模型级别设置缓存键
result["promptCacheKey"] = input.sessionID
```

**缓存机制**：
- 自动应用于所有 system 消息和前面的 user/assistant 消息
- 最后一条消息自动排除（允许动态输入）
- 无需显式 breakpoint 标记

**成本结构**：
```
input_tokens_details.cached_tokens: 缓存读取的 tokens
// 缓存读取成本通常是 input 的 10%
```

**缓存键管理** (transform.ts L620-622):
```typescript
if (input.model.providerID === "openai" || input.providerOptions?.setCacheKey) {
  result["promptCacheKey"] = input.sessionID
}
```

---

## 6. 关键代码路径

### 6.1 消息处理流程

```
LLM.stream(input)
  ↓
ProviderTransform.message(msgs, model, options)
  ├─ normalizeMessages()        // 模型特定的消息规范化
  ├─ applyCaching()             // 添加缓存标记
  ├─ unsupportedParts()         // 过滤不支持的内容
  └─ return 处理后的消息
  ↓
ProviderTransform.options()
  ├─ 检查 providerID
  ├─ 设置 promptCacheKey (OpenAI)
  └─ return 模型选项
  ↓
streamText() (ai SDK)
  └─ 调用底层 API
```

### 6.2 成本计算流程

```
Provider.Model.cost
  ├─ input: 基础输入成本
  ├─ output: 基础输出成本
  ├─ cache.read: 缓存读取成本
  ├─ cache.write: 缓存写入成本
  └─ experimentalOver200K: 超过 200K tokens 的成本

Message.metadata.usage
  ├─ tokens.input: 实际输入 tokens
  ├─ tokens.output: 实际输出 tokens
  ├─ tokens.cache.read: 缓存读取 tokens
  └─ tokens.cache.write: 缓存写入 tokens

成本 = input * cost.input + output * cost.output 
      + cache_read * cost.cache.read 
      + cache_write * cost.cache.write
```

---

## 7. 测试覆盖

**文件**: `/packages/opencode/test/provider/transform.test.ts`

### 7.1 缓存键测试 (L6-85)

```typescript
describe("ProviderTransform.options - setCacheKey", () => {
  test("should set promptCacheKey when providerOptions.setCacheKey is true")
  test("should not set promptCacheKey when providerOptions.setCacheKey is false")
  test("should not set promptCacheKey when providerOptions is undefined")
  test("should not set promptCacheKey when providerOptions does not have setCacheKey")
  test("should set promptCacheKey for openai provider regardless of setCacheKey")
})
```

### 7.2 缓存控制测试 (L1295-1327)

```typescript
describe("ProviderTransform.message - claude w/bedrock custom inference profile", () => {
  test("adds cachePoint", () => {
    // 验证 Bedrock 的 cachePoint 正确添加
  })
})
```

---

## 8. 配置最佳实践

### 8.1 启用缓存

**对于 OpenAI**：
```typescript
// 自动启用，无需配置
const model = { providerID: "openai", ... }
```

**对于 Anthropic**：
```typescript
// 自动启用（通过 applyCaching）
const model = { providerID: "anthropic", ... }
```

**对于其他 provider**：
```typescript
// 显式启用
const options = ProviderTransform.options({
  model,
  sessionID,
  providerOptions: { setCacheKey: true }
})
```

### 8.2 成本优化

**缓存写入成本 > 输入成本**：
- 仅在会话中重复使用时才值得缓存
- 建议最少 3-5 次重复使用

**缓存读取成本 < 输入成本**：
- 缓存命中时节省 90% 的输入成本
- 长上下文场景下收益最大

---

## 9. 已知限制

### 9.1 不支持的 Provider

- **Google Gemini**: 无缓存支持
- **Mistral**: 无缓存支持
- **其他小型 provider**: 需要逐个添加支持

### 9.2 缓存失效场景

1. **系统提示变化**: 缓存自动失效
2. **消息顺序变化**: 缓存自动失效
3. **模型版本更新**: 缓存自动失效
4. **TTL 过期** (Anthropic): 5m/1h 后自动失效

### 9.3 缓存大小限制

- Anthropic: 系统消息 + 前面消息总计不超过上下文限制
- OpenAI: 同样受上下文限制约束
- Bedrock: 依赖 AWS 配置

---

## 10. 总结

### 核心设计原则

1. **分层抽象**: 缓存逻辑集中在 ProviderTransform 层
2. **多模型支持**: 通过 provider-specific 配置处理差异
3. **成本透明**: 缓存成本在模型定义中明确
4. **优雅降级**: 不支持的 provider 静默跳过缓存
5. **自动管理**: 缓存标记自动放置，无需手动干预

### 关键文件

| 文件 | 职责 |
|------|------|
| `transform.ts` | 缓存标记注入、消息转换 |
| `models.ts` | 缓存成本定义 |
| `provider.ts` | 模型元数据、成本计算 |
| `llm.ts` | 消息流处理 |
| `anthropic.ts` | Anthropic 缓存解析 |
| `openai.ts` | OpenAI 缓存解析 |
| `message.ts` | 缓存统计存储 |

### 与 Leon 的对比

| 特性 | OpenCode | Leon |
|------|----------|------|
| 缓存实现 | 分散在 provider 层 | 集中在 middleware 层 |
| 配置方式 | 模型级 + 消息级 | 中间件配置 |
| 多模型支持 | provider-specific | 统一接口 |
| 成本追踪 | 消息元数据 | Monitor middleware |
| 降级策略 | 静默跳过 | 可配置 |

