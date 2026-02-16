"""Agent loader for .md file format."""

from pathlib import Path

import yaml

from .types import AgentConfig


class AgentLoader:
    """Load agent definitions from .md files with YAML frontmatter."""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root
        self._agents: dict[str, AgentConfig] = {}

    def load_all(self) -> dict[str, AgentConfig]:
        """Load all agents by priority (low -> high, later overrides earlier)."""
        # 1. Built-in agents (lowest priority)
        builtin_dir = Path(__file__).parent.parent.parent / "agents"
        self._load_from_dir(builtin_dir)

        # 2. User-level agents
        user_dir = Path.home() / ".leon" / "agents"
        self._load_from_dir(user_dir)

        # 3. Project-level agents (highest priority)
        if self.workspace_root:
            project_dir = self.workspace_root / ".leon" / "agents"
            self._load_from_dir(project_dir)

        return self._agents

    def _load_from_dir(self, dir_path: Path) -> None:
        """Load all .md files from a directory."""
        if not dir_path.exists():
            return

        for md_file in dir_path.glob("*.md"):
            config = self._parse_agent_file(md_file)
            if config:
                self._agents[config.name] = config  # Override lower priority

    def _parse_agent_file(self, path: Path) -> AgentConfig | None:
        """Parse Markdown file with YAML frontmatter."""
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return None

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return None

        if not frontmatter or "name" not in frontmatter:
            return None

        system_prompt = parts[2].strip()

        return AgentConfig(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            tools=frontmatter.get("tools", []),
            system_prompt=system_prompt,
            max_turns=frontmatter.get("max_turns", 50),
            model=frontmatter.get("model"),
        )

    def get_agent(self, name: str) -> AgentConfig | None:
        """Get a specific agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        return list(self._agents.keys())
