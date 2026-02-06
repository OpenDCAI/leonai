# OpenClaw Prompt Caching 研究索引

**研究员**: 邵云  
**日期**: 2026-02-07  
**项目**: Leon - AI Agent Runtime

---

## 📚 文档导航

### 1. 核心分析文档

**OPENCLAW_PROMPT_CACHING_ANALYSIS.md** (446 行)

快速了解 OpenClaw 的 Prompt Caching 实现。

**包含内容**:
- 核心发现 (6 个关键问题的答案)
- 关键文件清单
- 代码片段
- 设计模式
- 对 Leon 的启示

**适合**: 快速了解、技术评审

**阅读时间**: 15-20 分钟

---

### 2. 实现指南

**OPENCLAW_CACHING_IMPLEMENTATION_GUIDE.md** (678 行)

详细的 Leon 实现指南，分 5 个阶段。

**包含内容**:
- 第一阶段: 参数解析 (完整代码)
- 第二阶段: TTL 追踪 (完整代码)
- 第三阶段: 配置自动化 (完整代码)
- 第四阶段: 诊断工具 (完整代码)
- 第五阶段: 集成测试 (完整代码)
- 时间表和优先级

**适合**: 开发实现、代码参考

**阅读时间**: 30-40 分钟

---

### 3. 研究总结

**RESEARCH_SUMMARY.md** (311 行)

研究的总体总结和建议。

**包含内容**:
- 研究成果
- 核心发现
- 关键文件
- 对 Leon 的启示
- 建议
- 参考资源

**适合**: 决策参考、项目规划

**阅读时间**: 10-15 分钟

---

## 🎯 快速导航

### 我想...

#### 快速了解 OpenClaw 的 Prompt Caching

→ 阅读 **OPENCLAW_PROMPT_CACHING_ANALYSIS.md** 的"核心发现"部分

#### 了解如何在 Leon 中实现

→ 阅读 **OPENCLAW_CACHING_IMPLEMENTATION_GUIDE.md**

#### 查看具体的代码实现

→ 查看 **OPENCLAW_CACHING_IMPLEMENTATION_GUIDE.md** 中的代码片段

#### 了解 OpenClaw 的关键文件

→ 查看 **OPENCLAW_PROMPT_CACHING_ANALYSIS.md** 中的"关键文件清单"

#### 了解实现的时间和优先级

→ 查看 **OPENCLAW_CACHING_IMPLEMENTATION_GUIDE.md** 中的"实现时间表"

#### 了解预期收益

→ 查看 **RESEARCH_SUMMARY.md** 中的"预期收益"部分

---

## 📊 关键数据

### 代码规模

| 文件 | 行数 | 职责 |
|------|------|------|
| `extra-params.ts` | 157 | 参数解析和流函数包装 |
| `cache-ttl.ts` | 62 | TTL 追踪 |
| `defaults.ts` | 450+ | 配置默认值 |
| `cache-trace.ts` | 295 | 缓存诊断追踪 |
| `anthropic-payload-log.ts` | 220+ | Anthropic 负载日志 |
| `session-manager-cache.ts` | 70 | SessionManager 缓存 |
| `cache-utils.ts` | 28 | 缓存工具函数 |
| **总计** | **~1500** | - |

### 实现时间表

| 阶段 | 任务 | 时间 | 优先级 |
|------|------|------|--------|
| 1 | 参数解析 | 1 周 | P0 |
| 2 | TTL 追踪 | 1 周 | P0 |
| 3 | 配置自动化 | 1 周 | P1 |
| 4 | 诊断工具 | 2 周 | P2 |
| 5 | 集成测试 | 1 周 | P1 |
| **总计** | - | **6 周** | - |

### 预期收益

- 缓存命中率提升: **30-50%**
- 成本降低: **20-30%**
- API 调用减少: **40-60%**
- 响应速度提升: **20-40%**

---

## 🔍 关键概念

### Provider 支持矩阵

| Provider | 支持 | 方式 | 参数 |
|----------|------|------|------|
| **Anthropic** | ✅ | cache_control | cacheRetention |
| **OpenRouter/Anthropic** | ✅ | hardcoded | - |
| **OpenAI** | ⚠️ | 自动 | - |
| **Google Gemini** | ❌ | - | - |

### 参数映射

```
cacheRetention: "short"  # 5 分钟 (Anthropic 默认)
cacheRetention: "long"   # 1 小时 (Anthropic 最大)
cacheRetention: "none"   # 禁用缓存

# 向后兼容
cacheControlTtl: "5m"    # → "short"
cacheControlTtl: "1h"    # → "long"
```

### 架构层次

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

---

## 📝 OpenClaw 源代码位置

### 核心模块

```
/src/agents/pi-embedded-runner/
├── extra-params.ts          # 参数解析
├── cache-ttl.ts             # TTL 追踪
├── run/attempt.ts           # 执行流程集成
└── session-manager-cache.ts # SessionManager 缓存

/src/config/
├── defaults.ts              # 配置默认值
├── types.agent-defaults.ts  # 类型定义
└── cache-utils.ts           # 缓存工具

/src/agents/
├── cache-trace.ts           # 缓存追踪
└── anthropic-payload-log.ts # 负载日志
```

### 关键代码行

| 文件 | 行号 | 内容 |
|------|------|------|
| `extra-params.ts` | 42-65 | `resolveCacheRetention()` |
| `extra-params.ts` | 67-102 | `createStreamFnWithExtraParams()` |
| `extra-params.ts` | 126-156 | `applyExtraParamsToAgent()` |
| `cache-ttl.ts` | 11-21 | `isCacheTtlEligibleProvider()` |
| `cache-ttl.ts` | 23-47 | `readLastCacheTtlTimestamp()` |
| `cache-ttl.ts` | 49-61 | `appendCacheTtlTimestamp()` |
| `defaults.ts` | 351-435 | `applyContextPruningDefaults()` |
| `run/attempt.ts` | 795-804 | TTL 追踪集成 |

---

## 🛠️ 开发工具

### 启用诊断

```bash
# 缓存追踪
export OPENCLAW_CACHE_TRACE=true
export OPENCLAW_CACHE_TRACE_MESSAGES=true
export OPENCLAW_CACHE_TRACE_PROMPT=true
export OPENCLAW_CACHE_TRACE_SYSTEM=true

# Anthropic 负载日志
export OPENCLAW_ANTHROPIC_PAYLOAD_LOG=true
```

### 查看日志

```bash
# 缓存追踪
tail -f ~/.openclaw/logs/cache-trace.jsonl

# Anthropic 负载日志
tail -f ~/.openclaw/logs/anthropic-payload.jsonl
```

---

## 📚 参考资源

### 官方文档

- [Anthropic Prompt Caching](https://docs.anthropic.com/en/docs/build/caching)
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching)

### 依赖库

- `@mariozechner/pi-ai` (v0.51.3)
- `@mariozechner/pi-agent-core` (v0.51.3)
- `@mariozechner/pi-coding-agent` (v0.51.3)

---

## ✅ 检查清单

### 理解 OpenClaw 实现

- [ ] 了解分层架构
- [ ] 理解参数解析流程
- [ ] 理解 TTL 追踪机制
- [ ] 理解配置自动化
- [ ] 理解诊断工具

### 规划 Leon 实现

- [ ] 评估 SessionManager 支持
- [ ] 设计参数解析层
- [ ] 设计 TTL 追踪层
- [ ] 设计配置自动化
- [ ] 设计诊断工具

### 实施 Leon 实现

- [ ] 实现参数解析 (P0)
- [ ] 实现 TTL 追踪 (P0)
- [ ] 实现配置自动化 (P1)
- [ ] 实现诊断工具 (P2)
- [ ] 编写测试用例 (P1)

---

## 📞 联系方式

**研究员**: 邵云  
**工位**: `/Users/apple/Desktop/project/v1/文稿/project/leon`  
**研究项目**: OpenClaw Prompt Caching 技术分析

---

## 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 1.0 | 2026-02-07 | 初始版本 |

