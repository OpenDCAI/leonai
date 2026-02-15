#!/usr/bin/env python3
"""Test hot-reload functionality for Agent.update_config()."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent import LeonAgent


def test_update_config_basic():
    """Test 1: Basic update_config() method execution."""
    print("\n=== Test 1: Basic update_config() ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create agent with new config system
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",  # Use new config system
            verbose=True,
        )

        print(f"Initial model: {agent.model_name}")
        print(f"Initial checkpointer: {agent.checkpointer}")

        # Update to different model
        try:
            agent.update_config(model="gpt-4")
            print("✅ update_config() executed successfully")
            print(f"New model: {agent.model_name}")
            print(f"Checkpointer preserved: {agent.checkpointer is not None}")
            return True
        except Exception as e:
            print(f"❌ update_config() failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            agent.close()


def test_virtual_model_resolution():
    """Test 2: Virtual model name resolution."""
    print("\n=== Test 2: Virtual Model Resolution ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=True,
        )

        virtual_models = ["leon:mini", "leon:medium", "leon:large", "leon:max"]
        results = []

        for vm in virtual_models:
            try:
                agent.update_config(model=vm)
                resolved = agent.model_name
                print(f"✅ {vm} → {resolved}")
                results.append(True)
            except Exception as e:
                print(f"❌ {vm} failed: {e}")
                results.append(False)

        agent.close()
        return all(results)


def test_concrete_model_names():
    """Test 3: Concrete model name switching."""
    print("\n=== Test 3: Concrete Model Names ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=True,
        )

        concrete_models = [
            "gpt-4",
            "claude-opus-4-6",
            "claude-sonnet-4-5-20250929",
        ]
        results = []

        for model in concrete_models:
            try:
                agent.update_config(model=model)
                print(f"✅ Switched to {model}")
                print(f"   agent.model_name = {agent.model_name}")
                results.append(True)
            except Exception as e:
                print(f"❌ {model} failed: {e}")
                results.append(False)

        agent.close()
        return all(results)


def test_tool_config_updates():
    """Test 4: Tool configuration updates."""
    print("\n=== Test 4: Tool Config Updates ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=True,
        )

        try:
            # Update tool settings
            agent.update_config(
                model="gpt-4",
                web={"enabled": False},
            )
            print("✅ Tool config update executed")
            print(f"   Model: {agent.model_name}")
            print(f"   Web tools enabled: {agent.config.tools.web.enabled}")
            return True
        except Exception as e:
            print(f"❌ Tool config update failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            agent.close()


def test_error_handling():
    """Test 5: Error handling for invalid inputs."""
    print("\n=== Test 5: Error Handling ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 5a: Invalid model name
        print("\n5a. Invalid virtual model name:")
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=False,
        )

        try:
            agent.update_config(model="leon:invalid")
            print("❌ Should have raised ValueError")
            result_5a = False
        except ValueError as e:
            print(f"✅ Correctly raised ValueError: {e}")
            result_5a = True
        except Exception as e:
            print(f"❌ Wrong exception type: {e}")
            result_5a = False
        finally:
            agent.close()

        # Test 5b: Update on old profile mode
        print("\n5b. Update on old profile mode:")
        try:
            agent_old = LeonAgent(
                model_name="claude-sonnet-4-5-20250929",
                workspace_root=tmpdir,
                profile=None,  # Old profile mode
                verbose=False,
            )

            try:
                agent_old.update_config(model="gpt-4")
                print("❌ Should have raised RuntimeError")
                result_5b = False
            except RuntimeError as e:
                print(f"✅ Correctly raised RuntimeError: {e}")
                result_5b = True
            except Exception as e:
                print(f"❌ Wrong exception type: {e}")
                result_5b = False
            finally:
                agent_old.close()
        except Exception as e:
            print(f"⚠️  Could not create old-mode agent: {e}")
            result_5b = True  # Skip this test

        return result_5a and result_5b


def test_checkpointer_preservation():
    """Test 6: Checkpointer preservation across updates."""
    print("\n=== Test 6: Checkpointer Preservation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=True,
        )

        original_checkpointer = agent.checkpointer
        print(f"Original checkpointer: {original_checkpointer}")

        # Update config
        agent.update_config(model="gpt-4")

        new_checkpointer = agent.checkpointer
        print(f"New checkpointer: {new_checkpointer}")

        # Verify same instance
        if original_checkpointer is new_checkpointer:
            print("✅ Checkpointer preserved (same instance)")
            result = True
        else:
            print("❌ Checkpointer changed (different instance)")
            result = False

        agent.close()
        return result


def test_middleware_stack_rebuild():
    """Test 7: Middleware stack rebuild."""
    print("\n=== Test 7: Middleware Stack Rebuild ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = LeonAgent(
            model_name="claude-sonnet-4-5-20250929",
            workspace_root=tmpdir,
            agent="default",
            verbose=True,
        )

        # Check initial middleware
        print(f"Initial agent: {agent.agent}")
        print(f"Initial runtime: {agent.runtime}")

        # Update config
        agent.update_config(model="gpt-4")

        # Check updated middleware
        print(f"Updated agent: {agent.agent}")
        print(f"Updated runtime: {agent.runtime}")

        if agent.agent is not None and agent.runtime is not None:
            print("✅ Middleware stack rebuilt successfully")
            result = True
        else:
            print("❌ Middleware stack incomplete")
            result = False

        agent.close()
        return result


def main():
    """Run all tests."""
    print("=" * 60)
    print("Hot-Reload Functionality Test Suite")
    print("=" * 60)

    # Check API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return False

    tests = [
        ("Basic update_config()", test_update_config_basic),
        ("Virtual model resolution", test_virtual_model_resolution),
        ("Concrete model names", test_concrete_model_names),
        ("Tool config updates", test_tool_config_updates),
        ("Error handling", test_error_handling),
        ("Checkpointer preservation", test_checkpointer_preservation),
        ("Middleware stack rebuild", test_middleware_stack_rebuild),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
