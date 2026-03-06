#!/usr/bin/env python3
"""sksadd - Install skill from last search results into a group."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ANSI colors
BOLD  = "\033[1m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
GRAY  = "\033[90m"
RED   = "\033[31m"
RESET = "\033[0m"


def get_paths() -> tuple[Path, Path, Path]:
    """Return (claude_dir, skills_dir, groups_dir)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        claude_dir = Path(result.stdout.strip()) / ".claude"
    except subprocess.CalledProcessError:
        claude_dir = Path.cwd() / ".claude"
    return claude_dir, claude_dir / "skills", claude_dir / "skill-groups"


def main() -> None:
    if len(sys.argv) < 3:
        print(f"{GRAY}用法：/sksadd <组名> <编号>{RESET}")
        print(f"{GRAY}先运行 {RESET}{CYAN}/skssearch <关键词>{RESET}{GRAY} 获取编号。{RESET}")
        sys.exit(1)

    group = sys.argv[1]
    try:
        index = int(sys.argv[2]) - 1
    except ValueError:
        print(f"❌ 编号必须是整数")
        sys.exit(1)

    claude_dir, skills_dir, groups_dir = get_paths()
    last_search = claude_dir / ".sks-last-search.json"

    if not last_search.exists():
        print(f"❌ 没有搜索记录，请先运行 {CYAN}/skssearch <关键词>{RESET}")
        sys.exit(1)

    group_dir = groups_dir / group
    if not group_dir.exists():
        print(f"❌ 组 '{group}' 不存在，先运行 {CYAN}/sksgnew {group}{RESET}")
        sys.exit(1)

    data = json.loads(last_search.read_text())
    if index < 0 or index >= len(data):
        print(f"❌ 编号超出范围（共 {len(data)} 条结果）")
        sys.exit(1)

    install_cmd = data[index]["installCmd"]
    skill_name = install_cmd.split("@")[-1].split("/")[-1] if "@" in install_cmd else install_cmd.split("/")[-1]

    print(f"{GRAY}正在安装 {skill_name}...{RESET}")
    result = subprocess.run(
        ["npx", "skills", "add", install_cmd, "--agent", "claude-code", "--copy", "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌ 安装失败，可能是 SkillsMP 数据不准确或网络问题")
        sys.exit(1)

    installed = skills_dir / skill_name
    if not installed.exists():
        print(f"❌ 安装失败，未找到 {installed}（可能是 skill 路径不匹配）")
        sys.exit(1)

    dest = group_dir / skill_name
    shutil.move(str(installed), str(dest))
    print(f"✅ {BOLD}{skill_name}{RESET} 已安装到组 {BOLD}{group}{RESET}{GRAY}（未激活）{RESET}")
    print(f"{GRAY}激活请运行：{RESET}{CYAN}/skson {group}{RESET}\n")


if __name__ == "__main__":
    main()
