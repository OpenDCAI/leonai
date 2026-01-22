"""
Quick start script for the Comprehensive Anthropic Agent.

This script provides a simple interactive demo to test the agent.
Uses LangChain v1 API.
"""

import os

from agent import create_comprehensive_agent


def main():
    """Run a quick interactive demo of the agent."""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  ANTHROPIC_API_KEY=your-api-key-here")
        return

    print("=" * 60)
    print("🤖 Comprehensive LangChain Anthropic Agent")
    print("=" * 60)
    print("\nInitializing agent with all middleware...")
    print("  ✓ Prompt caching")
    print("  ✓ Bash tool")
    print("  ✓ Text editor")
    print("  ✓ Memory")
    print("  ✓ File search")
    print()

    # Create agent
    agent = create_comprehensive_agent()
    thread_id = "quick-start-demo"

    try:
        # Demo 1: Memory
        print("📝 Demo 1: Testing memory...")
        response = agent.get_response(
            "Remember that I'm testing the LangChain agent and my name is User. Confirm what you stored.",
            thread_id=thread_id
        )
        print(f"Agent: {response}\n")

        # Demo 2: File creation
        print("📄 Demo 2: Creating a file...")
        response = agent.get_response(
            "Create a simple Python script at /project/demo.py that prints 'Hello from LangChain!'",
            thread_id=thread_id
        )
        print(f"Agent: {response}\n")

        # Demo 3: Memory recall
        print("🧠 Demo 3: Recalling from memory...")
        response = agent.get_response(
            "What's my name?",
            thread_id=thread_id
        )
        print(f"Agent: {response}\n")

        print("=" * 60)
        print("✅ Quick start demo completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  • Run 'python examples.py' for comprehensive examples")
        print("  • Check README.md for detailed documentation")
        print("  • Modify agent.py to customize the agent")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  • Ensure ANTHROPIC_API_KEY is set correctly")
        print("  • Check that all dependencies are installed")
        print("  • See README.md for more help")

    finally:
        agent.cleanup()
        print("\n🧹 Cleanup complete")


if __name__ == "__main__":
    main()
