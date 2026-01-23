#!/usr/bin/env python3
"""验证 bash session 真正持久化"""

from agent import create_leon_agent

agent = create_leon_agent()
thread_id = "verify-persistence"

print("=" * 70)
print("测试 1: 验证 Shell 进程 PID 持久化")
print("=" * 70)

# 第 1 次调用
r1 = agent.invoke("使用 bash 执行：echo $$", thread_id=thread_id)
print(f"第 1 次 PID: {r1['messages'][-1].content}\n")

# 第 2 次调用
r2 = agent.invoke("使用 bash 执行：echo $$", thread_id=thread_id)
print(f"第 2 次 PID: {r2['messages'][-1].content}\n")

# 第 3 次调用
r3 = agent.invoke("使用 bash 执行：echo $$", thread_id=thread_id)
print(f"第 3 次 PID: {r3['messages'][-1].content}\n")

print("=" * 70)
print("测试 2: 验证文件系统持久化")
print("=" * 70)

# 创建文件
r4 = agent.invoke("使用 bash 执行：echo 'test' > /tmp/verify.txt", thread_id=thread_id)
print(f"创建文件: {r4['messages'][-1].content}\n")

# 读取文件
r5 = agent.invoke("使用 bash 执行：cat /tmp/verify.txt", thread_id=thread_id)
print(f"读取文件: {r5['messages'][-1].content}\n")

# 清理
agent.invoke("使用 bash 执行：rm -f /tmp/verify.txt", thread_id=thread_id)
agent.cleanup()

print("=" * 70)
print("结论: 如果 PID 相同，说明 session 持久化成功！")
print("=" * 70)
