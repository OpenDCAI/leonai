#!/usr/bin/env python3
"""简单测试：直接发送一个不安全命令"""

import os
from pathlib import Path

# Load .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from agent import create_leon

leon = create_leon()
print(f"Workspace: {leon.workspace_root}\n")

# 测试一个明显不安全的命令
print("测试命令: cd /tmp")
print("-" * 70)
response = leon.get_response(
    "Execute this bash command: cd /tmp",
    thread_id="simple-test"
)
print(response)
