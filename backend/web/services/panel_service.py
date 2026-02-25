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


# ── Seed data ──

_SEED_STAFF: list[dict[str, Any]] = [
    {"id": "1", "name": "Code Reviewer", "role": "高级代码审查员", "description": "审查代码质量，提供改进建议和最佳实践指导", "status": "active", "version": "1.2.0",
     "config": {"prompt": "You are a senior code reviewer. Your job is to:\n\n1. Identify bugs, security issues, and performance problems\n2. Suggest improvements following best practices\n3. Provide clear, actionable feedback\n\nAlways be constructive and explain *why* something should change.",
                "rules": "## Rules\n\n1. 始终使用中文回复\n2. 代码示例需包含注释\n3. 不提供生产环境的敏感信息",
                "memory": "## Memory\n\n- 用户偏好：TypeScript + React 技术栈\n- 项目约定：使用 ESLint + Prettier",
                "tools": [{"id": "1", "name": "Web Search", "desc": "搜索互联网获取最新信息", "enabled": True}, {"id": "2", "name": "Code Executor", "desc": "在沙盒中运行代码", "enabled": True}, {"id": "3", "name": "File Reader", "desc": "读取和分析文件内容", "enabled": False}],
                "mcps": [{"id": "1", "name": "GitHub MCP", "desc": "访问 GitHub 仓库和 PR", "enabled": True}, {"id": "2", "name": "Notion MCP", "desc": "读取 Notion 文档和数据库", "enabled": False}],
                "skills": [{"id": "1", "name": "代码审查", "desc": "深度代码审查和建议", "enabled": True}, {"id": "2", "name": "性能分析", "desc": "识别性能瓶颈", "enabled": True}, {"id": "3", "name": "安全扫描", "desc": "检查常见安全漏洞", "enabled": True}, {"id": "4", "name": "文档生成", "desc": "自动生成 API 文档", "enabled": False}],
                "subAgents": [{"id": "1", "name": "Linter Bot", "desc": "专注于代码风格和格式检查"}]}},
    {"id": "2", "name": "Data Analyst", "role": "数据分析师", "description": "分析数据集，生成可视化报告和洞察", "status": "active", "version": "1.0.0",
     "config": {"prompt": "You are a data analyst.", "rules": "", "memory": "",
                "tools": [{"id": "1", "name": "Python Runner", "desc": "运行 Python 数据分析脚本", "enabled": True}, {"id": "2", "name": "Chart Generator", "desc": "生成数据可视化图表", "enabled": True}, {"id": "3", "name": "SQL Query", "desc": "执行 SQL 查询", "enabled": True}, {"id": "4", "name": "Web Search", "desc": "搜索互联网获取最新信息", "enabled": True}, {"id": "5", "name": "File Reader", "desc": "读取和分析文件内容", "enabled": True}],
                "mcps": [{"id": "1", "name": "GitHub MCP", "desc": "访问 GitHub 仓库和 PR", "enabled": True}, {"id": "2", "name": "Notion MCP", "desc": "读取 Notion 文档和数据库", "enabled": True}, {"id": "3", "name": "Linear MCP", "desc": "管理 Linear 项目和 Issues", "enabled": True}],
                "skills": [{"id": "1", "name": "数据清洗", "desc": "自动处理和清洗数据集", "enabled": True}, {"id": "2", "name": "统计分析", "desc": "描述性和推断性统计", "enabled": True}, {"id": "3", "name": "可视化", "desc": "生成图表和仪表盘", "enabled": True}, {"id": "4", "name": "报告生成", "desc": "自动生成分析报告", "enabled": True}, {"id": "5", "name": "异常检测", "desc": "识别数据异常值", "enabled": True}, {"id": "6", "name": "预测建模", "desc": "时间序列预测", "enabled": False}],
                "subAgents": [{"id": "1", "name": "Chart Bot", "desc": "专注于图表生成"}, {"id": "2", "name": "SQL Bot", "desc": "专注于 SQL 查询优化"}]}},
    {"id": "3", "name": "Writing Assistant", "role": "文案助手", "description": "辅助文案撰写、翻译和内容优化", "status": "draft", "version": "0.3.0",
     "config": {"prompt": "You are a writing assistant.", "rules": "", "memory": "",
                "tools": [{"id": "1", "name": "Web Search", "desc": "搜索互联网获取最新信息", "enabled": True}, {"id": "2", "name": "Translator", "desc": "多语言翻译", "enabled": True}],
                "mcps": [{"id": "1", "name": "Notion MCP", "desc": "读取 Notion 文档和数据库", "enabled": True}],
                "skills": [{"id": "1", "name": "文案撰写", "desc": "撰写营销文案", "enabled": True}, {"id": "2", "name": "翻译", "desc": "中英互译", "enabled": True}, {"id": "3", "name": "校对", "desc": "语法和拼写检查", "enabled": True}],
                "subAgents": []}},
    {"id": "4", "name": "DevOps Engineer", "role": "运维工程师", "description": "自动化部署流程，监控系统健康状态", "status": "inactive", "version": "2.1.0",
     "config": {"prompt": "You are a DevOps engineer.", "rules": "", "memory": "",
                "tools": [{"id": "1", "name": "Shell Executor", "desc": "执行 Shell 命令", "enabled": True}, {"id": "2", "name": "Docker CLI", "desc": "管理 Docker 容器", "enabled": True}, {"id": "3", "name": "K8s CLI", "desc": "管理 Kubernetes 集群", "enabled": True}, {"id": "4", "name": "AWS CLI", "desc": "管理 AWS 资源", "enabled": True}, {"id": "5", "name": "Terraform", "desc": "基础设施即代码", "enabled": True}, {"id": "6", "name": "Ansible", "desc": "配置管理", "enabled": False}, {"id": "7", "name": "Monitoring", "desc": "监控告警", "enabled": True}],
                "mcps": [{"id": "1", "name": "GitHub MCP", "desc": "访问 GitHub 仓库和 PR", "enabled": True}, {"id": "2", "name": "Slack MCP", "desc": "发送消息和管理频道", "enabled": True}, {"id": "3", "name": "Linear MCP", "desc": "管理项目和 Issues", "enabled": True}, {"id": "4", "name": "PagerDuty MCP", "desc": "告警管理", "enabled": True}],
                "skills": [{"id": "1", "name": "CI/CD", "desc": "持续集成部署", "enabled": True}, {"id": "2", "name": "容器编排", "desc": "Docker/K8s 管理", "enabled": True}, {"id": "3", "name": "监控告警", "desc": "系统监控和告警", "enabled": True}, {"id": "4", "name": "日志分析", "desc": "日志收集和分析", "enabled": True}, {"id": "5", "name": "安全加固", "desc": "系统安全配置", "enabled": True}, {"id": "6", "name": "性能调优", "desc": "系统性能优化", "enabled": True}, {"id": "7", "name": "灾备恢复", "desc": "备份和恢复策略", "enabled": True}, {"id": "8", "name": "成本优化", "desc": "云资源成本优化", "enabled": False}],
                "subAgents": [{"id": "1", "name": "Monitor Bot", "desc": "专注于监控告警"}, {"id": "2", "name": "Deploy Bot", "desc": "专注于自动化部署"}, {"id": "3", "name": "Security Bot", "desc": "专注于安全扫描"}]}},
    {"id": "5", "name": "Security Auditor", "role": "安全审计员", "description": "检查OWASP漏洞，审查依赖安全性", "status": "active", "version": "1.1.0",
     "config": {"prompt": "You are a security auditor.", "rules": "", "memory": "",
                "tools": [{"id": "1", "name": "SAST Scanner", "desc": "静态代码分析", "enabled": True}, {"id": "2", "name": "Dependency Check", "desc": "依赖漏洞扫描", "enabled": True}, {"id": "3", "name": "Web Search", "desc": "搜索安全公告", "enabled": True}, {"id": "4", "name": "Shell Executor", "desc": "执行安全工具", "enabled": True}],
                "mcps": [{"id": "1", "name": "GitHub MCP", "desc": "访问 GitHub 仓库和 PR", "enabled": True}, {"id": "2", "name": "Linear MCP", "desc": "管理安全 Issues", "enabled": True}],
                "skills": [{"id": "1", "name": "OWASP 扫描", "desc": "检查 OWASP Top 10", "enabled": True}, {"id": "2", "name": "依赖审计", "desc": "审查第三方依赖", "enabled": True}, {"id": "3", "name": "渗透测试", "desc": "模拟攻击测试", "enabled": True}, {"id": "4", "name": "合规检查", "desc": "安全合规审计", "enabled": True}, {"id": "5", "name": "密钥扫描", "desc": "检测泄露的密钥", "enabled": True}],
                "subAgents": [{"id": "1", "name": "CVE Bot", "desc": "专注于 CVE 漏洞追踪"}]}},
    {"id": "6", "name": "API Designer", "role": "API 设计师", "description": "设计RESTful和GraphQL接口，生成文档", "status": "draft", "version": "0.2.0",
     "config": {"prompt": "You are an API designer.", "rules": "", "memory": "",
                "tools": [{"id": "1", "name": "OpenAPI Editor", "desc": "编辑 OpenAPI 规范", "enabled": True}, {"id": "2", "name": "Mock Server", "desc": "生成 Mock API", "enabled": True}, {"id": "3", "name": "Web Search", "desc": "搜索 API 最佳实践", "enabled": True}],
                "mcps": [{"id": "1", "name": "GitHub MCP", "desc": "访问 GitHub 仓库和 PR", "enabled": True}],
                "skills": [{"id": "1", "name": "REST 设计", "desc": "RESTful API 设计", "enabled": True}, {"id": "2", "name": "GraphQL 设计", "desc": "GraphQL Schema 设计", "enabled": True}, {"id": "3", "name": "文档生成", "desc": "自动生成 API 文档", "enabled": True}, {"id": "4", "name": "版本管理", "desc": "API 版本策略", "enabled": True}],
                "subAgents": []}},
]

_SEED_TASKS: list[dict[str, Any]] = [
    {"id": "1", "title": "审查 PR #142 的代码变更", "description": "需要审查 142 号 PR 中对认证模块的修改，包含 15 个文件变更。", "assignee_id": "1", "status": "running", "priority": "high", "progress": 65, "deadline": "2026-02-25"},
    {"id": "2", "title": "生成本月用户行为分析报告", "description": "汇总本月的用户留存、转化率和活跃度数据，生成可视化报告。", "assignee_id": "2", "status": "running", "priority": "medium", "progress": 40, "deadline": "2026-02-28"},
    {"id": "3", "title": "优化产品介绍页文案", "description": "根据 A/B 测试结果重写产品介绍页面的标题和描述文案。", "assignee_id": "3", "status": "pending", "priority": "low", "progress": 0, "deadline": "2026-03-05"},
    {"id": "4", "title": "检查 API 端点安全漏洞", "description": "完成对所有公开 API 端点的安全扫描，未发现高危漏洞。", "assignee_id": "1", "status": "completed", "priority": "high", "progress": 100, "deadline": "2026-02-20"},
    {"id": "5", "title": "部署 staging 环境更新", "description": "部署失败：Docker 镜像构建超时，需要检查 CI/CD 配置。", "assignee_id": "4", "status": "failed", "priority": "high", "progress": 80, "deadline": "2026-02-22"},
    {"id": "6", "title": "分析竞品用户留存数据", "description": "对比分析主要竞品的 30 天用户留存率和活跃用户增长趋势。", "assignee_id": "2", "status": "pending", "priority": "medium", "progress": 0, "deadline": "2026-03-01"},
    {"id": "7", "title": "编写用户手册第三章", "description": "编写关于高级配置和自定义设置的用户手册章节。", "assignee_id": "3", "status": "running", "priority": "low", "progress": 25, "deadline": "2026-03-10"},
    {"id": "8", "title": "重构认证模块", "description": "将现有 JWT 认证迁移到 OAuth 2.0 + PKCE 流程。", "assignee_id": "1", "status": "pending", "priority": "high", "progress": 0, "deadline": "2026-03-15"},
]

_SEED_LIBRARY: list[dict[str, Any]] = [
    {"id": "s1", "type": "skill", "name": "代码审查", "desc": "深度代码审查，覆盖质量、性能、安全", "category": "开发"},
    {"id": "s2", "type": "skill", "name": "性能分析", "desc": "识别性能瓶颈并提供优化建议", "category": "开发"},
    {"id": "s3", "type": "skill", "name": "安全扫描", "desc": "检查 OWASP Top 10 安全漏洞", "category": "安全"},
    {"id": "s4", "type": "skill", "name": "文档生成", "desc": "从代码生成 API 文档和使用说明", "category": "文档"},
    {"id": "s5", "type": "skill", "name": "数据清洗", "desc": "自动处理和清洗数据集", "category": "数据"},
    {"id": "s6", "type": "skill", "name": "测试编写", "desc": "为函数和组件生成单元测试", "category": "开发"},
    {"id": "m1", "type": "mcp", "name": "GitHub MCP", "desc": "访问 GitHub 仓库、PR、Issues", "category": "开发"},
    {"id": "m2", "type": "mcp", "name": "Notion MCP", "desc": "读取 Notion 页面和数据库", "category": "知识"},
    {"id": "m3", "type": "mcp", "name": "Slack MCP", "desc": "发送消息和管理 Slack 频道", "category": "通信"},
    {"id": "m4", "type": "mcp", "name": "Linear MCP", "desc": "管理 Linear 项目和 Issues", "category": "项目"},
    {"id": "a1", "type": "agent", "name": "Linter Bot", "desc": "代码风格和格式检查", "category": "开发"},
    {"id": "a2", "type": "agent", "name": "Translator", "desc": "多语言翻译引擎", "category": "内容"},
    {"id": "a3", "type": "agent", "name": "Summarizer", "desc": "文档摘要生成", "category": "内容"},
]


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Insert seed data only when tables are empty."""
    if conn.execute("SELECT COUNT(*) FROM panel_staff").fetchone()[0] > 0:
        return
    now = int(time.time() * 1000)
    for s in _SEED_STAFF:
        conn.execute(
            "INSERT INTO panel_staff (id,name,role,description,status,version,config,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (s["id"], s["name"], s["role"], s["description"], s["status"], s["version"], json.dumps(s["config"], ensure_ascii=False), now, now),
        )
    for t in _SEED_TASKS:
        conn.execute(
            "INSERT INTO panel_tasks (id,title,description,assignee_id,status,priority,progress,deadline,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (t["id"], t["title"], t["description"], t["assignee_id"], t["status"], t["priority"], t["progress"], t["deadline"], now),
        )
    for r in _SEED_LIBRARY:
        conn.execute(
            "INSERT INTO panel_library (id,type,name,desc,category,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (r["id"], r["type"], r["name"], r["desc"], r["category"], now, now),
        )
    conn.execute("INSERT OR IGNORE INTO panel_profile (id) VALUES (1)")
    conn.commit()


def init_panel_tables() -> None:
    """Called at app startup to ensure tables + seed data exist."""
    with _conn() as conn:
        _seed_if_empty(conn)


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
