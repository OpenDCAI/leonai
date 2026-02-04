#!/usr/bin/env python3
"""
Leon CLI - Textual TUI 模式

使用 Textual 框架构建的现代化终端界面
"""

import argparse
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from tui.config import ConfigManager, interactive_config, show_config
from tui.session import SessionManager


def format_relative_time(dt: datetime | str | None) -> str:
    """Format datetime as relative time string"""
    if dt is None:
        return "未知"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt

    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} 分钟前"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} 小时前"
    else:
        days = int(seconds / 86400)
        return f"{days} 天前"


def cmd_thread_list(args):
    """List all conversation threads"""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    session_mgr = SessionManager()

    # Get threads from session
    threads = session_mgr.get_threads()

    if not threads:
        console.print("[yellow]暂无对话记录[/yellow]")
        return

    # Try to get more info from database
    db_threads = session_mgr.get_threads_from_db()
    db_info = {t["thread_id"]: t for t in db_threads}

    # Get message counts using TimeTravelManager
    from tui.time_travel import TimeTravelManager
    time_travel_mgr = TimeTravelManager()

    table = Table(title="对话列表")
    table.add_column("Thread ID", style="cyan")
    table.add_column("消息", style="magenta", justify="right")
    table.add_column("首条消息", style="white", max_width=30)
    table.add_column("最后活跃", style="green")
    table.add_column("状态", style="yellow")

    last_thread = session_mgr.get_last_thread_id()

    for thread_id in threads:
        info = db_info.get(thread_id, {})
        last_active = format_relative_time(info.get("last_active"))
        status = "(当前)" if thread_id == last_thread else ""

        # Get message count and first message
        checkpoints = time_travel_mgr.get_checkpoints(thread_id, user_turns_only=True)
        msg_count = str(len(checkpoints)) if checkpoints else "0"
        first_msg = "-"
        if checkpoints and checkpoints[0].user_message:
            first_msg = checkpoints[0].user_message
            if len(first_msg) > 28:
                first_msg = first_msg[:28] + "…"

        table.add_row(thread_id, msg_count, first_msg, last_active, status)

    console.print(table)


def cmd_thread_history(args):
    """Show checkpoint history for a thread"""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    thread_id = args.thread_id

    db_path = Path.home() / ".leon" / "leon.db"
    if not db_path.exists():
        console.print("[red]数据库不存在[/red]")
        return

    from tui.time_travel import TimeTravelManager

    time_travel_mgr = TimeTravelManager()
    checkpoints = time_travel_mgr.get_checkpoints(thread_id, user_turns_only=True)

    if not checkpoints:
        console.print(f"[yellow]对话 {thread_id} 暂无历史节点[/yellow]")
        return

    table = Table(title=f"对话历史: {thread_id}")
    table.add_column("#", style="dim")
    table.add_column("Checkpoint ID", style="cyan")
    table.add_column("时间", style="green")
    table.add_column("消息", style="white")
    table.add_column("文件操作", style="yellow")

    for i, cp in enumerate(checkpoints):
        time_str = format_relative_time(cp.timestamp)
        msg = cp.user_message or "-"
        if len(msg) > 40:
            msg = msg[:40] + "..."
        ops = str(cp.file_operations_count) if cp.file_operations_count > 0 else "-"
        current = " (当前)" if cp.is_current else ""
        table.add_row(
            str(i + 1) + current,
            cp.checkpoint_id[:12] + "...",
            time_str,
            msg,
            ops,
        )

    console.print(table)


def cmd_thread_rewind(args):
    """Rewind a thread to a specific checkpoint"""
    from rich.console import Console

    console = Console()
    thread_id = args.thread_id
    checkpoint_id = args.checkpoint_id

    db_path = Path.home() / ".leon" / "leon.db"
    if not db_path.exists():
        console.print("[red]数据库不存在[/red]")
        return

    from tui.time_travel import TimeTravelManager

    time_travel_mgr = TimeTravelManager()

    # Find the checkpoint
    checkpoints = time_travel_mgr.get_checkpoints(thread_id)
    target_cp = None

    for cp in checkpoints:
        if cp.checkpoint_id.startswith(checkpoint_id):
            target_cp = cp
            break

    if not target_cp:
        console.print(f"[red]找不到 checkpoint: {checkpoint_id}[/red]")
        return

    # Show what will be reverted
    ops_to_revert = time_travel_mgr.get_operations_to_revert(thread_id, target_cp.checkpoint_id)

    if ops_to_revert:
        console.print(f"[yellow]将撤销 {len(ops_to_revert)} 个文件操作:[/yellow]")
        for op in ops_to_revert[:5]:
            console.print(f"  - {op.operation_type}: {op.file_path}")
        if len(ops_to_revert) > 5:
            console.print(f"  ... 还有 {len(ops_to_revert) - 5} 个操作")

    # Confirm
    if not args.yes:
        confirm = input("\n确认回退? [y/N] ")
        if confirm.lower() != "y":
            console.print("[yellow]已取消[/yellow]")
            return

    # Execute rewind
    result = time_travel_mgr.rewind_to(thread_id, target_cp.checkpoint_id)

    if result.success:
        console.print(f"[green]✓ {result.message}[/green]")
    else:
        console.print(f"[red]✗ {result.message}[/red]")
        for error in result.errors:
            console.print(f"  [red]{error}[/red]")


def cmd_thread_rm(args):
    """Delete a thread"""
    from rich.console import Console

    console = Console()
    thread_id = args.thread_id

    session_mgr = SessionManager()

    # Confirm
    if not args.yes:
        confirm = input(f"确认删除对话 {thread_id}? [y/N] ")
        if confirm.lower() != "y":
            console.print("[yellow]已取消[/yellow]")
            return

    if session_mgr.delete_thread(thread_id):
        console.print(f"[green]✓ 已删除对话: {thread_id}[/green]")
    else:
        console.print(f"[red]✗ 删除失败[/red]")


def cmd_sandbox(args):
    """Launch sandbox session manager TUI"""
    import os

    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ AGENTBAY_API_KEY not set")
        print("Set it in ~/.leon/config.env or as environment variable")
        sys.exit(1)

    try:
        from tui.widgets.sandbox_manager import SandboxManagerApp
        SandboxManagerApp(api_key=api_key).run()
    except ImportError as e:
        print(f"❌ Failed to import sandbox manager: {e}")
        print("Make sure wuying-agentbay-sdk is installed: uv pip install wuying-agentbay-sdk")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Leon AI - 你的 AI 编程助手", add_help=False)
    parser.add_argument("--profile", type=str, help="Profile 配置文件路径")
    parser.add_argument("--workspace", type=str, help="工作目录")
    parser.add_argument("--thread", type=str, help="Thread ID (恢复对话)")
    parser.add_argument("-c", "--continue", dest="continue_last", action="store_true", help="继续上次对话")
    parser.add_argument("-h", "--help", action="store_true", help="显示帮助信息")
    parser.add_argument("command", nargs="?", help="命令 (config, thread)")
    parser.add_argument("subcommand", nargs="?", help="子命令")
    parser.add_argument("extra_args", nargs="*", help="额外参数")

    args, unknown = parser.parse_known_args()

    if args.help and not args.command:
        print("Leon AI - 你的 AI 编程助手\n")
        print("用法:")
        print("  leonai                    启动 Leon (新对话)")
        print("  leonai -c                 继续上次对话")
        print("  leonai --profile <path>   使用指定 profile 启动")
        print("  leonai --workspace <dir>  指定工作目录")
        print("  leonai --thread <id>      恢复指定对话")
        print("  leonai config             配置 API key 和其他设置")
        print("  leonai config show        显示当前配置")
        print()
        print("Thread 管理:")
        print("  leonai thread ls          列出所有对话")
        print("  leonai thread list        列出所有对话")
        print("  leonai thread history <thread_id>   查看对话历史")
        print("  leonai thread rewind <thread_id> <checkpoint_id>  回退到指定节点")
        print("  leonai thread rm <thread_id>        删除对话")
        print()
        print("Sandbox 管理:")
        print("  leonai sandbox            打开 sandbox 会话管理器")
        return

    # Handle config command
    if args.command == "config":
        if args.subcommand == "show":
            show_config()
        else:
            interactive_config()
        return

    # Handle thread command
    if args.command == "thread":
        subcommand = args.subcommand

        if subcommand in ("ls", "list", None):
            cmd_thread_list(args)
        elif subcommand == "history":
            if not args.extra_args:
                print("用法: leonai thread history <thread_id>")
                sys.exit(1)
            args.thread_id = args.extra_args[0]
            cmd_thread_history(args)
        elif subcommand == "rewind":
            if len(args.extra_args) < 2:
                print("用法: leonai thread rewind <thread_id> <checkpoint_id> [-y]")
                sys.exit(1)
            args.thread_id = args.extra_args[0]
            args.checkpoint_id = args.extra_args[1]
            args.yes = "-y" in unknown or "--yes" in unknown
            cmd_thread_rewind(args)
        elif subcommand == "rm":
            if not args.extra_args:
                print("用法: leonai thread rm <thread_id> [-y]")
                sys.exit(1)
            args.thread_id = args.extra_args[0]
            args.yes = "-y" in unknown or "--yes" in unknown
            cmd_thread_rm(args)
        else:
            print(f"未知子命令: {subcommand}")
            print("可用子命令: ls, list, history, rewind, rm")
            sys.exit(1)
        return

    # Handle sandbox command
    if args.command == "sandbox":
        cmd_sandbox(args)
        return

    config_manager = ConfigManager()
    config_manager.load_to_env()

    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  未检测到 API Key，进入配置向导...\n")
        interactive_config()
        config_manager.load_to_env()
        if not os.getenv("OPENAI_API_KEY"):
            print("\n❌ 配置未完成，退出")
            sys.exit(1)
        print()  # 空行分隔

    workspace = Path(args.workspace) if args.workspace else Path.cwd()

    model_name = os.getenv("MODEL_NAME") or None
    print("🚀 初始化 Leon Agent...")

    from agent import create_leon_agent
    from tui.app import run_tui

    try:
        agent = create_leon_agent(
            model_name=model_name or "claude-sonnet-4-5-20250929",
            profile=args.profile,
            workspace_root=workspace,
        )
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

    print(f"✅ Agent 已就绪")
    print(f"📁 工作目录: {agent.workspace_root}\n")

    # Session 管理
    session_mgr = SessionManager()

    # 确定 thread_id
    if args.thread:
        thread_id = args.thread
        print(f"📝 恢复对话: {thread_id}")
    elif args.continue_last:
        last_thread = session_mgr.get_last_thread_id()
        if last_thread:
            thread_id = last_thread
            print(f"📝 继续上次对话: {thread_id}")
        else:
            thread_id = f"tui-{uuid.uuid4().hex[:8]}"
            print(f"📝 新对话: {thread_id}")
    else:
        thread_id = f"tui-{uuid.uuid4().hex[:8]}"
        print(f"📝 新对话: {thread_id}")

    try:
        run_tui(agent, agent.workspace_root, thread_id, session_mgr)
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    finally:
        # 保存 session
        session_mgr.save_session(thread_id, str(workspace))
        # 清理资源
        agent.close()
        print("\n🧹 已退出")


if __name__ == "__main__":
    main()
