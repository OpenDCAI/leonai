#!/usr/bin/env python3
"""
Cascade-Like Agent 演示脚本

展示所有 Cascade 风格的工具功能：
1. 文件操作（read/write/edit/multi_edit/list_dir）
2. 搜索功能（grep_search/find_by_name）
3. 命令执行（bash with security hooks）
4. 安全机制（权限控制、审计日志）
"""

import os
import sys
from pathlib import Path

# 加载 .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from cascade_agent import create_leon_agent


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_file_operations(agent, workspace):
    """演示文件操作"""
    print_section("Demo 1: File Operations")

    # 1. 创建文件
    print("📝 Creating a Python file...")
    response = agent.get_response(
        f"Create a Python file at {workspace}/calculator.py with a simple Calculator class "
        f"that has add and subtract methods.",
        thread_id="demo-file-ops",
    )
    print(f"Response: {response[:200]}...\n")

    # 2. 读取文件
    print("📖 Reading the file...")
    response = agent.get_response(
        f"Read the file {workspace}/calculator.py", thread_id="demo-file-ops"
    )
    print(f"Response:\n{response}\n")

    # 3. 编辑文件
    print("✏️  Editing the file...")
    response = agent.get_response(
        f"Add a multiply method to the Calculator class in {workspace}/calculator.py",
        thread_id="demo-file-ops",
    )
    print(f"Response: {response[:200]}...\n")

    # 4. 列出目录
    print("📂 Listing directory...")
    response = agent.get_response(f"List the contents of {workspace}", thread_id="demo-file-ops")
    print(f"Response:\n{response}\n")


def demo_search_operations(agent, workspace):
    """演示搜索功能"""
    print_section("Demo 2: Search Operations")

    # 1. 创建多个文件用于搜索
    print("📝 Creating test files...")
    agent.get_response(
        f"Create three Python files in {workspace}:\n"
        f"1. {workspace}/utils.py with helper functions\n"
        f"2. {workspace}/models.py with data models\n"
        f"3. {workspace}/tests.py with test cases",
        thread_id="demo-search",
    )

    # 2. grep_search - 搜索内容
    print("\n🔍 Searching for 'def' in Python files...")
    response = agent.get_response(
        f"Search for the pattern 'def' in all files under {workspace} using grep_search",
        thread_id="demo-search",
    )
    print(f"Response:\n{response}\n")

    # 3. find_by_name - 查找文件
    print("🔎 Finding all Python files...")
    response = agent.get_response(
        f"Find all Python files (*.py) in {workspace} using find_by_name",
        thread_id="demo-search",
    )
    print(f"Response:\n{response}\n")


def demo_bash_operations(agent, workspace):
    """演示命令执行"""
    print_section("Demo 3: Bash Operations")

    # 1. 安全命令
    print("✅ Executing safe commands...")
    response = agent.get_response(
        f"Use bash to:\n"
        f"1. Check Python version\n"
        f"2. List files in the workspace\n"
        f"3. Count the number of .py files",
        thread_id="demo-bash",
    )
    print(f"Response: {response[:300]}...\n")

    # 2. 尝试危险命令（会被拦截）
    print("⚠️  Attempting dangerous command (should be blocked)...")
    response = agent.get_response(
        "Use bash to remove all files with 'rm -rf *'", thread_id="demo-bash"
    )
    print(f"Response: {response[:300]}...\n")


def demo_multi_edit(agent, workspace):
    """演示批量编辑"""
    print_section("Demo 4: Multi-Edit Operations")

    # 创建一个文件
    print("📝 Creating a file for multi-edit demo...")
    agent.get_response(
        f"Create a file at {workspace}/config.py with these variables:\n"
        f"DEBUG = False\n"
        f"PORT = 8000\n"
        f"HOST = 'localhost'",
        thread_id="demo-multi",
    )

    # 使用 multi_edit 批量修改
    print("\n✏️  Applying multiple edits...")
    response = agent.get_response(
        f"Use multi_edit to change {workspace}/config.py:\n"
        f"1. Change DEBUG from False to True\n"
        f"2. Change PORT from 8000 to 3000\n"
        f"3. Change HOST from 'localhost' to '0.0.0.0'",
        thread_id="demo-multi",
    )
    print(f"Response: {response[:200]}...\n")

    # 读取修改后的文件
    print("📖 Reading the modified file...")
    response = agent.get_response(
        f"Read {workspace}/config.py to verify the changes", thread_id="demo-multi"
    )
    print(f"Response:\n{response}\n")


def demo_security_features(agent, workspace):
    """演示安全功能"""
    print_section("Demo 5: Security Features")

    # 1. 尝试访问 workspace 外的文件
    print("🔒 Attempting to access file outside workspace (should be blocked)...")
    response = agent.get_response(
        "Read the file /etc/passwd", thread_id="demo-security"
    )
    print(f"Response: {response[:300]}...\n")

    # 2. 尝试使用相对路径
    print("🔒 Attempting to use relative path (should fail)...")
    response = agent.get_response(
        "Read the file ./test.py", thread_id="demo-security"
    )
    print(f"Response: {response[:300]}...\n")

    # 3. 查看审计日志
    print("📋 Checking audit logs...")
    log_files = [
        workspace / "bash_commands.log",
        workspace / "file_access.log",
    ]
    for log_file in log_files:
        if log_file.exists():
            print(f"\n{log_file.name}:")
            with open(log_file, "r") as f:
                lines = f.readlines()
                for line in lines[-5:]:  # 显示最后 5 行
                    print(f"  {line.rstrip()}")


def demo_read_only_mode():
    """演示只读模式"""
    print_section("Demo 6: Read-Only Mode")

    # 创建只读 agent
    print("🔒 Creating agent in read-only mode...")
    readonly_agent = create_leon_agent(read_only=True)

    try:
        # 尝试写入（应该被拦截）
        print("\n❌ Attempting write operation (should be blocked)...")
        response = readonly_agent.get_response(
            f"Create a file at {readonly_agent.workspace_root}/test.txt",
            thread_id="demo-readonly",
        )
        print(f"Response: {response[:300]}...\n")

    finally:
        readonly_agent.cleanup()


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("  CASCADE-LIKE AGENT DEMONSTRATION")
    print("  Complete Middleware-Based Implementation")
    print("=" * 80)

    # 创建 agent
    print("\n🚀 Initializing Cascade-Like Agent...")
    agent = create_leon_agent()
    workspace = agent.workspace_root

    print(f"✅ Agent initialized")
    print(f"📁 Workspace: {workspace}\n")

    try:
        # 运行所有演示
        demo_file_operations(agent, workspace)
        demo_search_operations(agent, workspace)
        demo_bash_operations(agent, workspace)
        demo_multi_edit(agent, workspace)
        demo_security_features(agent, workspace)
        demo_read_only_mode()

        print_section("Summary")
        print("✅ All demonstrations completed successfully!")
        print("\n📊 Features Demonstrated:")
        print("  ✓ File operations (read/write/edit/multi_edit/list_dir)")
        print("  ✓ Search operations (grep_search/find_by_name)")
        print("  ✓ Bash command execution with security hooks")
        print("  ✓ Multi-edit for batch file modifications")
        print("  ✓ Security features (path validation, command blocking)")
        print("  ✓ Read-only mode")
        print("  ✓ Audit logging")
        print("\n💡 All operations use absolute paths and are restricted to workspace")
        print(f"📁 Workspace location: {workspace}")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🧹 Cleaning up...")
        agent.cleanup()
        print("✅ Done!\n")


if __name__ == "__main__":
    main()
