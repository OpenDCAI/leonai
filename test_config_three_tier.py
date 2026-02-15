#!/usr/bin/env python3
"""Test script for three-tier configuration system.

Tests:
1. System defaults loading
2. User-level config override
3. Project-level config override
4. Config merging priority
5. Environment variable handling
6. Virtual model resolution
"""

import json
import os
import tempfile
from pathlib import Path

from config.loader import ConfigLoader
from config.schema import LeonSettings


def test_system_defaults():
    """Test 1: System defaults loading."""
    print("\n=== Test 1: System Defaults ===")

    # Load system defaults
    loader = ConfigLoader()
    system_config = loader._load_system_defaults()

    print(f"✓ System defaults loaded from: {loader._system_defaults_dir}")
    print(f"  - Default model: {system_config.get('api', {}).get('model')}")
    print(f"  - Memory pruning keep_recent: {system_config.get('memory', {}).get('pruning', {}).get('keep_recent')}")
    print(f"  - Tools filesystem enabled: {system_config.get('tools', {}).get('filesystem', {}).get('enabled')}")

    return system_config


def test_virtual_model_resolution():
    """Test 2: Virtual model resolution."""
    print("\n=== Test 2: Virtual Model Resolution ===")

    # Set API key for validation
    os.environ["OPENAI_API_KEY"] = "test-key"

    loader = ConfigLoader()
    settings = loader.load()

    # Test each virtual model
    virtual_models = ["leon:fast", "leon:balanced", "leon:powerful", "leon:coding"]

    for vm in virtual_models:
        if vm.replace("leon:", "") in ["fast", "balanced", "powerful", "coding"]:
            # Map to actual model_mapping keys
            mapping_key = {
                "leon:fast": "leon:mini",
                "leon:balanced": "leon:medium",
                "leon:powerful": "leon:large",
                "leon:coding": "leon:max",
            }.get(vm)

            if mapping_key and mapping_key in settings.model_mapping:
                actual_model, kwargs = settings.resolve_model(mapping_key)
                print(f"✓ {mapping_key} -> {actual_model}")
                if kwargs:
                    print(f"  kwargs: {kwargs}")

    return settings


def test_user_config_override():
    """Test 3: User-level config override."""
    print("\n=== Test 3: User Config Override ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user config
        user_dir = Path(tmpdir) / ".leon"
        user_dir.mkdir()

        user_config = {"api": {"model": "claude-opus-4-6", "temperature": 0.7}, "tools": {"web": {"enabled": False}}}

        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f, indent=2)

        print(f"✓ Created user config at: {user_dir / 'config.json'}")

        # Mock HOME
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        os.environ["OPENAI_API_KEY"] = "test-key"

        try:
            loader = ConfigLoader()
            settings = loader.load()

            print(f"  - Model: {settings.api.model} (expected: claude-opus-4-6)")
            print(f"  - Temperature: {settings.api.temperature} (expected: 0.7)")
            print(f"  - Web tools enabled: {settings.tools.web.enabled} (expected: False)")

            assert settings.api.model == "claude-opus-4-6", "User config model override failed"
            assert settings.api.temperature == 0.7, "User config temperature override failed"
            assert settings.tools.web.enabled is False, "User config tools override failed"

            print("✓ User config overrides applied correctly")

        finally:
            if original_home:
                os.environ["HOME"] = original_home
            else:
                del os.environ["HOME"]


def test_project_config_override():
    """Test 4: Project-level config override."""
    print("\n=== Test 4: Project Config Override ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user config
        user_dir = Path(tmpdir) / ".leon"
        user_dir.mkdir()
        user_config = {"api": {"model": "claude-sonnet-4-5-20250929", "temperature": 0.5}}
        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f, indent=2)

        # Create project config
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        leon_dir = project_dir / ".leon"
        leon_dir.mkdir()

        project_config = {"api": {"model": "gpt-4", "temperature": 0.9}, "system_prompt": "Project-specific prompt"}

        with open(leon_dir / "config.json", "w") as f:
            json.dump(project_config, f, indent=2)

        print(f"✓ Created project config at: {leon_dir / 'config.json'}")

        # Mock HOME
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        os.environ["OPENAI_API_KEY"] = "test-key"

        try:
            loader = ConfigLoader(workspace_root=str(project_dir))
            settings = loader.load()

            print(f"  - Model: {settings.api.model} (expected: gpt-4)")
            print(f"  - Temperature: {settings.api.temperature} (expected: 0.9)")
            print(f"  - System prompt: {settings.system_prompt[:30]}... (expected: Project-specific...)")

            assert settings.api.model == "gpt-4", "Project config model override failed"
            assert settings.api.temperature == 0.9, "Project config temperature override failed"
            assert settings.system_prompt == "Project-specific prompt", "Project config system_prompt failed"

            print("✓ Project config overrides user config correctly")

        finally:
            if original_home:
                os.environ["HOME"] = original_home
            else:
                del os.environ["HOME"]


def test_config_merging():
    """Test 5: Deep merge behavior."""
    print("\n=== Test 5: Config Merging ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user config with partial settings
        user_dir = Path(tmpdir) / ".leon"
        user_dir.mkdir()
        user_config = {"api": {"temperature": 0.7}, "memory": {"pruning": {"keep_recent": 15}}}
        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f, indent=2)

        # Create project config with different partial settings
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        leon_dir = project_dir / ".leon"
        leon_dir.mkdir()

        project_config = {"api": {"model": "gpt-4"}, "memory": {"compaction": {"trigger_ratio": 0.9}}}

        with open(leon_dir / "config.json", "w") as f:
            json.dump(project_config, f, indent=2)

        print("✓ Created configs with partial overlapping settings")

        # Mock HOME
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        os.environ["OPENAI_API_KEY"] = "test-key"

        try:
            loader = ConfigLoader(workspace_root=str(project_dir))
            settings = loader.load()

            # Check deep merge results
            print(f"  - Model: {settings.api.model} (from project)")
            print(f"  - Temperature: {settings.api.temperature} (from user)")
            print(f"  - Pruning keep_recent: {settings.memory.pruning.keep_recent} (from user)")
            print(f"  - Compaction trigger_ratio: {settings.memory.compaction.trigger_ratio} (from project)")

            assert settings.api.model == "gpt-4", "Project model not applied"
            assert settings.api.temperature == 0.7, "User temperature not preserved"
            assert settings.memory.pruning.keep_recent == 15, "User pruning not preserved"
            assert settings.memory.compaction.trigger_ratio == 0.9, "Project compaction not applied"

            print("✓ Deep merge working correctly")

        finally:
            if original_home:
                os.environ["HOME"] = original_home
            else:
                del os.environ["HOME"]


def test_none_values():
    """Test 6: None values don't override."""
    print("\n=== Test 6: None Values Handling ===")

    loader = ConfigLoader()

    dict1 = {"api": {"model": "gpt-4", "temperature": 0.5}}
    dict2 = {"api": {"temperature": None}}

    result = loader._deep_merge(dict1, dict2)

    print("  - Original temperature: 0.5")
    print(f"  - Override with None: {dict2['api']['temperature']}")
    print(f"  - Result temperature: {result['api']['temperature']}")

    assert result["api"]["temperature"] == 0.5, "None value incorrectly overrode existing value"

    print("✓ None values correctly preserved existing values")


def test_environment_variables():
    """Test 7: Environment variable handling."""
    print("\n=== Test 7: Environment Variables ===")

    # Set environment variables
    os.environ["LEON__API__MODEL"] = "claude-opus-4-6"
    os.environ["LEON__API__TEMPERATURE"] = "0.8"
    os.environ["LEON__TOOLS__WEB__ENABLED"] = "false"
    os.environ["OPENAI_API_KEY"] = "test-key"

    try:
        settings = LeonSettings()

        print(f"  - LEON__API__MODEL -> {settings.api.model}")
        print(f"  - LEON__API__TEMPERATURE -> {settings.api.temperature}")
        print(f"  - LEON__TOOLS__WEB__ENABLED -> {settings.tools.web.enabled}")

        assert settings.api.model == "claude-opus-4-6", "Env var model not applied"
        assert settings.api.temperature == 0.8, "Env var temperature not applied"
        assert settings.tools.web.enabled is False, "Nested env var not applied"

        print("✓ Environment variables applied correctly")

    finally:
        # Clean up
        for key in ["LEON__API__MODEL", "LEON__API__TEMPERATURE", "LEON__TOOLS__WEB__ENABLED"]:
            if key in os.environ:
                del os.environ[key]


def test_lookup_strategy():
    """Test 8: Lookup strategy for MCP/Skills (first found wins)."""
    print("\n=== Test 8: Lookup Strategy (MCP/Skills) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user config with MCP
        user_dir = Path(tmpdir) / ".leon"
        user_dir.mkdir()
        user_config = {"mcp": {"servers": {"user_server": {"command": "user-command"}}}}
        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f, indent=2)

        # Create project config with different MCP
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        leon_dir = project_dir / ".leon"
        leon_dir.mkdir()

        project_config = {"mcp": {"servers": {"project_server": {"command": "project-command"}}}}

        with open(leon_dir / "config.json", "w") as f:
            json.dump(project_config, f, indent=2)

        print("✓ Created user MCP (user_server) and project MCP (project_server)")

        # Mock HOME
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        os.environ["OPENAI_API_KEY"] = "test-key"

        try:
            loader = ConfigLoader(workspace_root=str(project_dir))
            settings = loader.load()

            print(f"  - MCP servers: {list(settings.mcp.servers.keys())}")

            assert "project_server" in settings.mcp.servers, "Project MCP not found"
            assert "user_server" not in settings.mcp.servers, "User MCP incorrectly merged"

            print("✓ Lookup strategy working (project wins, no merge)")

        finally:
            if original_home:
                os.environ["HOME"] = original_home
            else:
                del os.environ["HOME"]


def main():
    """Run all tests."""
    print("=" * 60)
    print("Three-Tier Configuration System Test")
    print("=" * 60)

    try:
        test_system_defaults()
        test_virtual_model_resolution()
        test_user_config_override()
        test_project_config_override()
        test_config_merging()
        test_none_values()
        test_environment_variables()
        test_lookup_strategy()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
