"""Constants for Anthropic tools middleware."""

TEXT_EDITOR_TOOL_TYPE = "text_editor_20250728"
TEXT_EDITOR_TOOL_NAME = "str_replace_based_edit_tool"
MEMORY_TOOL_TYPE = "memory_20250818"
MEMORY_TOOL_NAME = "memory"

MEMORY_SYSTEM_PROMPT = """IMPORTANT: ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE \
DOING ANYTHING ELSE.
MEMORY PROTOCOL:
1. Use the `view` command of your `memory` tool to check for earlier progress.
2. ... (work on the task) ...
   - As you make progress, record status / progress / thoughts etc in your memory.
ASSUME INTERRUPTION: Your context window might be reset at any moment, so you risk \
losing any progress that is not recorded in your memory directory."""
