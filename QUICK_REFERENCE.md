# OpenCode Token 追踪 - 快速参考

## 核心概念

### Token 分项（6 项）

```
输入 token (input)
  ↓ 排除缓存读写
  
输出 token (output)
  ↓ 排除推理 token
  
推理 token (reasoning)
  ↓ 仅 o1/o3 模型
  
缓存读 token (cache.read)
  ↓ 缓存命中
  
缓存写 5m (cache.write_5m)
  ↓ 5 分钟缓存
  
缓存写 1h (cache.write_1h)
  ↓ 1 小时缓存
```

### 成本计算公式

```
成本 = Σ(token_i × price_i / 1,000,000)

其中：
- token_i：第 i 项的 token 数
- price_i：第 i 项的单价（美元/百万 token）
- 结果单位：美元
```

### 单位转换

```
美元 × 100 = cent
cent × 10,000 = microcents（数据库存储单位）
```

---

## 关键代码位置

### 1. Token 计算

**文件：** `/packages/opencode/src/session/index.ts`

**函数：** `Session.getUsage()`

**输入：**
```typescript
{
  model: Provider.Model,
  usage: LanguageModelUsage,
  metadata?: ProviderMetadata,
}
```

**输出：**
```typescript
{
  cost: number,
  tokens: {
    input: number,
    output: number,
    reasoning: number,
    cache: { read: number, write: number },
  }
}
```

### 2. Provider 适配

**文件：** `/packages/console/app/routes/zen/util/provider/`

**关键函数：** `normalizeUsage()`

**作用：** 将 provider 特定的 usage 格式转换为统一的 `UsageInfo`

### 3. 网关层计费

**文件：** `/packages/console/app/routes/zen/util/handler.ts`

**函数：** `trackUsage()`

**作用：** 
- 计算分项成本
- 记录 usage 到数据库
- 更新账户余额/订阅

### 4. 数据库存储

**文件：** `/packages/console/core/src/schema/billing.sql.ts`

**表：** `UsageTable`

**字段：**
```typescript
{
  model: string,
  provider: string,
  inputTokens: int,
  outputTokens: int,
  reasoningTokens?: int,
  cacheReadTokens?: int,
  cacheWrite5mTokens?: int,
  cacheWrite1hTokens?: int,
  cost: bigint,  // microcents
  keyID: string,
  enrichment?: { plan: "sub" },
}
```

---

## Provider 差异速查表

### OpenAI

```typescript
// 缓存处理
inputTokens = usage.input_tokens - (usage.input_tokens_details?.cached_tokens ?? 0)
cacheReadTokens = usage.input_tokens_details?.cached_tokens

// 推理 token
reasoningTokens = usage.output_tokens_details?.reasoning_tokens
outputTokens = usage.output_tokens - (reasoningTokens ?? 0)
```

### Anthropic

```typescript
// 缓存处理（已排除）
inputTokens = usage.input_tokens
cacheReadTokens = usage.cache_read_input_tokens
cacheWrite5mTokens = usage.cache_creation?.ephemeral_5m_input_tokens
cacheWrite1hTokens = usage.cache_creation?.ephemeral_1h_input_tokens

// 推理 token（不支持）
reasoningTokens = undefined
```

### Google

```typescript
// 类似 OpenAI
inputTokens = usage.input_tokens - (usage.input_tokens_details?.cached_tokens ?? 0)
cacheReadTokens = usage.input_tokens_details?.cached_tokens
```

---

## 成本计算示例

### 场景：OpenAI GPT-4 请求

```
模型定价：
  input: $0.003 / 百万 token
  output: $0.006 / 百万 token
  cache_read: $0.0015 / 百万 token

请求结果：
  inputTokens: 1,000
  outputTokens: 500
  cacheReadTokens: 100

成本计算：
  inputCost = 1,000 × 0.003 / 1,000,000 = $0.000003
  outputCost = 500 × 0.006 / 1,000,000 = $0.000003
  cacheReadCost = 100 × 0.0015 / 1,000,000 = $0.00000015
  
  totalCost = $0.000006015 ≈ $0.000006
```

### 场景：200K+ Token 特殊定价

```
模型定价：
  normal: { input: $0.003, output: $0.006 }
  over200k: { input: $0.0015, output: $0.003 }

请求结果：
  inputTokens: 150,000
  cacheReadTokens: 100,000
  总 token: 250,000 > 200,000

应用定价：
  使用 over200k 定价
  inputCost = 150,000 × 0.0015 / 1,000,000 = $0.000225
  outputCost = 500 × 0.003 / 1,000,000 = $0.0000015
```

---

## 流程图

### 非流式请求

```
API 请求
  ↓
获取响应 JSON
  ↓
提取 usage
  ↓
Provider 适配 (normalizeUsage)
  ↓
规范化为 UsageInfo
  ↓
计费 (trackUsage)
  ├─ 计算分项成本
  ├─ 记录 usage 到数据库
  ├─ 更新账户余额/订阅
  └─ 返回成本信息
  ↓
自动充值 (reload)
  ├─ 检查余额
  ├─ 触发充值（如需要）
  └─ 返回响应
```

### 流式请求

```
API 请求
  ↓
创建 usage 解析器
  ↓
流式接收数据
  ├─ 解析每个 chunk
  ├─ 累积 usage 信息
  └─ 转发给客户端
  ↓
流结束
  ↓
获取最终 usage
  ↓
计费 (trackUsage)
  ↓
自动充值 (reload)
```

---

## 常见问题

### Q1: 为什么要排除缓存 token？

**A:** 缓存 token 的成本更低，需要单独计费。排除后可以准确计算非缓存部分的成本。

### Q2: 推理 token 如何计费？

**A:** 推理 token 按输出价格计费（与输出 token 相同）。

### Q3: 200K+ 特殊定价如何判断？

**A:** 当 `inputTokens + cacheReadTokens > 200,000` 时，使用特殊定价。

### Q4: 为什么使用 Decimal.js？

**A:** 避免浮点精度问题。例如 `0.003 * 1000000 * 100` 可能得到 `299999.99999999994`。

### Q5: 订阅和余额计费有什么区别？

**A:** 
- 订阅：固定周期 + 滚动窗口，有使用量限制
- 余额：直接扣费，余额不足时自动充值

---

## 集成检查清单

- [ ] 复用 `Session.getUsage()` 的 token 计算逻辑
- [ ] 实现 Provider 适配器模式
- [ ] 添加 6 项 token 分项追踪
- [ ] 实现分项成本计算
- [ ] 使用 Decimal.js 精确计算
- [ ] 添加详细的指标记录
- [ ] 实现 usage 数据库存储
- [ ] 支持多种计费模式
- [ ] 添加单元测试
- [ ] 添加集成测试

---

## 性能优化建议

1. **数据库索引**
   - `(workspaceID, timeCreated)` 用于时间范围查询
   - `workspaceID` 用于快速查询

2. **批量操作**
   - 使用事务批量更新
   - 减少数据库往返

3. **缓存策略**
   - 缓存模型成本信息
   - 缓存 provider 配置

4. **异步处理**
   - 异步记录指标
   - 异步触发充值

---

## 监控指标

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

---

## 相关文档

- `opencode_token_billing_analysis.md` - 完整架构分析
- `opencode_implementation_details.md` - 实现细节
- `RESEARCH_SUMMARY.md` - 研究总结

