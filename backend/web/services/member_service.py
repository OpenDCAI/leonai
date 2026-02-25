"""Member CRUD — file-system based (~/.leon/members/)."""

import json
import shutil
import time
from pathlib import Path
from typing import Any

import yaml

LEON_HOME = Path.home() / ".leon"
MEMBERS_DIR = LEON_HOME / "members"


def ensure_members_dir() -> None:
    MEMBERS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_agent_md(path: Path) -> dict[str, Any] | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not fm or "name" not in fm:
        return None
    return {
        "name": fm["name"],
        "description": fm.get("description", ""),
        "model": fm.get("model"),
        "tools": fm.get("tools", ["*"]),
        "system_prompt": parts[2].strip(),
    }

def _write_agent_md(path: Path, name: str, description: str = "",
                    model: str | None = None, tools: list[str] | None = None,
                    system_prompt: str = "") -> None:
    fm: dict[str, Any] = {"name": name}
    if description:
        fm["description"] = description
    if model:
        fm["model"] = model
    if tools and tools != ["*"]:
        fm["tools"] = tools
    content = f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False).strip()}\n---\n\n{system_prompt}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _member_to_dict(member_dir: Path) -> dict[str, Any] | None:
    parsed = _parse_agent_md(member_dir / "agent.md")
    if not parsed:
        return None
    meta = _read_json(member_dir / "meta.json", {"status": "draft", "version": "0.1.0"})
    config = _read_json(member_dir / "config.json", {})
    return {
        "id": member_dir.name,
        "name": parsed["name"],
        "description": parsed["description"],
        "model": parsed.get("model"),
        "status": meta.get("status", "draft"),
        "version": meta.get("version", "0.1.0"),
        "config": {
            "prompt": parsed.get("system_prompt", ""),
            "rules": "",
            "memory": "",
            "tools": config.get("tools", []),
            "mcps": config.get("mcps", []),
            "skills": config.get("skills", []),
            "subAgents": config.get("subAgents", []),
        },
        "created_at": meta.get("created_at", 0),
        "updated_at": meta.get("updated_at", 0),
    }


LEON_BUILTIN: dict[str, Any] = {
    "id": "__leon__",
    "name": "Leon",
    "description": "通用数字成员，随时准备为你工作",
    "status": "active",
    "version": "1.0.0",
    "config": {"prompt": "", "rules": "", "memory": "", "tools": [], "mcps": [], "skills": [], "subAgents": []},
    "created_at": 0,
    "updated_at": 0,
    "builtin": True,
}

def list_members() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = [LEON_BUILTIN]
    if MEMBERS_DIR.exists():
        for d in sorted(MEMBERS_DIR.iterdir(), reverse=True):
            if d.is_dir() and (d / "agent.md").exists():
                item = _member_to_dict(d)
                if item:
                    results.append(item)
    return results


def get_member(member_id: str) -> dict[str, Any] | None:
    if member_id == "__leon__":
        return LEON_BUILTIN
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return None
    return _member_to_dict(member_dir)


def create_member(name: str, description: str = "") -> dict[str, Any]:
    now = int(time.time() * 1000)
    member_id = str(now)
    member_dir = MEMBERS_DIR / member_id
    member_dir.mkdir(parents=True, exist_ok=True)
    _write_agent_md(member_dir / "agent.md", name=name, description=description)
    _write_json(member_dir / "meta.json", {
        "status": "draft", "version": "0.1.0",
        "created_at": now, "updated_at": now,
    })
    _write_json(member_dir / "config.json", {
        "tools": [], "mcps": [], "skills": [], "subAgents": [],
    })
    return get_member(member_id)  # type: ignore


def update_member(member_id: str, **fields: Any) -> dict[str, Any] | None:
    if member_id == "__leon__":
        return None
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return None
    allowed = {"name", "description", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_member(member_id)
    if "status" in updates:
        meta = _read_json(member_dir / "meta.json", {})
        meta["status"] = updates["status"]
        meta["updated_at"] = int(time.time() * 1000)
        _write_json(member_dir / "meta.json", meta)
    if "name" in updates or "description" in updates:
        parsed = _parse_agent_md(member_dir / "agent.md") or {}
        _write_agent_md(
            member_dir / "agent.md",
            name=updates.get("name", parsed.get("name", "")),
            description=updates.get("description", parsed.get("description", "")),
            model=parsed.get("model"),
            tools=parsed.get("tools"),
            system_prompt=parsed.get("system_prompt", ""),
        )
        meta = _read_json(member_dir / "meta.json", {})
        meta["updated_at"] = int(time.time() * 1000)
        _write_json(member_dir / "meta.json", meta)
    return get_member(member_id)

def update_member_config(member_id: str, config_patch: dict[str, Any]) -> dict[str, Any] | None:
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return None
    if "prompt" in config_patch and config_patch["prompt"] is not None:
        parsed = _parse_agent_md(member_dir / "agent.md") or {}
        _write_agent_md(
            member_dir / "agent.md",
            name=parsed.get("name", ""),
            description=parsed.get("description", ""),
            model=parsed.get("model"),
            tools=parsed.get("tools"),
            system_prompt=config_patch["prompt"],
        )
    config_keys = {"tools", "mcps", "skills", "subAgents", "rules", "memory"}
    cfg_updates = {k: v for k, v in config_patch.items() if k in config_keys and v is not None}
    if cfg_updates:
        cfg = _read_json(member_dir / "config.json", {})
        cfg.update(cfg_updates)
        _write_json(member_dir / "config.json", cfg)
    meta = _read_json(member_dir / "meta.json", {})
    meta["updated_at"] = int(time.time() * 1000)
    _write_json(member_dir / "meta.json", meta)
    return get_member(member_id)


def publish_member(member_id: str, bump_type: str = "patch") -> dict[str, Any] | None:
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return None
    meta = _read_json(member_dir / "meta.json", {})
    parts = meta.get("version", "0.1.0").split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump_type == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump_type == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    meta["version"] = f"{major}.{minor}.{patch}"
    meta["status"] = "active"
    meta["updated_at"] = int(time.time() * 1000)
    _write_json(member_dir / "meta.json", meta)
    return get_member(member_id)


def delete_member(member_id: str) -> bool:
    if member_id == "__leon__":
        return False
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return False
    shutil.rmtree(member_dir)
    return True
