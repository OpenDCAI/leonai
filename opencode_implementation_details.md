# OpenCode Token 追踪实现细节

## 核心文件位置

```
opencode/
├── packages/opencode/src/
│   ├── session/
│   │   ├── index.ts              # Session.getUsage() - 核心计算
│   │   ├── message-v2.ts         # 消息结构定义
│   │   ├── processor.ts          # 处理流程
│   │   └── llm.ts                # LLM 流处理
│   └── provider/
│       └── models.ts             # 模型成本定义
│
└── packages/console/
    ├── core/src/
    │   ├── schema/billing.sql.ts # 数据库表结构
    │   └── billing.ts            # 计费逻辑
    └── app/src/routes/zen/util/
        ├── handler.ts            # trackUsage() - 网关层计费
        └── provider/
            ├── provider.ts       # 通用接口
            ├── openai.ts         # OpenAI 适配
            ├── anthropic.ts      # Anthropic 适配
            └── google.ts         # Google 适配
```

---

## 1. Token 计算的关键细节

### 1.1 缓存 Token 的处理

**问题：** 不同 provider 对缓存 token 的报告方式不同

**OpenAI 的处理：**
```typescript
// OpenAI 在 input_tokens_details 中报告缓存 token
const cacheReadTokens = usage.input_tokens_details?.cached_tokens ?? undefined

// 需要从 inputTokens 中排除缓存 token
return {
  inputTokens: inputTokens - (cacheReadTokens ?? 0),
  cacheReadTokens,
}
```

**Anthropic 的处理：**
```typescript
// Anthropic 已经在 input_tokens 中排除了缓存 token
// 缓存 token 单独报告
const cacheReadInputTokens = usage.cache_read_input_tokens ?? undefined
const cacheWrite5mTokens = usage.cache_creation?.ephemeral_5m_input_tokens ?? undefined

// 直接使用 input_tokens，不需要调整
return {
  inputTokens: usage.input_tokens ?? 0,
  cacheReadTokens: cacheReadInputTokens,
  cacheWrite5mTokens,
}
```

**客户端的统一处理：**
```typescript
// 检测 provider 是否已排除缓存 token
const excludesCachedTokens = !!(
  input.metadata?.["anthropic"] || input.metadata?.["bedrock"]
)

// 根据 provider 类型调整
const adjustedInputTokens = excludesCachedTokens
  ? (input.usage.inputTokens ?? 0)  // 已排除，直接使用
  : (input.usage.inputTokens ?? 0) - cacheReadInputTokens - cacheWriteInputTokens  // 需要排除
```

### 1.2 推理 Token 的处理

**OpenAI o1/o3 模型：**
```typescript
// OpenAI 在 output_tokens_details 中报告推理 token
const reasoningTokens = usage.output_tokens_details?.reasoning_tokens ?? undefined

// 需要从 outputTokens 中排除推理 token
return {
  outputTokens: outputTokens - (reasoningTokens ?? 0),
  reasoningTokens,
}
```

**成本计算：**
```typescript
// 推理 token 按输出价格计费（与输出 token 相同）
const reasoningCost = reasoningTokens 
  ? modelCost.output * reasoningTokens * 100 
  : undefined
```

### 1.3 200K+ Token 特殊定价

```typescript
// 某些模型在超过 200K token 时有特殊定价
const costInfo =
  input.model.cost?.experimentalOver200K && 
  tokens.input + tokens.cache.read > 200_000
    ? input.model.cost.experimentalOver200K
    : input.model.cost

// 计算时使用选定的成本信息
const inputCost = costInfo.input * tokens.input / 1_000_000
```

---

## 2. 成本计算的精确性

### 2.1 单位转换链

```
模型定价（美元/百万 token）
    ↓
计算过程（cent = 美元 * 100）
    ↓
数据库存储（microcents = cent * 10000）
```

**具体计算：**
```typescript
// 模型定价：0.003 美元/百万 token（OpenAI GPT-4）
const modelCost = { input: 0.003, output: 0.006 }

// 计算成本（单位：cent）
const inputCost = modelCost.input * inputTokens * 100
// = 0.003 * 1000000 * 100 = 300000 cent = $3000

// 存储到数据库（单位：microcents）
const costInMicroCents = centsToMicroCents(totalCostInCent)
// = totalCostInCent * 10000
```

### 2.2 使用 Decimal.js 避免浮点精度问题

```typescript
// 错误方式（浮点精度问题）
const cost = 0.003 * 1000000 * 100  // 可能得到 299999.99999999994

// 正确方式（Decimal.js）
const cost = new Decimal(0)
  .add(new Decimal(tokens.input).mul(costInfo?.input ?? 0).div(1_000_000))
  .add(new Decimal(tokens.output).mul(costInfo?.output ?? 0).div(1_000_000))
  .toNumber()
```

---

## 3. Provider 适配层的设计

### 3.1 适配器接口

```typescript
export type ProviderHelper = (input: { 
  reqModel: string;      // 请求中的模型名
  providerModel: string; // Provider 实际使用的模型名
}) => {
  format: ZenData.Format                    // "openai" | "anthropic" | "google"
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

### 3.2 流式响应的 Usage 解析

**OpenAI 流式响应：**
```typescript
createUsageParser: () => {
  let usage: Usage

  return {
    parse: (chunk: string) => {
      const [event, data] = chunk.split("\n")
      if (event !== "event: response.completed") return  // 只在完成时有 usage
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
}
```

**Anthropic 流式响应：**
```typescript
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

      // Anthropic 在每个事件中都可能有 usage，需要合并
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
}
```

---

## 4. 网关层的 Usage 记录

### 4.1 非流式请求的处理

```typescript
// 1. 获取响应
const json = await res.json()

// 2. 规范化 usage
const tokensInfo = providerInfo.normalizeUsage(json.usage)

// 3. 记录指标
logger.metric({
  "tokens.input": tokensInfo.inputTokens,
  "tokens.output": tokensInfo.outputTokens,
  "tokens.reasoning": tokensInfo.reasoningTokens,
  "tokens.cache_read": tokensInfo.cacheReadTokens,
  "tokens.cache_write_5m": tokensInfo.cacheWrite5mTokens,
  "tokens.cache_write_1h": tokensInfo.cacheWrite1hTokens,
})

// 4. 计费
const costInfo = await trackUsage(authInfo, modelInfo, providerInfo, billingSource, tokensInfo)

// 5. 自动充值
await reload(authInfo, costInfo)
```

### 4.2 流式请求的处理

```typescript
// 1. 创建 usage 解析器
const usageParser = providerInfo.createUsageParser()

// 2. 在流处理中解析 usage
for (let part of parts) {
  part = part.trim()
  usageParser.parse(part)  // 累积 usage 信息
}

// 3. 流结束时获取最终 usage
const usage = usageParser.retrieve()
if (usage) {
  const tokensInfo = providerInfo.normalizeUsage(usage)
  const costInfo = await trackUsage(authInfo, modelInfo, providerInfo, billingSource, tokensInfo)
  await reload(authInfo, costInfo)
}
```

---

## 5. 数据库存储的细节

### 5.1 Usage 表的索引

```typescript
export const UsageTable = mysqlTable("usage", {
  // ... 字段定义
}, (table) => [
  ...workspaceIndexes(table),
  index("usage_time_created").on(table.workspaceID, table.timeCreated),
])
```

**索引策略：**
- `workspaceID` + `timeCreated`：用于按时间范围查询
- `workspaceID`：用于按 workspace 查询

### 5.2 订阅 vs 余额计费的差异

**订阅计费（固定周期 + 滚动窗口）：**
```typescript
db.update(SubscriptionTable).set({
  // 固定周期：本周期内的累计成本
  fixedUsage: sql`
    CASE
      WHEN ${SubscriptionTable.timeFixedUpdated} >= ${week.start} 
      THEN ${SubscriptionTable.fixedUsage} + ${cost}
      ELSE ${cost}
    END
  `,
  
  // 滚动窗口：过去 N 小时内的累计成本
  rollingUsage: sql`
    CASE
      WHEN UNIX_TIMESTAMP(${SubscriptionTable.timeRollingUpdated}) >= UNIX_TIMESTAMP(now()) - ${rollingWindowSeconds}
      THEN ${SubscriptionTable.rollingUsage} + ${cost}
      ELSE ${cost}
    END
  `,
})
```

**余额计费（直接扣费）：**
```typescript
db.update(BillingTable).set({
  // 直接扣费
  balance: sql`${BillingTable.balance} - ${cost}`,
  
  // 月度使用量
  monthlyUsage: sql`
    CASE
      WHEN MONTH(${BillingTable.timeMonthlyUsageUpdated}) = MONTH(now()) 
        AND YEAR(${BillingTable.timeMonthlyUsageUpdated}) = YEAR(now())
      THEN ${BillingTable.monthlyUsage} + ${cost}
      ELSE ${cost}
    END
  `,
})
```

---

## 6. 自动充值机制

### 6.1 充值触发条件

```typescript
async function reload(authInfo: AuthInfo, costInfo: Awaited<ReturnType<typeof trackUsage>>) {
  // 不需要充值的情况
  if (!authInfo) return
  if (authInfo.isFree) return                    // 免费用户
  if (authInfo.provider?.credentials) return    // 自带 API Key
  if (authInfo.subscription) return             // 订阅用户

  // 获取充值触发值
  const reloadTrigger = centsToMicroCents(
    (authInfo.billing.reloadTrigger ?? Billing.RELOAD_TRIGGER) * 100
  )
  
  // 余额充足，不需要充值
  if (authInfo.billing.balance - costInfo.costInMicroCents >= reloadTrigger) return
  
  // 已在充值冷却期，不需要充值
  if (authInfo.billing.timeReloadLockedTill && authInfo.billing.timeReloadLockedTill > new Date()) return

  // 触发充值
  await Billing.reload()
}
```

### 6.2 充值流程

```typescript
export const reload = async () => {
  // 1. 获取计费信息
  const billing = await Database.use((tx) =>
    tx.select({
      customerID: BillingTable.customerID,
      paymentMethodID: BillingTable.paymentMethodID,
      reloadAmount: BillingTable.reloadAmount,
    })
    .from(BillingTable)
    .where(eq(BillingTable.workspaceID, Actor.workspace()))
    .then((rows) => rows[0]),
  )

  // 2. 创建 Stripe 发票
  const draft = await Billing.stripe().invoices.create({
    customer: customerID!,
    auto_advance: false,
    default_payment_method: paymentMethodID!,
    collection_method: "charge_automatically",
    currency: "usd",
  })

  // 3. 添加信用项
  await Billing.stripe().invoiceItems.create({
    amount: amountInCents,
    currency: "usd",
    customer: customerID!,
    invoice: draft.id!,
    description: "opencode credits",
  })

  // 4. 添加处理费
  await Billing.stripe().invoiceItems.create({
    amount: calculateFeeInCents(amountInCents),
    currency: "usd",
    customer: customerID!,
    invoice: draft.id!,
    description: "processing fee",
  })

  // 5. 最终化并支付
  await Billing.stripe().invoices.finalizeInvoice(draft.id!)
  await Billing.stripe().invoices.pay(draft.id!, {
    off_session: true,
    payment_method: paymentMethodID!,
  })
}
```

---

## 7. 关键常数

```typescript
// 充值配置
export const RELOAD_AMOUNT = 20              // 默认充值金额（美元）
export const RELOAD_AMOUNT_MIN = 10          // 最小充值金额（美元）
export const RELOAD_TRIGGER = 5              // 充值触发值（美元）
export const RELOAD_TRIGGER_MIN = 5          // 最小触发值（美元）

// 处理费计算
// 公式：x = total - (total * 0.044 + 0.30)
// 反推：(x + 0.30) / 0.956 = total
// 处理费 = total * 0.044 + 0.30
export const calculateFeeInCents = (x: number) => {
  return Math.round(((x + 30) / 0.956) * 0.044 + 30)
}

// LLM 输出限制
export const OUTPUT_TOKEN_MAX = Flag.OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX || 32_000
```

---

## 8. 与 Leon 的集成建议

### 8.1 可直接复用的代码

1. **Token 计算逻辑** (`Session.getUsage()`)
   - 缓存 token 处理
   - 推理 token 处理
   - 200K+ 特殊定价

2. **Provider 适配器模式**
   - 定义通用接口
   - 实现 provider 特定的 usage 解析

3. **成本计算** (`trackUsage()`)
   - 分项成本计算
   - 指标记录

### 8.2 需要调整的部分

1. **数据库存储**
   - Leon 使用 SQLite，OpenCode 使用 MySQL
   - 需要调整 SQL 语法

2. **计费模式**
   - Leon 可能不需要订阅模式
   - 可简化为余额模式

3. **自动充值**
   - Leon 可能不需要 Stripe 集成
   - 可简化为手动充值

---

## 9. 测试建议

### 9.1 单元测试

```typescript
// 测试 token 计算
test("Session.getUsage - OpenAI with cache", () => {
  const result = Session.getUsage({
    model: gpt4Model,
    usage: {
      inputTokens: 1000,
      outputTokens: 500,
      cachedInputTokens: 100,
    },
    metadata: { openai: {} },
  })
  
  expect(result.tokens.input).toBe(900)  // 1000 - 100
  expect(result.tokens.cache.read).toBe(100)
})

// 测试 provider 适配
test("OpenAI normalizeUsage", () => {
  const result = openaiHelper({}).normalizeUsage({
    input_tokens: 1000,
    output_tokens: 500,
    input_tokens_details: { cached_tokens: 100 },
    output_tokens_details: { reasoning_tokens: 50 },
  })
  
  expect(result.inputTokens).toBe(900)
  expect(result.cacheReadTokens).toBe(100)
  expect(result.reasoningTokens).toBe(50)
})
```

### 9.2 集成测试

```typescript
// 测试完整的计费流程
test("trackUsage - subscription billing", async () => {
  const costInfo = await trackUsage(
    authInfo,
    modelInfo,
    providerInfo,
    "subscription",
    usageInfo,
  )
  
  // 验证 usage 记录
  const usage = await db.select().from(UsageTable).where(...)
  expect(usage).toHaveLength(1)
  expect(usage[0].inputTokens).toBe(usageInfo.inputTokens)
  
  // 验证订阅使用量更新
  const subscription = await db.select().from(SubscriptionTable).where(...)
  expect(subscription[0].fixedUsage).toBeGreaterThan(0)
})
```

---

## 10. 性能考虑

### 10.1 数据库查询优化

```typescript
// 使用索引加速查询
const usages = await db
  .select()
  .from(UsageTable)
  .where(
    and(
      eq(UsageTable.workspaceID, workspaceID),
      gte(UsageTable.timeCreated, startTime),
      lte(UsageTable.timeCreated, endTime),
    ),
  )
  .orderBy(desc(UsageTable.timeCreated))
  .limit(100)
```

### 10.2 批量操作

```typescript
// 使用事务批量更新
await Database.transaction(async (tx) => {
  await tx.insert(UsageTable).values(usageRecord)
  await tx.update(KeyTable).set({ timeUsed: sql`now()` }).where(...)
  await tx.update(BillingTable).set({ balance: ... }).where(...)
})
```

---

## 11. 监控和告警

### 11.1 关键指标

```typescript
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

### 11.2 告警规则

- 单个请求成本异常高（> $10）
- 缓存命中率过低（< 10%）
- 推理 token 占比过高（> 50%）
- 充值失败

