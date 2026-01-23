#!/usr/bin/env python3
"""测试原生 ShellToolMiddleware 的持久化"""

import os
from pathlib import Path

# 加载 .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from langchain.agents import create_agent
from langchain.agents.middleware import ShellToolMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

# 创建 agent
model = init_chat_model("claude-sonnet-4-5-20250929")

agent = create_agent(
    model=model,
    tools=[],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/tmp",
        ),
    ],
    checkpointer=MemorySaver(),
)

thread_id = "test"

# 第 1 次
r1 = agent.invoke(
    {"messages": [{"role": "user", "content": "使用 bash 执行：echo $$"}]},
    config={"configurable": {"thread_id": thread_id}},
)
print("第 1 次:", r1["messages"][-1].content[:100])

# 第 2 次
r2 = agent.invoke(
    {"messages": [{"role": "user", "content": "使用 bash 执行：echo $$"}]},
    config={"configurable": {"thread_id": thread_id}},
)
print("第 2 次:", r2["messages"][-1].content[:100])

# 第 3 次
r3 = agent.invoke(
    {"messages": [{"role": "user", "content": "使用 bash 执行：echo $$"}]},
    config={"configurable": {"thread_id": thread_id}},
)
print("第 3 次:", r3["messages"][-1].content[:100])
