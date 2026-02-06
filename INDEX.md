# OpenCode Token 追踪和计费研究 - 文档索引

## 文档概览

本研究包含 4 份详细文档，共 1,400+ 行代码和分析。

### 文档列表

| 文档 | 大小 | 行数 | 用途 |
|------|------|------|------|
| **QUICK_REFERENCE.md** | 8KB | 300+ | 快速查询，适合开发者 |
| **opencode_token_billing_analysis.md** | 16KB | 562 | 完整架构分析 |
| **opencode_implementation_details.md** | 16KB | 617 | 实现细节和代码示例 |
| **RESEARCH_SUMMARY.md** | 6KB | 244 | 研究总结和建议 |

---

## 快速导航

### 我想快速了解 OpenCode 的 token 追踪

→ 阅读 **QUICK_REFERENCE.md**

包含：
- 6 项 token 分项说明
- 成本计算公式
- Provider 差异速查表
- 成本计算示例
- 常见问题解答

### 我想深入理解整个架构

→ 阅读 **opencode_token_billing_analysis.md**

包含：
- 完整的架构分析
- 客户端层实现
- 网关层实现
- 数据库层实现
- 与 Leon 的对比
- 可借鉴的设计模式

### 我想了解具体的实现细节

→ 阅读 **opencode_implementation_details.md**

包含：
- 核心文件位置
- Token 计算的关键细节
- 成本计算的精确性保证
- Provider 适配层设计
- 网关层 usage 记录流程
- 数据库存储策略
- 自动充值机制
- 测试和性能建议

### 我想了解研究成果和建议

→ 阅读 **RESEARCH_SUMMARY.md**

包含：
- 关键发现总结
- 核心代码位置
- 与 Leon 的对比
- 实现建议（短/中/长期）
- 后续行动

---

## 核心概念速查

### Token 分项（6 项）

1. **输入 token** - 排除缓存读写
2. **输出 token** - 排除推理 token
3. **推理 token** - 仅 o1/o3 模型
4. **缓存读 token** - 缓存命中
5. **缓存写 5m** - 5 分钟缓存
6. **缓存写 1h** - 1 小时缓存

### 关键函数

| 函数 | 文件 | 功能 |
|------|------|------|
| `Session.getUsage()` | `packages/opencode/src/session/index.ts` | 计算 token 和成本 |
| `normalizeUsage()` | `packages/console/app/routes/zen/util/provider/` | 规范化 usage |
| `trackUsage()` | `packages/console/app/routes/zen/util/handler.ts` | 网关层计费 |

### 关键表

| 表 | 文件 | 用途 |
|----|------|------|
| `UsageTable` | `packages/console/core/src/schema/billing.sql.ts` | 记录每个请求的 token 和成本 |
| `BillingTable` | 同上 | 记录账户余额和计费信息 |
| `SubscriptionTable` | 同上 | 记录订阅使用量 |

---

## 学习路径

### 初级（了解基本概念）

1. 阅读 QUICK_REFERENCE.md 的"核心概念"部分
2. 了解 6 项 token 分项
3. 理解成本计算公式

**预计时间：** 15 分钟

### 中级（理解架构）

1. 阅读 RESEARCH_SUMMARY.md 的"关键发现"部分
2. 阅读 opencode_token_billing_analysis.md 的"概述"和"架构"部分
3. 查看核心代码位置

**预计时间：** 30 分钟

### 高级（掌握实现细节）

1. 阅读 opencode_implementation_details.md 的全部内容
2. 查看具体的代码片段
3. 理解 provider 适配层的设计
4. 学习测试和性能优化建议

**预计时间：** 1 小时

### 专家（集成到 Leon）

1. 阅读 RESEARCH_SUMMARY.md 的"实现建议"部分
2. 审查 Leon 现有的 token 计算逻辑
3. 制定集成计划
4. 准备测试用例

**预计时间：** 2-3 小时

---

## 关键数字

| 指标 | 值 |
|------|-----|
| Token 分项数 | 6 |
| Provider 支持数 | 10+ |
| 成本精度 | 微分（1/100万 美元） |
| 缓存类型 | 2（5m/1h） |
| 计费模式 | 2（订阅/余额） |
| 数据库表数 | 4 |
| 核心文件数 | 15+ |
| 代码行数 | 1,400+ |

---

## 文件位置

所有文档保存在：

```
/Users/apple/Desktop/project/v1/文稿/project/leon/
├── INDEX.md                                    # 本文档
├── QUICK_REFERENCE.md                          # 快速参考
├── RESEARCH_SUMMARY.md                         # 研究总结
├── opencode_token_billing_analysis.md          # 完整分析
└── opencode_implementation_details.md          # 实现细节
```

---

## 相关资源

### OpenCode 项目

- 位置：`/Users/apple/Documents/Project/邵云-moltbot研究/repos/opencode/`
- 主要包：`packages/opencode`、`packages/console`
- 语言：TypeScript/JavaScript
- 框架：Bun、SST

### Leon 项目

- 位置：`/Users/apple/Desktop/project/v1/文稿/project/leon/`
- 语言：Python
- 框架：Pydantic、SQLite

---

## 常见问题

### Q: 这些文档适合谁？

A: 
- **开发者**：想快速了解 token 追踪机制
- **架构师**：想理解整体设计
- **研究员**：想深入学习实现细节
- **集成者**：想将 OpenCode 的方案集成到 Leon

### Q: 需要多长时间学完？

A: 
- 快速浏览：15 分钟
- 深入学习：1-2 小时
- 完全掌握：3-5 小时

### Q: 可以直接复用 OpenCode 的代码吗？

A: 
- Token 计算逻辑：可以直接复用
- Provider 适配器：需要调整（Leon 可能不需要所有 provider）
- 数据库存储：需要调整（Leon 使用 SQLite，OpenCode 使用 MySQL）
- 计费模式：需要简化（Leon 可能不需要订阅模式）

### Q: 与 Leon 的主要差异是什么？

A: 
- OpenCode 追踪 6 项 token，Leon 追踪 4 项
- OpenCode 支持 10+ provider，Leon 支持较少
- OpenCode 有完整的计费系统，Leon 的计费较简单
- OpenCode 使用 MySQL，Leon 使用 SQLite

---

## 后续行动

### 立即行动

1. 阅读 QUICK_REFERENCE.md 了解基本概念
2. 查看 RESEARCH_SUMMARY.md 的关键发现
3. 确定是否需要集成 OpenCode 的方案

### 短期（1-2 周）

1. 审查 Leon 现有的 token 计算逻辑
2. 对比 OpenCode 的实现
3. 制定集成计划

### 中期（2-4 周）

1. 实现 6 项 token 分项追踪
2. 优化 provider 适配层
3. 增加详细的指标记录

### 长期（1-3 个月）

1. 支持订阅计费模式
2. 实现自动充值机制
3. 添加成本优化建议

---

## 联系方式

如有问题或需要进一步讨论，请参考文档中的代码片段和文件位置。

---

## 文档版本

- 版本：1.0
- 创建日期：2026-02-06
- 最后更新：2026-02-06
- 研究范围：OpenCode 项目的 token 追踪和计费实现
- 研究深度：完整的架构分析 + 实现细节 + 代码示例

