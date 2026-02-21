# Agent Team 管理规范

经验教训，组建 Agent Team 时必须遵守：

## PM 职责边界
- PM 只协调、不写码。必须通过 spawn 子成员执行任务
- ❌ PM 自己标 completed 但没人 review、没跑通

## 完成标准
- 代码写了 ≠ 完成。**跑通 + 测试通过 = 完成**
- 基础设施类任务必须实际启动验证（Docker 容器运行、端口可达、健康检查通过）
- 每个模块必须有对应测试，没有测试不算完成

## 基础设施先行
- 基建项目先搭基础设施（Docker/Redis/RabbitMQ/Supabase），确认可用后再写业务代码
- ❌ 先写一堆代码再补基础设施

## 先读后写
- 每个成员开始前必须先读懂 leonai 相关模块的现有代码
- 核心原则："包一层"，复用现有 sandbox/ 和 middleware/，不重写
- ❌ 创建与现有代码功能重复的新文件

## Reviewer 全程跟进
- 每个模块完成后立即 review，不是最后才审
- Review 检查项：是否复用现有代码、是否有测试、是否实际跑通、是否与现有代码兼容

## 环境信息
- Docker 已安装，Redis/RabbitMQ 用 Docker 容器运行
- `proxy_on` 开代理，安装软件前先执行
- Supabase MCP 可用（`~/.mcp.json`），可直接操作 Supabase
