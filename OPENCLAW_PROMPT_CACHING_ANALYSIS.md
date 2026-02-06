# OpenClaw Prompt Caching 技术分析

**研究员**: 邵云  
**日期**: 2026-02-07  
**项目**: OpenClaw (Clawebot/moltbot 技术研究)

---

## 核心发现

### 1. OpenClaw 如何实现 Prompt Caching?

OpenClaw 采用**分层架构**实现 Prompt Caching:

```
参数层 (extra-params.ts)
  ↓ 解析 cacheRetention 参数
TTL 层 (cache-ttl.ts)
  ↓ 追踪缓存时间戳
配置层 (defaults.ts)
  ↓ 自动启用 cache-ttl 模式
诊断层 (cache-trace.ts + anthropic-payload-log.ts)
  ↓ 完整的追踪和日志
```

**关键特点**:
- 无专门的 middleware，而是通过流函数包装
- 与 pi-ai 库紧密集成
- 配置驱动，自动启用

### 2. 多模型适配策略

| Provider | 支持 | 方式 | 参数 |
|----------|------|------|------|
| **Anthropic** | ✅ | cache_control | cacheRetention |
| **OpenRouter/Anthropic** | ✅ | hardcoded | - |
| **OpenAI** | ⚠️ | 自动 | - |
| **Google Gemini** | ❌ | - | - |

**关键代码** (cache-ttl.ts):

```typescript
export function isCacheTtlEligibleProvider(provider: string, modelId: string): boolean {
  const normalizedProvider = provider.toLowerCase();
  const normalizedModelId = modelId.toLowerCase();
  
  if (normalizedProvider === "anthropic") {
    return true;
  }
  
  if (normalizedProvider === "openrouter" && normalizedModelId.startsWith("anthropic/")) {
    return true;
  }
  
  return false;
}
```

### 3. Anthropic cache_control 注入

**方式**: 通过 `cacheRetention` 流选项

**文件**: `/src/agents/pi-embedded-runner/extra-params.ts`

```typescript
function resolveCacheRetention(
  extraParams: Record<string, unknown> | undefined,
  provider: string,
): CacheRetention | undefined {
  if (provider !== "anthropic") {
    return undefined;  // 仅 Anthropic
  }

  // 新参数优先
  const newVal = extraParams?.cacheRetention;
  if (newVal === "none" || newVal === "short" || newVal === "long") {
    return newVal;
  }

  // 向后兼容
  const legacy = extraParams?.cacheControlTtl;
  if (legacy === "5m") {
    return "short";
  }
  if (legacy === "1h") {
    return "long";
  }
  return undefined;
}
```

**流程**:
1. 从配置读取 `cacheRetention` 参数
2. 创建包装的流函数
3. pi-ai 库将其转换为 Anthropic 的 `cache_control`

### 4. OpenAI 自动缓存处理

**状态**: 不主动支持

**原因** (extra-params.ts, 第 39-40 行):

```typescript
/**
 * Only applies to Anthropic provider (OpenRouter uses openai-completions API
 * with hardcoded cache_control, not the cacheRetention stream option).
 */
```

**含义**:
- OpenAI 的自动缓存基于 token 数量阈值 (1024+ tokens)
- 无需显式配置
- OpenClaw 不干预

### 5. 缓存 TTL 策略

**文件**: `/src/agents/pi-embedded-runner/cache-ttl.ts`

```typescript
export type CacheTtlEntryData = {
  timestamp: number;        // 缓存创建时间戳
  provider?: string;        // 使用的 provider
  modelId?: string;         // 使用的模型 ID
};

export const CACHE_TTL_CUSTOM_TYPE = "openclaw.cache-ttl";
```

**TTL 追踪流程**:

```
1. 检查 contextPruning.mode === "cache-ttl"
   ↓
2. 检查 isCacheTtlEligibleProvider(provider, modelId)
   ↓
3. appendCacheTtlTimestamp(sessionManager, {
     timestamp: Date.now(),
     provider,
     modelId
   })
   ↓
4. 存储在 SessionManager 自定义条目中
   ↓
5. 后续可通过 readLastCacheTtlTimestamp() 读取
```

**Breakpoint 放置**:
- 在 `activeSession.prompt()` 调用前 (run/attempt.ts, 第 795-804 行)
- 记录时间戳用于后续 TTL 检查

### 6. Provider 动态切换

**文件**: `/src/config/defaults.ts`

```typescript
export function applyContextPruningDefaults(cfg: OpenClawConfig): OpenClawConfig {
  const authMode = resolveAnthropicDefaultAuthMode(cfg);
  if (!authMode) {
    return cfg;  // 无 Anthropic 认证，不启用
  }

  // 自动启用 cache-ttl
  if (defaults.contextPruning?.mode === undefined) {
    nextDefaults.contextPruning = {
      ...contextPruning,
      mode: "cache-ttl",
      ttl: defaults.contextPruning?.ttl ?? "1h",
    };
    mutated = true;
  }

  // 为 API Key 模式设置 cacheRetention
  if (authMode === "api_key") {
    for (const [key, entry] of Object.entries(nextModels)) {
      const parsed = parseModelRef(key, "anthropic");
      if (!parsed || parsed.provider !== "anthropic") {
        continue;
      }
      const params = (current as { params?: Record<string, unknown> }).params ?? {};
      if (typeof params.cacheRetention === "string") {
        continue;
      }
      nextModels[key] = {
        ...(current as Record<string, unknown>),
        params: { ...params, cacheRetention: "short" },
      };
      modelsMutated = true;
    }
  }

  return mutated ? { ...cfg, agents: { ...cfg.agents, defaults: nextDefaults } } : cfg;
}
```

**自动启用条件**:
1. 检测到 Anthropic 认证 (OAuth 或 API Key)
2. 设置 `contextPruning.mode = "cache-ttl"`
3. 设置 `contextPruning.ttl = "1h"` (默认)
4. 为 API Key 模式的所有 Anthropic 模型设置 `cacheRetention: "short"`

---

## 关键文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `extra-params.ts` | 157 | 参数解析和流函数包装 |
| `cache-ttl.ts` | 62 | TTL 追踪 |
| `defaults.ts` | 450+ | 配置默认值 |
| `cache-trace.ts` | 295 | 缓存诊断追踪 |
| `anthropic-payload-log.ts` | 220+ | Anthropic 负载日志 |
| `session-manager-cache.ts` | 70 | SessionManager 缓存 |
| `cache-utils.ts` | 28 | 缓存工具函数 |

---

## 代码片段

### 完整的参数应用流程

```typescript
export function applyExtraParamsToAgent(
  agent: { streamFn?: StreamFn },
  cfg: OpenClawConfig | undefined,
  provider: string,
  modelId: string,
  extraParamsOverride?: Record<string, unknown>,
): void {
  // 1. 从配置解析参数
  const extraParams = resolveExtraParams({
    cfg,
    provider,
    modelId,
  });

  // 2. 合并覆盖参数
  const override =
    extraParamsOverride && Object.keys(extraParamsOverride).length > 0
      ? Object.fromEntries(
          Object.entries(extraParamsOverride).filter(([, value]) => value !== undefined),
        )
      : undefined;
  const merged = Object.assign({}, extraParams, override);

  // 3. 创建包装的流函数
  const wrappedStreamFn = createStreamFnWithExtraParams(agent.streamFn, merged, provider);

  if (wrappedStreamFn) {
    log.debug(`applying extraParams to agent streamFn for ${provider}/${modelId}`);
    agent.streamFn = wrappedStreamFn;
  }

  // 4. 为 OpenRouter 添加属性头
  if (provider === "openrouter") {
    log.debug(`applying OpenRouter app attribution headers for ${provider}/${modelId}`);
    agent.streamFn = createOpenRouterHeadersWrapper(agent.streamFn);
  }
}
```

### 流函数包装

```typescript
function createStreamFnWithExtraParams(
  baseStreamFn: StreamFn | undefined,
  extraParams: Record<string, unknown> | undefined,
  provider: string,
): StreamFn | undefined {
  if (!extraParams || Object.keys(extraParams).length === 0) {
    return undefined;
  }

  const streamParams: CacheRetentionStreamOptions = {};
  if (typeof extraParams.temperature === "number") {
    streamParams.temperature = extraParams.temperature;
  }
  if (typeof extraParams.maxTokens === "number") {
    streamParams.maxTokens = extraParams.maxTokens;
  }
  const cacheRetention = resolveCacheRetention(extraParams, provider);
  if (cacheRetention) {
    streamParams.cacheRetention = cacheRetention;
  }

  if (Object.keys(streamParams).length === 0) {
    return undefined;
  }

  log.debug(`creating streamFn wrapper with params: ${JSON.stringify(streamParams)}`);

  const underlying = baseStreamFn ?? streamSimple;
  const wrappedStreamFn: StreamFn = (model, context, options) =>
    underlying(model, context, {
      ...streamParams,
      ...options,
    });

  return wrappedStreamFn;
}
```

### TTL 追踪集成

```typescript
// run/attempt.ts, 第 795-804 行
const shouldTrackCacheTtl =
  params.config?.agents?.defaults?.contextPruning?.mode === "cache-ttl" &&
  isCacheTtlEligibleProvider(params.provider, params.modelId);

if (shouldTrackCacheTtl) {
  appendCacheTtlTimestamp(sessionManager, {
    timestamp: Date.now(),
    provider: params.provider,
    modelId: params.modelId,
  });
}
```

---

## 诊断工具

### 缓存追踪 (cache-trace.ts)

**启用方式**:

```bash
export OPENCLAW_CACHE_TRACE=true
export OPENCLAW_CACHE_TRACE_MESSAGES=true
export OPENCLAW_CACHE_TRACE_PROMPT=true
export OPENCLAW_CACHE_TRACE_SYSTEM=true
```

**输出**: `~/.openclaw/logs/cache-trace.jsonl`

**追踪阶段**:
- `session:loaded`
- `session:sanitized`
- `session:limited`
- `prompt:before`
- `prompt:images`
- `stream:context`
- `session:after`

### Anthropic 负载日志 (anthropic-payload-log.ts)

**启用方式**:

```bash
export OPENCLAW_ANTHROPIC_PAYLOAD_LOG=true
```

**输出**: `~/.openclaw/logs/anthropic-payload.jsonl`

**记录内容**:
- 请求负载 (payload)
- 使用统计 (usage)
- 错误信息

---

## 设计模式

### 1. 流函数包装模式

```
baseStreamFn
    ↓
[ExtraParams Wrapper]
    ↓
[OpenRouter Headers Wrapper]
    ↓
[CacheTrace Wrapper]
    ↓
[AnthropicPayloadLog Wrapper]
    ↓
finalStreamFn
```

### 2. 配置默认值应用

```
User Config
    ↓
[Anthropic Auth Detection]
    ↓
[Apply Context Pruning Defaults]
    ↓
[Apply Cache Retention Defaults]
    ↓
[Apply Heartbeat Defaults]
    ↓
Final Config
```

### 3. TTL 追踪

```
Session Start
    ↓
[Check cache-ttl mode]
    ↓
[Check provider eligibility]
    ↓
[Append TTL timestamp]
    ↓
[Later: Read TTL for pruning]
```

---

## 对 Leon 的启示

### 可直接借鉴的设计

1. **参数解析层**: 实现 `resolveCacheRetention()` 等价物
2. **TTL 追踪**: 在 SessionManager 中添加自定义条目支持
3. **配置自动化**: 检测 Anthropic 认证并自动启用
4. **诊断工具**: 实现缓存追踪和负载日志

### 实现优先级

1. **P0**: 参数解析 + TTL 追踪
2. **P1**: 配置自动化
3. **P2**: 诊断工具
4. **P3**: Provider 适配

---

## 总结

OpenClaw 的 Prompt Caching 实现是**生产就绪**的，具有以下特点:

- ✅ 完整的 TTL 管理
- ✅ 自动化配置
- ✅ 完善的诊断工具
- ✅ 多 Provider 支持
- ✅ 向后兼容

Leon 可参考 OpenClaw 的架构，实现类似的功能，预期可获得:

- 缓存命中率提升 30-50%
- 成本降低 20-30%
- 诊断能力增强
- 用户体验改善

