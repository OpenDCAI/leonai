"""Panel data service — SQLite CRUD for Staff, Tasks, Library, Profile."""

import json
import sqlite3
import time
from typing import Any

from backend.web.core.config import DB_PATH

# ── Table init ──

def _ensure_panel_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS panel_staff (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT DEFAULT '',
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            version TEXT DEFAULT '0.1.0',
            config TEXT DEFAULT '{}',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
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
        );
        CREATE TABLE IF NOT EXISTS panel_library (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            desc TEXT DEFAULT '',
            category TEXT DEFAULT '',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS panel_profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT DEFAULT '用户名',
            initials TEXT DEFAULT 'YZ',
            email TEXT DEFAULT 'user@example.com'
        );
    """)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_panel_tables(conn)
    return conn


def init_panel_tables() -> None:
    """Called at app startup to ensure tables exist."""
    with _conn() as conn:
        pass  # tables created by _ensure_panel_tables in _conn()


# ── Staff CRUD ──

def _row_to_staff(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["config"] = json.loads(d["config"]) if d.get("config") else {}
    return d


def list_staff() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM panel_staff ORDER BY created_at DESC").fetchall()
        return [_row_to_staff(r) for r in rows]


def get_staff(staff_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM panel_staff WHERE id = ?", (staff_id,)).fetchone()
        return _row_to_staff(row) if row else None


def create_staff(name: str, description: str = "") -> dict[str, Any]:
    now = int(time.time() * 1000)
    sid = str(now)
    default_config = {"prompt": "", "rules": "", "memory": "", "tools": [], "mcps": [], "skills": [], "subAgents": []}
    with _conn() as conn:
        conn.execute(
            "INSERT INTO panel_staff (id,name,role,description,status,version,config,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, name, "", description, "draft", "0.1.0", json.dumps(default_config, ensure_ascii=False), now, now),
        )
        conn.commit()
    return get_staff(sid)  # type: ignore


def update_staff(staff_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"name", "role", "description", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_staff(staff_id)
    updates["updated_at"] = int(time.time() * 1000)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _conn() as conn:
        conn.execute(f"UPDATE panel_staff SET {set_clause} WHERE id = ?", (*updates.values(), staff_id))
        conn.commit()
    return get_staff(staff_id)


def update_staff_config(staff_id: str, config_patch: dict[str, Any]) -> dict[str, Any] | None:
    staff = get_staff(staff_id)
    if not staff:
        return None
    cfg = staff["config"]
    cfg.update({k: v for k, v in config_patch.items() if v is not None})
    now = int(time.time() * 1000)
    with _conn() as conn:
        conn.execute("UPDATE panel_staff SET config = ?, updated_at = ? WHERE id = ?",
                      (json.dumps(cfg, ensure_ascii=False), now, staff_id))
        conn.commit()
    return get_staff(staff_id)


def publish_staff(staff_id: str, bump_type: str = "patch") -> dict[str, Any] | None:
    staff = get_staff(staff_id)
    if not staff:
        return None
    parts = staff["version"].split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump_type == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump_type == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_version = f"{major}.{minor}.{patch}"
    now = int(time.time() * 1000)
    with _conn() as conn:
        conn.execute("UPDATE panel_staff SET version = ?, status = 'active', updated_at = ? WHERE id = ?",
                      (new_version, now, staff_id))
        conn.commit()
    return get_staff(staff_id)


def delete_staff(staff_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM panel_staff WHERE id = ?", (staff_id,))
        conn.commit()
        return cur.rowcount > 0


# ── Tasks CRUD ──

def list_tasks() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM panel_tasks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def create_task(**fields: Any) -> dict[str, Any]:
    now = int(time.time() * 1000)
    tid = str(now)
    with _conn() as conn:
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
        with _conn() as conn:
            row = conn.execute("SELECT * FROM panel_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _conn() as conn:
        conn.execute(f"UPDATE panel_tasks SET {set_clause} WHERE id = ?", (*updates.values(), task_id))
        conn.commit()
        row = conn.execute("SELECT * FROM panel_tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def delete_task(task_id: str) -> bool:
    with _conn() as conn:
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
    with _conn() as conn:
        cur = conn.execute(
            f"UPDATE panel_tasks SET status = ?{progress_update} WHERE id IN ({placeholders})",
            (status, *ids),
        )
        conn.commit()
        return cur.rowcount


# ── Library CRUD ──

def list_library(resource_type: str) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM panel_library WHERE type = ? ORDER BY created_at DESC", (resource_type,)).fetchall()
        return [dict(r) for r in rows]


def create_resource(resource_type: str, name: str, desc: str = "", category: str = "") -> dict[str, Any]:
    now = int(time.time() * 1000)
    rid = f"{resource_type[0]}{now}"
    with _conn() as conn:
        conn.execute(
            "INSERT INTO panel_library (id,type,name,desc,category,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (rid, resource_type, name, desc, category or "未分类", now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM panel_library WHERE id = ?", (rid,)).fetchone()
        return dict(row)


def update_resource(resource_type: str, resource_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"name", "desc", "category"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        with _conn() as conn:
            row = conn.execute("SELECT * FROM panel_library WHERE id = ? AND type = ?", (resource_id, resource_type)).fetchone()
            return dict(row) if row else None
    updates["updated_at"] = int(time.time() * 1000)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _conn() as conn:
        conn.execute(f"UPDATE panel_library SET {set_clause} WHERE id = ? AND type = ?", (*updates.values(), resource_id, resource_type))
        conn.commit()
        row = conn.execute("SELECT * FROM panel_library WHERE id = ? AND type = ?", (resource_id, resource_type)).fetchone()
        return dict(row) if row else None


def delete_resource(resource_type: str, resource_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM panel_library WHERE id = ? AND type = ?", (resource_id, resource_type))
        conn.commit()
        return cur.rowcount > 0


def get_resource_used_by(resource_type: str, resource_name: str) -> int:
    """Count how many staff use a given resource by name."""
    config_key = {"skill": "skills", "mcp": "mcps", "agent": "subAgents"}.get(resource_type, "")
    if not config_key:
        return 0
    count = 0
    for staff in list_staff():
        items = staff.get("config", {}).get(config_key, [])
        if any(i.get("name") == resource_name for i in items):
            count += 1
    return count


# ── Profile ──

def get_profile() -> dict[str, Any]:
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO panel_profile (id) VALUES (1)")
        conn.commit()
        row = conn.execute("SELECT * FROM panel_profile WHERE id = 1").fetchone()
        return dict(row)


def update_profile(**fields: Any) -> dict[str, Any]:
    allowed = {"name", "initials", "email"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_profile()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _conn() as conn:
        conn.execute(f"UPDATE panel_profile SET {set_clause} WHERE id = 1", (*updates.values(),))
        conn.commit()
    return get_profile()
