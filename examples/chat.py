#!/usr/bin/env python3
"""
Interactive chat script for Leon Agent.

Usage:
    python chat.py              # Use default workspace
    python chat.py -d .         # Use current directory as workspace
    python chat.py -d /path     # Use specific directory as workspace
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env if exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from agent import create_leon


def print_banner():
    """Print welcome banner."""
    print("=" * 70)
    print("🤖 Leon Agent - Interactive Chat")
    print("=" * 70)
    print("Commands:")
    print("  /help    - Show this help message")
    print("  /clear   - Clear screen")
    print("  /exit    - Exit chat")
    print("  /quit    - Exit chat")
    print("=" * 70)
    print()


def print_help():
    """Print help message."""
    print("\n📖 Available Commands:")
    print("  /help    - Show this help message")
    print("  /clear   - Clear screen")
    print("  /exit    - Exit chat")
    print("  /quit    - Exit chat")
    print("\n💡 Tips:")
    print("  - Leon can execute bash commands in the workspace")
    print("  - Leon can create and edit files")
    print("  - Leon can run Python scripts")
    print("  - All files are saved in the workspace directory")
    print()


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def main():
    """Main interactive chat loop."""
    parser = argparse.ArgumentParser(
        description="Interactive chat with Leon Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chat.py              # Use default workspace
  python chat.py -d .         # Use current directory
  python chat.py -d /path     # Use specific path
        """
    )
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default=None,
        help='Workspace directory for Leon Agent (default: project workspace)'
    )

    args = parser.parse_args()

    # Determine workspace
    if args.directory:
        if args.directory == '.':
            workspace = Path.cwd()
        else:
            workspace = Path(args.directory).resolve()

        if not workspace.exists():
            print(f"❌ Error: Directory does not exist: {workspace}")
            sys.exit(1)
    else:
        workspace = None  # Use default

    # Create agent
    try:
        print("🔧 Initializing Leon Agent...")
        leon = create_leon(workspace_root=workspace)
        print("✅ Agent ready!")
        print(f"📁 Workspace: {leon.workspace_root}")
        print()
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        sys.exit(1)

    # Print banner
    print_banner()

    # Generate unique session ID
    session_id = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    message_count = 0

    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith('/'):
                command = user_input.lower()

                if command in ['/exit', '/quit']:
                    print("\n👋 Goodbye!")
                    break
                elif command == '/help':
                    print_help()
                    continue
                elif command == '/clear':
                    clear_screen()
                    print_banner()
                    continue
                else:
                    print(f"❌ Unknown command: {user_input}")
                    print("💡 Type /help for available commands")
                    continue

            # Send message to agent
            message_count += 1
            print("\n🤖 Leon: ", end="", flush=True)

            try:
                result = leon.invoke(
                    message=user_input,
                    thread_id=session_id
                )

                # Print response
                response = result['messages'][-1].content
                print(response)
                print()

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                print()
                continue
            except Exception as e:
                print(f"\n❌ Error: {type(e).__name__}: {str(e)[:200]}")
                print("💡 Try rephrasing your request or type /help for assistance")
                print()
                continue

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break


if __name__ == "__main__":
    main()
