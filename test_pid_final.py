#!/usr/bin/env python3
"""最终验证 - 直接提取 ToolMessage 中的 PID"""

from agent import create_leon_agent

agent = create_leon_agent()
thread_id = 'pid_test'

def extract_pid(result):
    """从结果中提取最新的 ToolMessage 内容"""
    for msg in reversed(result['messages']):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
            return msg.content.strip()
    return None

print("=" * 70)
print("验证 Bash Session PID 持久化")
print("=" * 70)

# 第 1 次
r1 = agent.invoke('使用 bash 执行：echo $$', thread_id)
pid1 = extract_pid(r1)
print(f"第 1 次 PID: {pid1}")

# 第 2 次
r2 = agent.invoke('使用 bash 执行：echo $$', thread_id)
pid2 = extract_pid(r2)
print(f"第 2 次 PID: {pid2}")

# 第 3 次
r3 = agent.invoke('使用 bash 执行：echo $$', thread_id)
pid3 = extract_pid(r3)
print(f"第 3 次 PID: {pid3}")

print("\n" + "=" * 70)
if pid1 == pid2 == pid3:
    print("✅ 成功！PID 保持不变，session 持久化工作正常！")
else:
    print(f"❌ 失败！PID 发生变化：{pid1} → {pid2} → {pid3}")
print("=" * 70)

# 测试文件系统持久化
print("\n" + "=" * 70)
print("验证文件系统持久化")
print("=" * 70)

r4 = agent.invoke('使用 bash 执行：echo "test" > /tmp/session_test.txt', thread_id)
print("创建文件...")

r5 = agent.invoke('使用 bash 执行：cat /tmp/session_test.txt', thread_id)
content = extract_pid(r5)
print(f"读取文件: {content}")

if content and 'test' in content:
    print("✅ 文件系统持久化成功！")
else:
    print("❌ 文件系统持久化失败！")

agent.invoke('使用 bash 执行：rm -f /tmp/session_test.txt', thread_id)
agent.cleanup()
