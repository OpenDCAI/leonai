"""Panel data service — File-system CRUD for Members, Tasks, Library, Profile."""

import json
import time
from pathlib import Path
from typing import Any

import yaml

LEON_HOME = Path.home() / ".leon"
MEMBERS_DIR = LEON_HOME / "members"
LIBRARY_DIR = LEON_HOME / "library"
CONFIG_PATH = LEON_HOME / "config.json"


def ensure_directories() -> None:
    """Ensure all required directories exist. Called at app startup."""
    MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    (LIBRARY_DIR / "skills").mkdir(exist_ok=True)
    (LIBRARY_DIR / "agents").mkdir(exist_ok=True)


# ── Helpers ──

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
    """Parse agent.md with YAML frontmatter."""
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
    """Write agent.md with YAML frontmatter."""
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


# ── Member CRUD ──

def _member_to_dict(member_dir: Path) -> dict[str, Any] | None:
    """Read a member directory into a dict."""
    agent_md = member_dir / "agent.md"
    meta_path = member_dir / "meta.json"
    config_path = member_dir / "config.json"

    parsed = _parse_agent_md(agent_md)
    if not parsed:
        return None

    meta = _read_json(meta_path, {"status": "draft", "version": "0.1.0"})
    config = _read_json(config_path, {})

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
        "status": "draft",
        "version": "0.1.0",
        "created_at": now,
        "updated_at": now,
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

    # Update meta if status changed
    if "status" in updates:
        meta = _read_json(member_dir / "meta.json", {})
        meta["status"] = updates["status"]
        meta["updated_at"] = int(time.time() * 1000)
        _write_json(member_dir / "meta.json", meta)

    # Update agent.md if name/description changed
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

    # Handle prompt separately — it lives in agent.md
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

    # Update config.json for tools/mcps/skills/subAgents
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
    import shutil
    member_dir = MEMBERS_DIR / member_id
    if not member_dir.is_dir():
        return False
    shutil.rmtree(member_dir)
    return True

# ── Tasks CRUD (SQLite — unchanged) ──

import sqlite3
from backend.web.core.config import DB_PATH


def _ensure_tasks_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS panel_tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assignee_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            progress INTEGER DEFAULT 0,
            deadline TEXT DEFAULT '',
            created_at INTEGER NOT NULL
        )
    """)


def _tasks_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_tasks_table(conn)
    return conn


def list_tasks() -> list[dict[str, Any]]:
    with _tasks_conn() as conn:
        rows = conn.execute("SELECT * FROM panel_tasks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def create_task(**fields: Any) -> dict[str, Any]:
    now = int(time.time() * 1000)
    tid = str(now)
    with _tasks_conn() as conn:
        conn.execute(
            "INSERT INTO panel_tasks (id,title,description,assignee_id,status,priority,progress,deadline,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (tid, fields.get("title", "新任务"), fields.get("description", ""), fields.get("assignee_id", ""),
             "pending", fields.get("priority", "medium"), 0, fields.get("deadline", ""), now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM panel_tasks WHERE id = ?", (tid,)).fetchone()
        return dict(row)


def update_task(task_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"title", "description", "assignee_id", "status", "priority", "progress", "deadline"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        with _tasks_conn() as conn:
            row = conn.execute("SELECT * FROM panel_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _tasks_conn() as conn:
        conn.execute(f"UPDATE panel_tasks SET {set_clause} WHERE id = ?", (*updates.values(), task_id))
        conn.commit()
        row = conn.execute("SELECT * FROM panel_tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

def delete_task(task_id: str) -> bool:
    with _tasks_conn() as conn:
        cur = conn.execute("DELETE FROM panel_tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0


def bulk_update_task_status(ids: list[str], status: str) -> int:
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    progress_update = ""
    if status == "completed":
        progress_update = ", progress = 100"
    elif status == "pending":
        progress_update = ", progress = 0"
    with _tasks_conn() as conn:
        cur = conn.execute(
            f"UPDATE panel_tasks SET status = ?{progress_update} WHERE id IN ({placeholders})",
            (status, *ids),
        )
        conn.commit()
        return cur.rowcount


# ── Library CRUD (file system) ──

def list_library(resource_type: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if resource_type == "skill":
        skills_dir = LIBRARY_DIR / "skills"
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir():
                    meta = _read_json(d / "meta.json", {})
                    results.append({
                        "id": d.name,
                        "type": "skill",
                        "name": meta.get("name", d.name),
                        "desc": meta.get("desc", ""),
                        "category": meta.get("category", "未分类"),
                        "created_at": meta.get("created_at", 0),
                        "updated_at": meta.get("updated_at", 0),
                    })
    elif resource_type == "agent":
        agents_dir = LIBRARY_DIR / "agents"
        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.md")):
                meta_path = f.with_suffix(".json")
                meta = _read_json(meta_path, {})
                results.append({
                    "id": f.stem,
                    "type": "agent",
                    "name": meta.get("name", f.stem),
                    "desc": meta.get("desc", ""),
                    "category": meta.get("category", "未分类"),
                    "created_at": meta.get("created_at", 0),
                    "updated_at": meta.get("updated_at", 0),
                })
    elif resource_type == "mcp":
        mcp_path = LIBRARY_DIR / ".mcp.json"
        mcp_data = _read_json(mcp_path, {"mcpServers": {}})
        for name, cfg in mcp_data.get("mcpServers", {}).items():
            results.append({
                "id": name,
                "type": "mcp",
                "name": name,
                "desc": cfg.get("desc", ""),
                "category": cfg.get("category", "未分类"),
                "created_at": cfg.get("created_at", 0),
                "updated_at": cfg.get("updated_at", 0),
            })
    return results

def create_resource(resource_type: str, name: str, desc: str = "", category: str = "") -> dict[str, Any]:
    now = int(time.time() * 1000)
    cat = category or "未分类"
    if resource_type == "skill":
        rid = name.lower().replace(" ", "-")
        skill_dir = LIBRARY_DIR / "skills" / rid
        skill_dir.mkdir(parents=True, exist_ok=True)
        _write_json(skill_dir / "meta.json", {
            "name": name, "desc": desc, "category": cat,
            "created_at": now, "updated_at": now,
        })
        (skill_dir / "SKILL.md").write_text(f"# {name}\n\n{desc}\n", encoding="utf-8")
        return {"id": rid, "type": "skill", "name": name, "desc": desc, "category": cat, "created_at": now, "updated_at": now}
    elif resource_type == "agent":
        rid = name.lower().replace(" ", "-")
        agents_dir = LIBRARY_DIR / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        _write_json(agents_dir / f"{rid}.json", {
            "name": name, "desc": desc, "category": cat,
            "created_at": now, "updated_at": now,
        })
        (agents_dir / f"{rid}.md").write_text(f"---\nname: {rid}\ndescription: {desc}\n---\n\n# {name}\n", encoding="utf-8")
        return {"id": rid, "type": "agent", "name": name, "desc": desc, "category": cat, "created_at": now, "updated_at": now}
    elif resource_type == "mcp":
        mcp_path = LIBRARY_DIR / ".mcp.json"
        mcp_data = _read_json(mcp_path, {"mcpServers": {}})
        mcp_data["mcpServers"][name] = {
            "desc": desc, "category": cat,
            "created_at": now, "updated_at": now,
        }
        _write_json(mcp_path, mcp_data)
        return {"id": name, "type": "mcp", "name": name, "desc": desc, "category": cat, "created_at": now, "updated_at": now}
    raise ValueError(f"Unknown resource type: {resource_type}")


def update_resource(resource_type: str, resource_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"name", "desc", "category"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    now = int(time.time() * 1000)
    if resource_type == "skill":
        meta_path = LIBRARY_DIR / "skills" / resource_id / "meta.json"
        if not meta_path.exists():
            return None
        meta = _read_json(meta_path, {})
        meta.update(updates)
        meta["updated_at"] = now
        _write_json(meta_path, meta)
        return {"id": resource_id, "type": "skill", **meta}
    elif resource_type == "agent":
        meta_path = LIBRARY_DIR / "agents" / f"{resource_id}.json"
        if not meta_path.exists():
            return None
        meta = _read_json(meta_path, {})
        meta.update(updates)
        meta["updated_at"] = now
        _write_json(meta_path, meta)
        return {"id": resource_id, "type": "agent", **meta}
    elif resource_type == "mcp":
        mcp_path = LIBRARY_DIR / ".mcp.json"
        mcp_data = _read_json(mcp_path, {"mcpServers": {}})
        if resource_id not in mcp_data.get("mcpServers", {}):
            return None
        mcp_data["mcpServers"][resource_id].update(updates)
        mcp_data["mcpServers"][resource_id]["updated_at"] = now
        _write_json(mcp_path, mcp_data)
        entry = mcp_data["mcpServers"][resource_id]
        return {"id": resource_id, "type": "mcp", "name": entry.get("name", resource_id), **entry}
    return None

def delete_resource(resource_type: str, resource_id: str) -> bool:
    import shutil
    if resource_type == "skill":
        target = LIBRARY_DIR / "skills" / resource_id
        if not target.is_dir():
            return False
        shutil.rmtree(target)
        return True
    elif resource_type == "agent":
        md_path = LIBRARY_DIR / "agents" / f"{resource_id}.md"
        json_path = LIBRARY_DIR / "agents" / f"{resource_id}.json"
        found = False
        if md_path.exists():
            md_path.unlink()
            found = True
        if json_path.exists():
            json_path.unlink()
            found = True
        return found
    elif resource_type == "mcp":
        mcp_path = LIBRARY_DIR / ".mcp.json"
        mcp_data = _read_json(mcp_path, {"mcpServers": {}})
        if resource_id not in mcp_data.get("mcpServers", {}):
            return False
        del mcp_data["mcpServers"][resource_id]
        _write_json(mcp_path, mcp_data)
        return True
    return False


def get_resource_used_by(resource_type: str, resource_name: str) -> int:
    """Count how many members use a given resource by name."""
    config_key = {"skill": "skills", "mcp": "mcps", "agent": "subAgents"}.get(resource_type, "")
    if not config_key:
        return 0
    count = 0
    for member in list_members():
        items = member.get("config", {}).get(config_key, [])
        if any(i.get("name") == resource_name for i in items):
            count += 1
    return count


# ── Profile (config.json) ──

def get_profile() -> dict[str, Any]:
    cfg = _read_json(CONFIG_PATH, {})
    profile = cfg.get("profile", {})
    return {
        "name": profile.get("name", "用户名"),
        "initials": profile.get("initials", "YZ"),
        "email": profile.get("email", "user@example.com"),
    }


def update_profile(**fields: Any) -> dict[str, Any]:
    allowed = {"name", "initials", "email"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_profile()
    cfg = _read_json(CONFIG_PATH, {})
    profile = cfg.get("profile", {})
    profile.update(updates)
    cfg["profile"] = profile
    _write_json(CONFIG_PATH, cfg)
    return get_profile()


# ── Backward compatibility aliases ──

list_staff = list_members
get_staff = get_member
create_staff = create_member
update_staff = update_member
update_staff_config = update_member_config
publish_staff = publish_member
delete_staff = delete_member
init_panel_tables = ensure_directories
