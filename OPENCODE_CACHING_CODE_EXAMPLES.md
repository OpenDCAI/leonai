# OpenCode Prompt Caching 代码示例与实现细节

---

## 1. 完整的消息处理流程

### 1.1 LLM 层入口

**文件**: `/packages/opencode/src/session/llm.ts` (L46-266)

```typescript
export async function stream(input: StreamInput) {
  // 1. 获取系统提示
  const system = []
  system.push(
    [
      ...(input.agent.prompt ? [input.agent.prompt] : isCodex ? [] : SystemPrompt.provider(input.model)),
      ...input.system,
      ...(input.user.system ? [input.user.system] : []),
    ]
      .filter((x) => x)
      .join("\n"),
  )

  // 2. 维持 2 部分结构以支持缓存
  const header = system[0]
  const original = clone(system)
  await Plugin.trigger("experimental.chat.system.transform", ...)
  
  if (system.length === 0) {
    system.push(...original)
  }
  
  // 重新组织为 2 部分结构（header + rest）
  if (system.length > 2 && system[0] === header) {
    const rest = system.slice(1)
    system.length = 0
    system.push(header, rest.join("\n"))
  }

  // 3. 构建消息数组
  const messages: ModelMessage[] = [
    ...system.map((x): ModelMessage => ({
      role: "system",
      content: x,
    })),
    ...input.messages,
  ]

  // 4. 调用 streamText
  return streamText({
    messages,
    model: wrapLanguageModel({
      model: language,
      middleware: [
        {
          async transformParams(args) {
            if (args.type === "stream") {
              // 在这里进行消息转换（包括缓存标记注入）
              args.params.prompt = ProviderTransform.message(
                args.params.prompt,
                input.model,
                options
              )
            }
            return args.params
          },
        },
      ],
    }),
    // ... 其他参数
  })
}
```

### 1.2 ProviderTransform 层处理

**文件**: `/packages/opencode/src/provider/transform.ts` (L44-209)

```typescript
export namespace ProviderTransform {
  // 主入口：处理消息
  export function message(
    msgs: ModelMessage[],
    model: Provider.Model,
    options: Record<string, unknown>,
  ): ModelMessage[] {
    // 步骤 1: 规范化消息（模型特定）
    msgs = normalizeMessages(msgs, model, options)

    // 步骤 2: 应用缓存标记
    msgs = applyCaching(msgs, model.providerID)

    // 步骤 3: 过滤不支持的内容
    msgs = unsupportedParts(msgs, model)

    return msgs
  }

  // 步骤 2: 应用缓存标记
  function applyCaching(msgs: ModelMessage[], providerID: string): ModelMessage[] {
    // 只在前 2 个 system 消息 + 最后 2 个消息上放置缓存标记
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

    // 应用缓存标记
    for (const msg of unique([...system, ...final])) {
      const useMessageLevelOptions = providerID === "anthropic" || providerID.includes("bedrock")
      const shouldUseContentOptions = !useMessageLevelOptions && Array.isArray(msg.content) && msg.content.length > 0

      if (shouldUseContentOptions) {
        // OpenAI 等：在最后一个 content part 上放置
        const lastContent = msg.content[msg.content.length - 1]
        if (lastContent && typeof lastContent === "object") {
          lastContent.providerOptions = mergeDeep(lastContent.providerOptions ?? {}, providerOptions)
          continue
        }
      }

      // Anthropic/Bedrock：在消息级别放置
      msg.providerOptions = mergeDeep(msg.providerOptions ?? {}, providerOptions)
    }

    return msgs
  }

  // 模型级别选项配置
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

    // GPT-5 特殊处理
    if (input.model.api.id.includes("gpt-5")) {
      if (input.model.providerID.startsWith("opencode")) {
        result["promptCacheKey"] = input.sessionID
        result["include"] = ["reasoning.encrypted_content"]
        result["reasoningSummary"] = "auto"
      }
    }

    return result
  }
}
```

---

## 2. Anthropic 缓存实现细节

### 2.1 缓存标记注入

**消息结构示例**：

```typescript
// 输入消息
const messages = [
  { role: "system", content: "You are a helpful assistant." },
  { role: "system", content: "Additional context..." },
  { role: "user", content: "Hello" },
  { role: "assistant", content: "Hi there!" },
  { role: "user", content: "How are you?" },
]

// 经过 applyCaching 后
const cachedMessages = [
  {
    role: "system",
    content: "You are a helpful assistant.",
    providerOptions: {
      anthropic: {
        cacheControl: { type: "ephemeral" }
      }
    }
  },
  {
    role: "system",
    content: "Additional context...",
    providerOptions: {
      anthropic: {
        cacheControl: { type: "ephemeral" }
      }
    }
  },
  { role: "user", content: "Hello" },
  { role: "assistant", content: "Hi there!" },
  {
    role: "user",
    content: "How are you?",
    providerOptions: {
      anthropic: {
        cacheControl: { type: "ephemeral" }
      }
    }
  },
]
```

### 2.2 缓存使用统计解析

**文件**: `/packages/console/app/src/routes/zen/util/provider/anthropic.ts` (L139-180)

```typescript
// 缓存使用统计类型
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

// 使用统计解析器
createUsageParser: () => {
  let usage: Usage

  return {
    parse: (chunk: string) => {
      const data = chunk.split("\n")[1]
      if (!data.startsWith("data: ")) return

      let json
      try {
        json = JSON.parse(data.slice(6))
      } catch (e) {
        return
      }

      const usageUpdate = json.usage ?? json.message?.usage
      if (!usageUpdate) return
      
      usage = {
        ...usage,
        ...usageUpdate,
        cache_creation: {
          ...usage?.cache_creation,
          ...usageUpdate.cache_creation,
        },
      }
    },
    retrieve: () => usage,
  }
},

// 统计规范化
normalizeUsage: (usage: Usage) => ({
  inputTokens: usage.input_tokens ?? 0,
  outputTokens: usage.output_tokens ?? 0,
  reasoningTokens: undefined,
  cacheReadTokens: usage.cache_read_input_tokens ?? undefined,
  cacheWrite5mTokens: usage.cache_creation?.ephemeral_5m_input_tokens ?? undefined,
  cacheWrite1hTokens: usage.cache_creation?.ephemeral_1h_input_tokens ?? undefined,
})
```

### 2.3 Bedrock 特殊处理

**文件**: `/packages/console/app/src/routes/zen/util/provider/anthropic.ts` (L19-53)

```typescript
export const anthropicHelper: ProviderHelper = ({ reqModel, providerModel }) => {
  // 检测 Bedrock 模型
  const isBedrockModelArn = providerModel.startsWith("arn:aws:bedrock:")
  const isBedrockModelID = providerModel.startsWith("global.anthropic.")
  const isBedrock = isBedrockModelArn || isBedrockModelID

  return {
    format: "anthropic",
    
    // Bedrock 使用不同的 URL 格式
    modifyUrl: (providerApi: string, isStream?: boolean) =>
      isBedrock
        ? `${providerApi}/model/${isBedrockModelArn ? encodeURIComponent(providerModel) : providerModel}/${isStream ? "invoke-with-response-stream" : "invoke"}`
        : providerApi + "/messages",

    // Bedrock 使用不同的请求头
    modifyHeaders: (headers: Headers, body: Record<string, any>, apiKey: string) => {
      if (isBedrock) {
        headers.set("Authorization", `Bearer ${apiKey}`)
      } else {
        headers.set("x-api-key", apiKey)
        headers.set("anthropic-version", headers.get("anthropic-version") ?? "2023-06-01")
      }
    },

    // Bedrock 需要特殊的请求体转换
    modifyBody: (body: Record<string, any>) => ({
      ...body,
      ...(isBedrock
        ? {
            anthropic_version: "bedrock-2023-05-31",
            model: undefined,
            stream: undefined,
          }
        : {
            service_tier: "standard_only",
          }),
    }),

    // Bedrock 使用二进制流编码
    createBinaryStreamDecoder: () => {
      if (!isBedrock) return undefined
      // ... 二进制解码逻辑
    },
  }
}
```

---

## 3. OpenAI 缓存实现细节

### 3.1 promptCacheKey 配置

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

### 3.2 缓存使用统计解析

**文件**: `/packages/console/app/src/routes/zen/util/provider/openai.ts` (L3-62)

```typescript
type Usage = {
  input_tokens?: number
  input_tokens_details?: {
    cached_tokens?: number
  }
  output_tokens?: number
  output_tokens_details?: {
    reasoning_tokens?: number
  }
  total_tokens?: number
}

export const openaiHelper: ProviderHelper = () => ({
  format: "openai",

  createUsageParser: () => {
    let usage: Usage

    return {
      parse: (chunk: string) => {
        const [event, data] = chunk.split("\n")
        if (event !== "event: response.completed") return
        if (!data.startsWith("data: ")) return

        let json
        try {
          json = JSON.parse(data.slice(6)) as { response?: { usage?: Usage } }
        } catch (e) {
          return
        }

        if (!json.response?.usage) return
        usage = json.response.usage
      },
      retrieve: () => usage,
    }
  },

  normalizeUsage: (usage: Usage) => {
    const inputTokens = usage.input_tokens ?? 0
    const outputTokens = usage.output_tokens ?? 0
    const reasoningTokens = usage.output_tokens_details?.reasoning_tokens ?? undefined
    const cacheReadTokens = usage.input_tokens_details?.cached_tokens ?? undefined
    
    return {
      inputTokens: inputTokens - (cacheReadTokens ?? 0),  // 扣除缓存读取
      outputTokens: outputTokens - (reasoningTokens ?? 0),
      reasoningTokens,
      cacheReadTokens,
      cacheWrite5mTokens: undefined,
      cacheWrite1hTokens: undefined,
    }
  },
})
```

---

## 4. 成本计算示例

### 4.1 模型成本定义

**文件**: `/packages/opencode/src/provider/models.ts`

```typescript
// 模型定义示例（Claude 3.5 Sonnet）
const model = {
  id: "claude-3-5-sonnet-20241022",
  name: "Claude 3.5 Sonnet",
  cost: {
    input: 0.003,           // $0.003 per 1K tokens
    output: 0.015,          // $0.015 per 1K tokens
    cache_read: 0.0003,     // $0.0003 per 1K tokens (90% 折扣)
    cache_write: 0.00375,   // $0.00375 per 1K tokens (25% 溢价)
  },
  limit: {
    context: 200000,
    output: 8192,
  },
}
```

### 4.2 成本计算逻辑

```typescript
// 假设一个请求的使用情况
const usage = {
  input_tokens: 1000,
  output_tokens: 500,
  cache_creation_input_tokens: 1000,  // 写入 1000 tokens
  cache_read_input_tokens: 0,         // 没有读取缓存
}

// 成本计算
const cost = {
  input: (1000 / 1000) * 0.003,                    // $0.003
  output: (500 / 1000) * 0.015,                   // $0.0075
  cache_write: (1000 / 1000) * 0.00375,           // $0.00375
  cache_read: (0 / 1000) * 0.0003,                // $0
  total: 0.003 + 0.0075 + 0.00375 + 0,            // $0.01425
}

// 第二个请求（缓存命中）
const usage2 = {
  input_tokens: 100,
  output_tokens: 500,
  cache_creation_input_tokens: 0,
  cache_read_input_tokens: 1000,  // 读取 1000 tokens 的缓存
}

const cost2 = {
  input: (100 / 1000) * 0.003,                    // $0.0003
  output: (500 / 1000) * 0.015,                   // $0.0075
  cache_write: 0,
  cache_read: (1000 / 1000) * 0.0003,             // $0.0003
  total: 0.0003 + 0.0075 + 0 + 0.0003,            // $0.0081
}

// 对比：
// 无缓存: $0.003 + $0.0075 = $0.0105
// 有缓存: $0.0081 (节省 23%)
```

---

## 5. 测试用例

### 5.1 缓存键测试

**文件**: `/packages/opencode/test/provider/transform.test.ts` (L6-85)

```typescript
describe("ProviderTransform.options - setCacheKey", () => {
  const sessionID = "test-session-123"

  const mockModel = {
    id: "anthropic/claude-3-5-sonnet",
    providerID: "anthropic",
    api: {
      id: "claude-3-5-sonnet-20241022",
      url: "https://api.anthropic.com",
      npm: "@ai-sdk/anthropic",
    },
    name: "Claude 3.5 Sonnet",
    capabilities: {
      temperature: true,
      reasoning: false,
      attachment: true,
      toolcall: true,
      input: { text: true, audio: false, image: true, video: false, pdf: true },
      output: { text: true, audio: false, image: false, video: false, pdf: false },
      interleaved: false,
    },
    cost: {
      input: 0.003,
      output: 0.015,
      cache: { read: 0.0003, write: 0.00375 },
    },
    limit: {
      context: 200000,
      output: 8192,
    },
    status: "active",
    options: {},
    headers: {},
  } as any

  // 测试 1: 显式启用缓存
  test("should set promptCacheKey when providerOptions.setCacheKey is true", () => {
    const result = ProviderTransform.options({
      model: mockModel,
      sessionID,
      providerOptions: { setCacheKey: true },
    })
    expect(result.promptCacheKey).toBe(sessionID)
  })

  // 测试 2: 显式禁用缓存
  test("should not set promptCacheKey when providerOptions.setCacheKey is false", () => {
    const result = ProviderTransform.options({
      model: mockModel,
      sessionID,
      providerOptions: { setCacheKey: false },
    })
    expect(result.promptCacheKey).toBeUndefined()
  })

  // 测试 3: OpenAI 自动启用
  test("should set promptCacheKey for openai provider regardless of setCacheKey", () => {
    const openaiModel = {
      ...mockModel,
      providerID: "openai",
      api: {
        id: "gpt-4",
        url: "https://api.openai.com",
        npm: "@ai-sdk/openai",
      },
    }
    const result = ProviderTransform.options({ model: openaiModel, sessionID, providerOptions: {} })
    expect(result.promptCacheKey).toBe(sessionID)
  })
})
```

### 5.2 缓存控制测试

**文件**: `/packages/opencode/test/provider/transform.test.ts` (L1295-1327)

```typescript
describe("ProviderTransform.message - claude w/bedrock custom inference profile", () => {
  test("adds cachePoint", () => {
    const model = {
      id: "amazon-bedrock/custom-claude-sonnet-4.5",
      providerID: "amazon-bedrock",
      api: {
        id: "arn:aws:bedrock:xxx:yyy:application-inference-profile/zzz",
        url: "https://api.test.com",
        npm: "@ai-sdk/amazon-bedrock",
      },
      name: "Custom inference profile",
      capabilities: {},
      options: {},
      headers: {},
    } as any

    const msgs = [
      {
        role: "user",
        content: "Hello",
      },
    ] as any[]

    const result = ProviderTransform.message(msgs, model, {})

    // 验证 Bedrock 的 cachePoint 正确添加
    expect(result[0].providerOptions?.bedrock).toEqual(
      expect.objectContaining({
        cachePoint: {
          type: "default",
        },
      }),
    )
  })
})
```

---

## 6. 实际使用场景

### 6.1 长上下文场景

```typescript
// 场景：代码审查 Agent，需要反复分析同一个大文件

// 第一次请求
const firstRequest = {
  messages: [
    {
      role: "system",
      content: "You are a code review expert...",
      providerOptions: {
        anthropic: { cacheControl: { type: "ephemeral" } }
      }
    },
    {
      role: "user",
      content: "Review this 50KB code file: " + largeCodeFile,
      providerOptions: {
        anthropic: { cacheControl: { type: "ephemeral" } }
      }
    },
    {
      role: "user",
      content: "What are the security issues?",
    }
  ]
}

// 成本: $0.15 (50KB 代码 + 系统提示缓存写入)

// 第二次请求（同一个文件，不同问题）
const secondRequest = {
  messages: [
    {
      role: "system",
      content: "You are a code review expert...",
      providerOptions: {
        anthropic: { cacheControl: { type: "ephemeral" } }
      }
    },
    {
      role: "user",
      content: "Review this 50KB code file: " + largeCodeFile,
      providerOptions: {
        anthropic: { cacheControl: { type: "ephemeral" } }
      }
    },
    {
      role: "user",
      content: "What are the performance issues?",
    }
  ]
}

// 成本: $0.015 (只有新问题的输入成本，缓存读取成本极低)
// 节省: 90% 的输入成本
```

### 6.2 多轮对话场景

```typescript
// 场景：客服 Agent，需要维持长对话历史

// 对话 1-5: 建立缓存
// 对话 6+: 缓存命中，成本大幅降低

const conversation = [
  { role: "system", content: "You are a helpful customer service agent..." },
  { role: "user", content: "I have a billing question" },
  { role: "assistant", content: "I'd be happy to help..." },
  { role: "user", content: "My invoice shows..." },
  { role: "assistant", content: "Let me check that..." },
  // ... 更多对话
  { role: "user", content: "Can you also help with..." },
]

// 前 5 条消息被缓存，后续请求只需支付新消息的成本
```

---

## 7. 调试技巧

### 7.1 查看缓存标记

```typescript
// 在 ProviderTransform.message 中添加日志
function applyCaching(msgs: ModelMessage[], providerID: string): ModelMessage[] {
  // ...
  for (const msg of unique([...system, ...final])) {
    // ...
    console.log("Caching message:", {
      role: msg.role,
      contentLength: typeof msg.content === "string" ? msg.content.length : msg.content?.length,
      providerOptions: msg.providerOptions,
    })
  }
  return msgs
}
```

### 7.2 查看缓存使用统计

```typescript
// 在 normalizeUsage 中添加日志
normalizeUsage: (usage: Usage) => {
  console.log("Cache usage:", {
    inputTokens: usage.input_tokens,
    cacheReadTokens: usage.cache_read_input_tokens,
    cacheWrite5m: usage.cache_creation?.ephemeral_5m_input_tokens,
    cacheWrite1h: usage.cache_creation?.ephemeral_1h_input_tokens,
  })
  
  return {
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    cacheReadTokens: usage.cache_read_input_tokens ?? undefined,
    cacheWrite5mTokens: usage.cache_creation?.ephemeral_5m_input_tokens ?? undefined,
    cacheWrite1hTokens: usage.cache_creation?.ephemeral_1h_input_tokens ?? undefined,
  }
}
```

---

## 8. 常见问题

### Q1: 为什么 Google Gemini 不支持缓存？

**A**: Google 的缓存实现与 Anthropic/OpenAI 不同，需要单独的 API 支持。OpenCode 目前未实现 Google 的缓存支持。

### Q2: 缓存写入成本为什么比输入成本高？

**A**: 这是 Anthropic 的定价策略。缓存写入需要额外的处理成本，但缓存读取成本极低（90% 折扣），所以长期来看仍然划算。

### Q3: 如何确保缓存命中？

**A**: 
1. 保持系统提示不变
2. 保持消息顺序不变
3. 使用相同的 sessionID
4. 在 TTL 内重复使用（Anthropic: 5m/1h）

### Q4: 缓存大小有限制吗？

**A**: 缓存大小受上下文窗口限制。例如 Claude 3.5 Sonnet 的上下文是 200K tokens，缓存内容不能超过这个限制。

