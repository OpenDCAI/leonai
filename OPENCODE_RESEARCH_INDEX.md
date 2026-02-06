# OpenCode Prompt Caching 研究索引

**研究时间**: 2026-02-07  
**研究员**: 邵云  
**项目**: OpenCode (TypeScript/Node.js)  
**总文档大小**: 48KB (3 份文档)

---

## 文档导航

### 1. OPENCODE_PROMPT_CACHING_ANALYSIS.md (18KB)

**完整的技术分析文档**，包含 10 个章节：

| 章节 | 内容 | 关键代码 |
|------|------|---------|
| 1. 架构概览 | 分层设计、关键特点 | - |
| 2. 核心实现细节 | 缓存标记放置、OpenAI 配置、多模型差异、成本模型、统计追踪 | applyCaching(), options() |
| 3. 缓存策略配置 | 消息结构优化、缓存启用条件 | llm.ts L82-97 |
| 4. 不支持模型降级 | 检测机制、降级行为 | transform.ts L171-209 |
| 5. 实现对比 | Anthropic vs OpenAI | anthropic.ts, openai.ts |
| 6. 关键代码路径 | 消息处理流程、成本计算流程 | - |
| 7. 测试覆盖 | 缓存键测试、缓存控制测试 | transform.test.ts |
| 8. 配置最佳实践 | 启用缓存、成本优化 | - |
| 9. 已知限制 | 不支持的 provider、缓存失效场景、大小限制 | - |
| 10. 总结 | 核心原则、关键文件、与 Leon 对比 | - |

**适合场景**：
- 深入理解 OpenCode 缓存架构
- 学习多模型缓存差异处理
- 参考 Leon 的缓存实现设计

---

### 2. OPENCODE_CACHING_CODE_EXAMPLES.md (20KB)

**代码示例和实现细节文档**，包含 8 个章节：

| 章节 | 内容 | 代码行数 |
|------|------|---------|
| 1. 完整消息处理流程 | LLM 层入口、ProviderTransform 层处理 | 100+ |
| 2. Anthropic 缓存实现 | 缓存标记注入、使用统计解析、Bedrock 特殊处理 | 150+ |
| 3. OpenAI 缓存实现 | promptCacheKey 配置、使用统计解析 | 100+ |
| 4. 成本计算示例 | 模型成本定义、成本计算逻辑 | 50+ |
| 5. 测试用例 | 缓存键测试、缓存控制测试 | 100+ |
| 6. 实际使用场景 | 长上下文场景、多轮对话场景 | 50+ |
| 7. 调试技巧 | 查看缓存标记、查看缓存统计 | 30+ |
| 8. 常见问题 | Q&A 解答 | - |

**适合场景**：
- 快速上手 OpenCode 缓存实现
- 复制粘贴代码示例
- 调试缓存相关问题
- 理解成本计算逻辑

---

### 3. OPENCODE_CACHING_SUMMARY.md (10KB)

**研究总结和快速参考文档**，包含 14 个章节：

| 章节 | 内容 | 关键信息 |
|------|------|---------|
| 1. 核心发现 | 架构设计、关键特点 | 分层缓存架构 |
| 2. 多模型缓存差异 | Anthropic vs OpenAI | 显式 vs 隐式 |
| 3. 缓存标记放置策略 | 为什么只在前 2 个 + 最后 2 个 | 成本优化 |
| 4. OpenAI promptCacheKey 机制 | 工作原理、与 Anthropic 对比 | sessionID 自动处理 |
| 5. 缓存成本模型 | 模型定义、成本计算示例 | 节省 43% 的成本 |
| 6. 缓存使用统计追踪 | Anthropic 统计、OpenAI 统计、规范化 | 统一格式 |
| 7. 不支持 Provider 降级 | 检测机制、降级行为 | 静默跳过 |
| 8. 消息结构优化 | 系统提示 2 部分结构 | 缓存稳定性 |
| 9. 关键文件清单 | 9 个关键文件 | 行数 + 职责 |
| 10. 与 Leon 对比 | 架构对比、可借鉴设计 | 5 个维度 |
| 11. 实现建议 | 对 Leon 的参考 | 4 个建议 |
| 12. 常见问题解答 | 4 个常见问题 | Q&A |
| 13. 研究成果 | 文档清单、关键代码片段 | 3 份文档 |
| 14. 后续研究方向 | 4 个研究方向 | 缓存效率、多 Agent 等 |

**适合场景**：
- 快速了解 OpenCode 缓存实现
- 查找特定问题的答案
- 与 Leon 进行架构对比
- 获取实现建议

---

## 快速查询表

### 按问题查找

| 问题 | 文档 | 章节 |
|------|------|------|
| OpenCode 缓存架构是什么？ | ANALYSIS | 1 |
| Anthropic 和 OpenAI 缓存有什么区别？ | ANALYSIS | 5 / SUMMARY | 2 |
| 如何放置缓存标记？ | ANALYSIS | 2.1 / EXAMPLES | 1 |
| OpenAI 的 promptCacheKey 怎么用？ | ANALYSIS | 2.2 / SUMMARY | 4 |
| 缓存成本怎么计算？ | ANALYSIS | 2.4 / EXAMPLES | 4 / SUMMARY | 5 |
| 如何追踪缓存使用统计？ | ANALYSIS | 2.5 / EXAMPLES | 2-3 |
| 不支持的 provider 怎么处理？ | ANALYSIS | 4 / SUMMARY | 7 |
| 有哪些测试用例？ | ANALYSIS | 7 / EXAMPLES | 5 |
| 最佳实践是什么？ | ANALYSIS | 8 / SUMMARY | 11 |
| 与 Leon 有什么区别？ | SUMMARY | 10 |
| 怎么调试缓存问题？ | EXAMPLES | 7 |
| 常见问题怎么解决？ | EXAMPLES | 8 / SUMMARY | 12 |

### 按文件查找

| 文件 | 文档 | 章节 |
|------|------|------|
| transform.ts | ANALYSIS | 2.1, 2.2, 2.3 |
| llm.ts | ANALYSIS | 3.1 |
| models.ts | ANALYSIS | 2.4 |
| provider.ts | ANALYSIS | 2.4 |
| anthropic.ts | ANALYSIS | 5.1 / EXAMPLES | 2 |
| openai.ts | ANALYSIS | 5.2 / EXAMPLES | 3 |
| message.ts | ANALYSIS | 2.5 |
| transform.test.ts | ANALYSIS | 7 / EXAMPLES | 5 |

### 按技术概念查找

| 概念 | 文档 | 章节 |
|------|------|------|
| cache_control | ANALYSIS | 2.1 / EXAMPLES | 2 |
| cacheControl | ANALYSIS | 2.1 / EXAMPLES | 2 |
| cachePoint | ANALYSIS | 2.1 / EXAMPLES | 2 |
| promptCacheKey | ANALYSIS | 2.2 / SUMMARY | 4 |
| ephemeral | ANALYSIS | 2.1 / EXAMPLES | 2 |
| breakpoint | ANALYSIS | 2.1 / SUMMARY | 3 |
| cache_read | ANALYSIS | 2.4 / EXAMPLES | 4 |
| cache_write | ANALYSIS | 2.4 / EXAMPLES | 4 |
| cache_creation_input_tokens | ANALYSIS | 2.5 / EXAMPLES | 2 |
| cache_read_input_tokens | ANALYSIS | 2.5 / EXAMPLES | 2 |
| applyCaching | ANALYSIS | 2.1 / EXAMPLES | 1 |
| normalizeUsage | ANALYSIS | 2.5 / EXAMPLES | 2-3 |

---

## 关键代码位置速查

### 缓存标记注入

```
文件: /packages/opencode/src/provider/transform.ts
函数: applyCaching()
行数: 171-209
文档: ANALYSIS 2.1, EXAMPLES 1.2, SUMMARY 3
```

### OpenAI 缓存配置

```
文件: /packages/opencode/src/provider/transform.ts
函数: options()
行数: 620-670
文档: ANALYSIS 2.2, EXAMPLES 3.1, SUMMARY 4
```

### 系统提示优化

```
文件: /packages/opencode/src/session/llm.ts
行数: 82-97
文档: ANALYSIS 3.1, EXAMPLES 1.1, SUMMARY 8
```

### Anthropic 缓存解析

```
文件: /packages/console/app/src/routes/zen/util/provider/anthropic.ts
行数: 139-180
文档: ANALYSIS 2.5, EXAMPLES 2.2, SUMMARY 6
```

### OpenAI 缓存解析

```
文件: /packages/console/app/src/routes/zen/util/provider/openai.ts
行数: 3-62
文档: ANALYSIS 2.5, EXAMPLES 3.2, SUMMARY 6
```

### 缓存成本定义

```
文件: /packages/opencode/src/provider/models.ts
行数: 36-50
文档: ANALYSIS 2.4, EXAMPLES 4.1, SUMMARY 5
```

### 缓存测试用例

```
文件: /packages/opencode/test/provider/transform.test.ts
行数: 6-1327
文档: ANALYSIS 7, EXAMPLES 5
```

---

## 核心概念速查

### 缓存类型

| 类型 | Provider | 字段 | 值 |
|------|----------|------|-----|
| ephemeral | Anthropic | cacheControl | { type: "ephemeral" } |
| ephemeral | OpenRouter | cacheControl | { type: "ephemeral" } |
| ephemeral | OpenAI Compatible | cache_control | { type: "ephemeral" } |
| ephemeral | Copilot | copilot_cache_control | { type: "ephemeral" } |
| default | Bedrock | cachePoint | { type: "default" } |
| auto | OpenAI | promptCacheKey | sessionID |

### 成本系数

| 操作 | Anthropic | OpenAI |
|------|-----------|--------|
| 输入 | 1.0x | 1.0x |
| 输出 | 1.0x | 1.0x |
| 缓存写入 | 1.25x | - |
| 缓存读取 | 0.1x | 0.1x |

### 缓存 TTL

| Provider | TTL |
|----------|-----|
| Anthropic | 5 分钟或 1 小时 |
| OpenAI | 无限制 |
| Bedrock | 依赖 AWS 配置 |

---

## 学习路径建议

### 初级（快速了解）

1. 阅读 SUMMARY 第 1-4 章
2. 查看 EXAMPLES 第 1 章
3. 理解基本概念

**预计时间**: 15 分钟

### 中级（深入理解）

1. 阅读 ANALYSIS 第 1-5 章
2. 阅读 EXAMPLES 第 2-3 章
3. 查看测试用例

**预计时间**: 1 小时

### 高级（完全掌握）

1. 阅读所有 3 份文档
2. 研究所有代码片段
3. 运行测试用例
4. 实现自己的缓存中间件

**预计时间**: 3-4 小时

---

## 与 Leon 的对接点

### 可直接借鉴的设计

1. **ProviderTransform 层的分层设计**
   - 文档: ANALYSIS 1, SUMMARY 10
   - 建议: 在 Leon 中创建 PromptCachingMiddleware

2. **Provider-specific 配置**
   - 文档: ANALYSIS 2.3, SUMMARY 2
   - 建议: 支持不同 provider 的缓存差异

3. **成本模型集成**
   - 文档: ANALYSIS 2.4, EXAMPLES 4, SUMMARY 5
   - 建议: 在 TokenMonitor 中追踪缓存成本

4. **统计规范化**
   - 文档: ANALYSIS 2.5, SUMMARY 6
   - 建议: 统一不同 provider 的统计格式

5. **降级策略**
   - 文档: ANALYSIS 4, SUMMARY 7
   - 建议: 不支持的 provider 静默跳过

---

## 文档维护信息

| 项目 | 信息 |
|------|------|
| 研究时间 | 2026-02-07 |
| 研究员 | 邵云 |
| 项目 | OpenCode (TypeScript/Node.js) |
| 源代码位置 | /Users/apple/Documents/Project/邵云-moltbot研究/repos/opencode/ |
| 文档位置 | /Users/apple/Desktop/project/v1/文稿/project/leon/ |
| 总文档大小 | 48KB |
| 文档数量 | 3 份 |
| 代码片段数 | 50+ |
| 关键文件数 | 9 |

---

## 快速参考卡片

### Anthropic 缓存流程

```
消息 → applyCaching() → 添加 cache_control → API 调用
                        ↓
                    前 2 个 system
                    最后 2 个消息
```

### OpenAI 缓存流程

```
消息 → options() → 设置 promptCacheKey → API 调用
                   ↓
                sessionID 自动处理
```

### 成本计算

```
总成本 = input_cost + output_cost + cache_read_cost + cache_write_cost
       = input * cost.input 
         + output * cost.output 
         + cache_read * cost.cache.read 
         + cache_write * cost.cache.write
```

---

**文档完成时间**: 2026-02-07  
**最后更新**: 2026-02-07

