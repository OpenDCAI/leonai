# OpenCode Token 追踪和计费实现分析

## 概述

OpenCode 是一个 TypeScript/JavaScript 项目（使用 Bun 和 SST），采用**分层架构**实现 token 追踪和计费：

1. **客户端层** (`packages/opencode/`)：计算 token 和成本
2. **网关层** (`packages/console/app/routes/zen/`)：拦截 API 请求，记录 usage
3. **数据库层** (`packages/console/core/`)：存储 usage 和 billing 数据

---

## 1. Token 计算架构

### 1.1 模型成本定义 (`packages/opencode/src/provider/models.ts`)

```typescript
// 模型成本结构
cost: {
  input: number,           // 每百万 token 的输入成本（美元）
  output: number,          // 每百万 token 的输出成本（美元）
  cache_read?: number,     // 缓存读取成本
  cache_write?: number,    // 缓存写入成本
  context_over_200k?: {    // 超过 200K token 的特殊定价
    input: number,
    output: number,
    cache_read?: number,
    cache_write?: number,
  }
}
```

### 1.2 客户端 Token 计算 (`packages/opencode/src/session/index.ts`)

**关键函数：`Session.getUsage()`**

```typescript
export const getUsage = fn(
  z.object({
    model: z.custom<Provider.Model>(),
    usage: z.custom<LanguageModelUsage>(),
    metadata: z.custom<ProviderMetadata>().optional(),
  }),
  (input) => {
    // 1. 提取缓存 token
    const cacheReadInputTokens = input.usage.cachedInputTokens ?? 0
    const cacheWriteInputTokens = (
      input.metadata?.["anthropic"]?.["cacheCreationInputTokens"] ??
      input.metadata?.["bedrock"]?.["usage"]?.["cacheWriteInputTokens"] ??
      input.metadata?.["venice"]?.["usage"]?.["cacheCreationInputTokens"] ??
      0
    ) as number

    // 2. 调整输入 token（某些提供商已排除缓存 token）
    const excludesCachedTokens = !!(
      input.metadata?.["anthropic"] || input.metadata?.["bedrock"]
    )
    const adjustedInputTokens = excludesCachedTokens
      ? (input.usage.inputTokens ?? 0)
      : (input.usage.inputTokens ?? 0) - cacheReadInputTokens - cacheWriteInputTokens

    // 3. 构建 token 对象
    const tokens = {
      input: safe(adjustedInputTokens),
      output: safe(input.usage.outputTokens ?? 0),
      reasoning: safe(input.usage?.reasoningTokens ?? 0),
      cache: {
        write: safe(cacheWriteInputTokens),
        read: safe(cacheReadInputTokens),
      },
    }

    // 4. 选择成本信息（200K+ 特殊定价）
    const costInfo =
      input.model.cost?.experimentalOver200K && 
      tokens.input + tokens.cache.read > 200_000
        ? input.model.cost.experimentalOver200K
        : input.model.cost

    // 5. 计算成本（使用 Decimal.js 精确计算）
    return {
      cost: safe(
        new Decimal(0)
          .add(new Decimal(tokens.input).mul(costInfo?.input ?? 0).div(1_000_000))
          .add(new Decimal(tokens.output).mul(costInfo?.output ?? 0).div(1_000_000))
          .add(new Decimal(tokens.cache.read).mul(costInfo?.cache?.read ?? 0).div(1_000_000))
          .add(new Decimal(tokens.cache.write).mul(costInfo?.cache?.write ?? 0).div(1_000_000))
          // 推理 token 按输出价格计费
          .add(new Decimal(tokens.reasoning).mul(costInfo?.output ?? 0).div(1_000_000))
          .toNumber(),
      ),
      tokens,
    }
  },
)
```

**Token 分项追踪：**
- `input`：调整后的输入 token（排除缓存读写）
- `output`：输出 token
- `reasoning`：推理 token（仅 o1/o3 等模型）
- `cache.read`：缓存读取 token
- `cache.write`：缓存写入 token（5m 和 1h 分别追踪）

---

## 2. 消息级别的 Token 和成本存储

### 2.1 消息结构 (`packages/opencode/src/session/message-v2.ts`)

**Assistant 消息包含：**
```typescript
export const Assistant = z.object({
  // ... 其他字段
  cost: z.number(),  // 总成本（美元）
  tokens: z.object({
    input: z.number(),
    output: z.number(),
    reasoning: z.number(),
    cache: z.object({
      read: z.number(),
      write: z.number(),
    }),
  }),
  finish: z.string().optional(),
})
```

**Step Finish Part（每个 LLM 调用）：**
```typescript
export const StepFinishPart = PartBase.extend({
  type: z.literal("step-finish"),
  reason: z.string(),
  snapshot: z.string().optional(),
  cost: z.number(),
  tokens: z.object({
    input: z.number(),
    output: z.number(),
    reasoning: z.number(),
    cache: z.object({
      read: z.number(),
      write: z.number(),
    }),
  }),
})
```

### 2.2 处理流程 (`packages/opencode/src/session/processor.ts`)

```typescript
case "finish-step":
  const usage = Session.getUsage({
    model: input.model,
    usage: value.usage,
    metadata: value.providerMetadata,
  })
  input.assistantMessage.finish = value.finishReason
  input.assistantMessage.cost += usage.cost  // 累加成本
  input.assistantMessage.tokens = usage.tokens
  
  // 保存 step-finish part
  await Session.updatePart({
    id: Identifier.ascending("part"),
    reason: value.finishReason,
    snapshot: await Snapshot.track(),
    messageID: input.assistantMessage.id,
    sessionID: input.assistantMessage.sessionID,
    type: "step-finish",
    tokens: usage.tokens,
    cost: usage.cost,
  })
```

---

## 3. 网关层 Usage 记录

### 3.1 Provider 适配层 (`packages/console/app/routes/zen/util/provider/`)

**通用 Usage 信息结构：**
```typescript
export type UsageInfo = {
  inputTokens: number
  outputTokens: number
  reasoningTokens?: number
  cacheReadTokens?: number
  cacheWrite5mTokens?: number
  cacheWrite1hTokens?: number
}
```

**Provider 适配器接口：**
```typescript
export type ProviderHelper = (input: { reqModel: string; providerModel: string }) => {
  format: ZenData.Format
  modifyUrl: (providerApi: string, isStream?: boolean) => string
  modifyHeaders: (headers: Headers, body: Record<string, any>, apiKey: string) => void
  modifyBody: (body: Record<string, any>) => Record<string, any>
  createBinaryStreamDecoder: () => ((chunk: Uint8Array) => Uint8Array | undefined) | undefined
  streamSeparator: string
  createUsageParser: () => {
    parse: (chunk: string) => void
    retrieve: () => any
  }
  normalizeUsage: (usage: any) => UsageInfo
}
```

### 3.2 OpenAI Provider 适配 (`openai.ts`)

```typescript
normalizeUsage: (usage: Usage) => {
  const inputTokens = usage.input_tokens ?? 0
  const outputTokens = usage.output_tokens ?? 0
  const reasoningTokens = usage.output_tokens_details?.reasoning_tokens ?? undefined
  const cacheReadTokens = usage.input_tokens_details?.cached_tokens ?? undefined
  return {
    inputTokens: inputTokens - (cacheReadTokens ?? 0),  // 排除缓存读
    outputTokens: outputTokens - (reasoningTokens ?? 0),  // 排除推理 token
    reasoningTokens,
    cacheReadTokens,
    cacheWrite5mTokens: undefined,
    cacheWrite1hTokens: undefined,
  }
}
```

### 3.3 Anthropic Provider 适配 (`anthropic.ts`)

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

---

## 4. 成本计算和计费 (`packages/console/app/routes/zen/util/handler.ts`)

### 4.1 分项成本计算

```typescript
async function trackUsage(
  authInfo: AuthInfo,
  modelInfo: ModelInfo,
  providerInfo: ProviderInfo,
  billingSource: ReturnType<typeof validateBilling>,
  usageInfo: UsageInfo,
) {
  const { inputTokens, outputTokens, reasoningTokens, cacheReadTokens, cacheWrite5mTokens, cacheWrite1hTokens } = usageInfo

  // 选择成本信息（200K+ 特殊定价）
  const modelCost =
    modelInfo.cost200K &&
    inputTokens + (cacheReadTokens ?? 0) + (cacheWrite5mTokens ?? 0) + (cacheWrite1hTokens ?? 0) > 200_000
      ? modelInfo.cost200K
      : modelInfo.cost

  // 分项计算成本（单位：cent）
  const inputCost = modelCost.input * inputTokens * 100
  const outputCost = modelCost.output * outputTokens * 100
  const reasoningCost = reasoningTokens ? modelCost.output * reasoningTokens * 100 : undefined
  const cacheReadCost = cacheReadTokens && modelCost.cacheRead 
    ? modelCost.cacheRead * cacheReadTokens * 100 
    : undefined
  const cacheWrite5mCost = cacheWrite5mTokens && modelCost.cacheWrite5m
    ? modelCost.cacheWrite5m * cacheWrite5mTokens * 100
    : undefined
  const cacheWrite1hCost = cacheWrite1hTokens && modelCost.cacheWrite1h
    ? modelCost.cacheWrite1h * cacheWrite1hTokens * 100
    : undefined

  // 总成本
  const totalCostInCent =
    inputCost +
    outputCost +
    (reasoningCost ?? 0) +
    (cacheReadCost ?? 0) +
    (cacheWrite5mCost ?? 0) +
    (cacheWrite1hCost ?? 0)

  // 记录指标
  logger.metric({
    "tokens.input": inputTokens,
    "tokens.output": outputTokens,
    "tokens.reasoning": reasoningTokens,
    "tokens.cache_read": cacheReadTokens,
    "tokens.cache_write_5m": cacheWrite5mTokens,
    "tokens.cache_write_1h": cacheWrite1hTokens,
    "cost.input": Math.round(inputCost),
    "cost.output": Math.round(outputCost),
    "cost.reasoning": reasoningCost ? Math.round(reasoningCost) : undefined,
    "cost.cache_read": cacheReadCost ? Math.round(cacheReadCost) : undefined,
    "cost.cache_write_5m": cacheWrite5mCost ? Math.round(cacheWrite5mCost) : undefined,
    "cost.cache_write_1h": cacheWrite1hCost ? Math.round(cacheWrite1hCost) : undefined,
    "cost.total": Math.round(totalCostInCent),
  })
```

### 4.2 成本分项说明

| 分项 | 计算方式 | 说明 |
|------|--------|------|
| 输入成本 | `inputTokens * modelCost.input / 1M * 100` | 调整后的输入 token（排除缓存） |
| 输出成本 | `outputTokens * modelCost.output / 1M * 100` | 输出 token |
| 推理成本 | `reasoningTokens * modelCost.output / 1M * 100` | 推理 token 按输出价格计费 |
| 缓存读成本 | `cacheReadTokens * modelCost.cacheRead / 1M * 100` | 缓存命中的 token |
| 缓存写成本 | `cacheWrite*Tokens * modelCost.cacheWrite* / 1M * 100` | 缓存创建的 token（5m/1h） |

---

## 5. 数据库存储

### 5.1 Usage 表结构 (`packages/console/core/src/schema/billing.sql.ts`)

```typescript
export const UsageTable = mysqlTable("usage", {
  ...workspaceColumns,
  ...timestamps,
  model: varchar("model", { length: 255 }).notNull(),
  provider: varchar("provider", { length: 255 }).notNull(),
  inputTokens: int("input_tokens").notNull(),
  outputTokens: int("output_tokens").notNull(),
  reasoningTokens: int("reasoning_tokens"),
  cacheReadTokens: int("cache_read_tokens"),
  cacheWrite5mTokens: int("cache_write_5m_tokens"),
  cacheWrite1hTokens: int("cache_write_1h_tokens"),
  cost: bigint("cost", { mode: "number" }).notNull(),  // 微分（microcents）
  keyID: ulid("key_id"),
  enrichment: json("enrichment").$type<{
    plan: "sub"
  }>(),
})
```

### 5.2 Usage 记录流程

```typescript
// 1. 插入 usage 记录
db.insert(UsageTable).values({
  workspaceID: authInfo.workspaceID,
  id: Identifier.create("usage"),
  model: modelInfo.id,
  provider: providerInfo.id,
  inputTokens,
  outputTokens,
  reasoningTokens,
  cacheReadTokens,
  cacheWrite5mTokens,
  cacheWrite1hTokens,
  cost,  // 微分
  keyID: authInfo.apiKeyId,
  enrichment: billingSource === "subscription" ? { plan: "sub" } : undefined,
})

// 2. 更新 API Key 使用时间
db.update(KeyTable)
  .set({ timeUsed: sql`now()` })
  .where(and(
    eq(KeyTable.workspaceID, authInfo.workspaceID),
    eq(KeyTable.id, authInfo.apiKeyId)
  ))

// 3. 更新订阅或余额
if (billingSource === "subscription") {
  // 更新订阅使用量（固定周期 + 滚动窗口）
  db.update(SubscriptionTable).set({
    fixedUsage: sql`CASE WHEN ... THEN ... ELSE ... END`,
    rollingUsage: sql`CASE WHEN ... THEN ... ELSE ... END`,
  })
} else {
  // 更新账户余额和月度使用量
  db.update(BillingTable).set({
    balance: sql`${BillingTable.balance} - ${cost}`,
    monthlyUsage: sql`CASE WHEN ... THEN ... ELSE ... END`,
  })
}
```

---

## 6. 计费模式

### 6.1 两种计费来源

```typescript
type BillingSource = "subscription" | "credits" | "anonymous"

// 订阅模式：固定周期 + 滚动窗口
if (billingSource === "subscription") {
  // fixedUsage：本周期内的累计成本
  // rollingUsage：滚动窗口内的累计成本
}

// 余额模式：直接扣费
else {
  // balance -= cost
  // monthlyUsage += cost
}
```

### 6.2 自动充值机制

```typescript
async function reload(authInfo: AuthInfo, costInfo: Awaited<ReturnType<typeof trackUsage>>) {
  if (!authInfo) return
  if (authInfo.isFree) return
  if (authInfo.provider?.credentials) return  // 自带 API Key 不计费
  if (authInfo.subscription) return  // 订阅用户不自动充值

  const reloadTrigger = centsToMicroCents(
    (authInfo.billing.reloadTrigger ?? Billing.RELOAD_TRIGGER) * 100
  )
  
  // 余额低于触发值时自动充值
  if (authInfo.billing.balance - costInfo.costInMicroCents >= reloadTrigger) return
  
  // 触发自动充值（通过 Stripe）
  await Billing.reload()
}
```

---

## 7. 关键特性

### 7.1 分项追踪

✅ **完整的分项追踪：**
- 输入 token（排除缓存）
- 输出 token
- 推理 token（o1/o3）
- 缓存读取 token
- 缓存写入 token（5m/1h 分别）

✅ **分项成本计算：**
- 每项都有独立的成本计算
- 支持不同的定价（如缓存读写有特殊价格）
- 200K+ token 特殊定价支持

### 7.2 多提供商支持

✅ **Provider 适配层：**
- OpenAI（包括 Responses API）
- Anthropic（包括 Bedrock）
- Google（Vertex AI）
- 其他 OpenAI 兼容 API

✅ **Usage 规范化：**
- 每个 provider 有自己的 usage 格式
- 统一转换为 `UsageInfo` 结构
- 处理 provider 差异（如缓存 token 是否已排除）

### 7.3 精确计算

✅ **使用 Decimal.js：**
- 避免浮点精度问题
- 成本计算精确到微分（microcents）

✅ **单位转换：**
- 模型定价：美元/百万 token
- 数据库存储：微分（1 美元 = 100 万微分）
- 计算过程：cent（1 美元 = 100 cent）

### 7.4 实时监控

✅ **指标记录：**
- 每个请求的 token 分项
- 每个请求的成本分项
- 时间指标（TTFB、响应时间等）

✅ **数据库查询：**
- 按 workspace 查询 usage
- 按 model/provider 分析成本
- 按时间范围统计

---

## 8. 与 Leon 的对比

| 特性 | OpenCode | Leon |
|------|----------|------|
| Token 追踪 | ✅ 分项追踪（6 项） | ✅ 基础追踪（4 项） |
| 成本计算 | ✅ 分项计算 + 200K+ 特殊定价 | ✅ 基础计算 |
| 缓存支持 | ✅ 5m/1h 分别追踪 | ✅ 基础支持 |
| 推理 token | ✅ 支持 | ✅ 支持 |
| 计费模式 | ✅ 订阅 + 余额 + 自动充值 | ⚠️ 基础余额 |
| Provider 适配 | ✅ 多层适配（API 层 + 规范化层） | ✅ 单层适配 |
| 精确计算 | ✅ Decimal.js | ✅ Decimal.js |
| 实时监控 | ✅ 详细指标 | ✅ 基础监控 |

---

## 9. 可借鉴的设计模式

### 9.1 Provider 适配器模式

```typescript
// 定义通用接口
export type ProviderHelper = (input) => {
  normalizeUsage: (usage: any) => UsageInfo
  createUsageParser: () => { parse, retrieve }
  // ...
}

// 每个 provider 实现适配器
export const openaiHelper: ProviderHelper = () => ({ ... })
export const anthropicHelper: ProviderHelper = () => ({ ... })
```

**优点：**
- 隔离 provider 差异
- 易于扩展新 provider
- 统一的 usage 规范

### 9.2 分层计算

```
API 响应 → Provider 适配 → 规范化 → 成本计算 → 数据库存储
```

**优点：**
- 职责清晰
- 易于测试
- 易于调试

### 9.3 指标记录

```typescript
logger.metric({
  "tokens.input": inputTokens,
  "tokens.output": outputTokens,
  "cost.input": Math.round(inputCost),
  "cost.output": Math.round(outputCost),
  "cost.total": Math.round(totalCostInCent),
})
```

**优点：**
- 实时可观测性
- 便于告警和分析
- 支持成本优化

---

## 10. 总结

OpenCode 的 token 追踪和计费系统具有以下特点：

1. **完整的分项追踪**：6 项 token 分别追踪，每项都有独立的成本计算
2. **多层适配**：API 层 → 规范化层 → 计算层，隔离 provider 差异
3. **精确计算**：使用 Decimal.js，支持微分级别的精确计费
4. **灵活的计费模式**：支持订阅、余额、自动充值等多种模式
5. **实时监控**：详细的指标记录，便于成本分析和优化
6. **可扩展性**：易于添加新的 provider 和计费模式

这套系统可以作为 Leon 的参考，特别是在分项追踪、provider 适配和计费模式方面。
