---
name: langchain-agents
description: LangChain middleware state/context 分层 + session 持久化。用于自定义 middleware、持久资源（shell/DB）、checkpoint 序列化问题。
---

# LangChain Agents

## State vs Runtime.context 严格分层

State: 只存可序列化数据（如 session_id）  
Runtime.context: 存不可序列化资源（如 session 池、数据库连接）

## UntrackedValue 的正确用法

用于运行时资源，不被 checkpoint 序列化  
每次恢复时需要在 before_agent 中重新注入

## Middleware 生命周期管理

before_agent: 注入运行时资源  
after_agent: 清理或保持资源  
禁用底层 middleware 的生命周期方法来接管控制

## Session 持久化的正确模式

Session 池存在 context 中  
Session ID 存在 state 中  
禁用 finalizer 防止垃圾回收
