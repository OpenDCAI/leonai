"""
Skills Middleware - Progressive disclosure of specialized capabilities

Based on LangChain skills pattern:
- Skills are SKILL.md files with frontmatter metadata
- Progressive disclosure: only load skill content when needed
- Tool-based invocation: load_skill tool to access specialized prompts
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage


class SkillsMiddleware(AgentMiddleware):
    """Skills Middleware - Progressive disclosure of specialized capabilities"""

    TOOL_LOAD_SKILL = "load_skill"

    def __init__(self, skill_paths: list[str | Path], enabled_skills: dict[str, bool] | None = None, verbose: bool = True):
        """
        Initialize Skills middleware

        Args:
            skill_paths: List of directories containing SKILL.md files
            enabled_skills: Dict of skill_name: enabled (None = all enabled)
            verbose: Whether to output detailed logs
        """
        self.skill_paths = [Path(p).expanduser().resolve() for p in skill_paths]
        self.enabled_skills = enabled_skills or {}
        self.verbose = verbose
        self._skills_index: dict[str, Path] = {}
        self._load_skills_index()

        if self.verbose:
            print(f"[SkillsMiddleware] Initialized with {len(self._skills_index)} skills")
            if self._skills_index:
                print(f"[SkillsMiddleware] Available: {', '.join(self._skills_index.keys())}")

    def _load_skills_index(self):
        """Scan skill directories and build index from frontmatter"""
        for skill_dir in self.skill_paths:
            if not skill_dir.exists():
                continue

            for skill_file in skill_dir.rglob("SKILL.md"):
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    metadata = self._parse_frontmatter(content)

                    if "name" in metadata:
                        skill_name = metadata["name"]
                        # Later paths override earlier ones
                        self._skills_index[skill_name] = skill_file
                except Exception as e:
                    print(f"[SkillsMiddleware] Error loading {skill_file}: {e}")

    def _parse_frontmatter(self, content: str) -> dict[str, str]:
        """Parse YAML frontmatter from SKILL.md"""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return {}

        frontmatter = match.group(1)
        metadata = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        return metadata

    def _load_skill_impl(self, skill_name: str) -> str:
        """Load skill content"""
        if skill_name not in self._skills_index:
            available = ', '.join(self._skills_index.keys())
            return f"Skill '{skill_name}' not found.\nAvailable skills: {available}"

        # Check if skill is disabled
        if self.enabled_skills and skill_name in self.enabled_skills and not self.enabled_skills[skill_name]:
            return f"Skill '{skill_name}' is disabled in profile configuration."

        skill_file = self._skills_index[skill_name]
        try:
            content = skill_file.read_text(encoding="utf-8")
            # Remove frontmatter, return instructions only
            content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
            return f"Loaded skill: {skill_name}\n\n{content}"
        except Exception as e:
            return f"Error loading skill '{skill_name}': {e}"

    def _get_tool_schema(self) -> dict:
        """Get load_skill tool schema"""
        available_skills = list(self._skills_index.keys())
        skills_list = '\n'.join(f"- {name}" for name in available_skills)

        return {
            "type": "function",
            "function": {
                "name": self.TOOL_LOAD_SKILL,
                "description": (
                    f"Load a specialized skill to access domain-specific knowledge and workflows.\n\n"
                    f"Available skills:\n{skills_list}\n\n"
                    f"Returns the skill's instructions and context."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": f"Name of the skill to load. Available: {', '.join(available_skills)}"
                        }
                    },
                    "required": ["skill_name"],
                },
            },
        }

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject load_skill tool"""
        if not self._skills_index:
            return handler(request)

        tools = list(request.tools or [])
        tools.append(self._get_tool_schema())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Async: Inject load_skill tool"""
        if not self._skills_index:
            return await handler(request)

        tools = list(request.tools or [])
        tools.append(self._get_tool_schema())
        return await handler(request.override(tools=tools))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """Handle load_skill tool calls"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")

        if tool_name == self.TOOL_LOAD_SKILL:
            args = tool_call.get("args", {})
            skill_name = args.get("skill_name", "")
            result = self._load_skill_impl(skill_name)
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """Async: Handle load_skill tool calls"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")

        if tool_name == self.TOOL_LOAD_SKILL:
            args = tool_call.get("args", {})
            skill_name = args.get("skill_name", "")
            result = self._load_skill_impl(skill_name)
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        return await handler(request)
