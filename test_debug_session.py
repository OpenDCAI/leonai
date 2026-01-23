#!/usr/bin/env python3
"""调试 session 状态"""

from agent import create_leon_agent

agent = create_leon_agent()
thread_id = 'test'

# 第 1 次调用
print("=" * 70)
print("第 1 次调用")
print("=" * 70)
r1 = agent.invoke('使用 bash 执行：echo $$', thread_id)

# 检查 session pool - 直接访问 agent 的 middleware
shell_middleware = agent.shell_middleware

if shell_middleware:
    print(f"\nSession pool: {list(shell_middleware._session_pool.keys())}")
    for sid, resources in shell_middleware._session_pool.items():
        session = resources.session
        process = session._process
        print(f"Session {sid}:")
        print(f"  Process: {process}")
        print(f"  Process poll: {process.poll() if process else 'None'}")
        print(f"  Terminated: {session._terminated}")

# 第 2 次调用
print("\n" + "=" * 70)
print("第 2 次调用")
print("=" * 70)
r2 = agent.invoke('使用 bash 执行：echo $$', thread_id)

if shell_middleware:
    print(f"\nSession pool: {list(shell_middleware._session_pool.keys())}")
    for sid, resources in shell_middleware._session_pool.items():
        session = resources.session
        process = session._process
        print(f"Session {sid}:")
        print(f"  Process: {process}")
        print(f"  Process poll: {process.poll() if process else 'None'}")
        print(f"  Terminated: {session._terminated}")

agent.cleanup()
