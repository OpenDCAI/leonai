from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import create_leon_agent
from middleware.monitor import AgentState
from middleware.queue import QueueMode, get_queue_manager
from sandbox.config import SandboxConfig
from sandbox.db import DEFAULT_DB_PATH as SANDBOX_DB_PATH
from sandbox.lease import LeaseStore
from sandbox.manager import SandboxManager, lookup_sandbox_for_thread
from sandbox.provider_events import ProviderEventStore
from sandbox.thread_context import set_current_thread_id
from tui.config import ConfigManager

DB_PATH = Path.home() / ".leon" / "leon.db"
SANDBOXES_DIR = Path.home() / ".leon" / "sandboxes"
LOCAL_WORKSPACE_ROOT = Path.cwd().resolve()
IDLE_REAPER_INTERVAL_SEC = 30


# --- Request models ---


class CreateThreadRequest(BaseModel):
    sandbox: str = "local"
    cwd: str | None = None


class RunRequest(BaseModel):
    message: str


class SteerRequest(BaseModel):
    message: str


# --- Agent pool ---


def _available_sandbox_types() -> list[dict[str, Any]]:
    """Scan ~/.leon/sandboxes/ for configured providers."""
    types = [{"name": "local", "available": True}]
    if not SANDBOXES_DIR.exists():
        return types
    skipped_daytona: list[str] = []
    for f in sorted(SANDBOXES_DIR.glob("*.json")):
        name = f.stem
        # @@@daytona-single-type - Daytona SaaS vs self-hosted is config-only (daytona.api_url). Do not surface
        # multiple Daytona config filenames as distinct "sandbox types" in the frontend.
        if name != "daytona" and name.startswith("daytona"):
            skipped_daytona.append(name)
            continue
        try:
            SandboxConfig.load(name)
            types.append({"name": name, "available": True})
        except Exception as e:
            types.append({"name": name, "available": False, "reason": str(e)})
    if skipped_daytona and not any(t.get("name") == "daytona" for t in types):
        types.append(
            {
                "name": "daytona",
                "available": False,
                "reason": f"Found Daytona config(s) {skipped_daytona} but expected ~/.leon/sandboxes/daytona.json",
            }
        )
    return types


def _create_agent_sync(sandbox_name: str, workspace_root: Path | None = None) -> Any:
    """Create a LeonAgent with the given sandbox. Runs in a thread."""
    # @@@ model_name=None lets the profile.yaml value take effect instead of the factory default
    return create_leon_agent(
        model_name=None,
        workspace_root=workspace_root or Path.cwd(),
        sandbox=sandbox_name if sandbox_name != "local" else None,
        verbose=True,
    )


async def _get_or_create_agent(app_obj: FastAPI, sandbox_type: str, thread_id: str | None = None) -> Any:
    """Lazy agent pool — one agent per thread, created on demand."""
    if thread_id:
        set_current_thread_id(thread_id)

    # Per-thread Agent instance: pool key = thread_id:sandbox_type
    # This ensures complete isolation of middleware state (memory, todo, runtime, filesystem, etc.)
    if not thread_id:
        raise ValueError("thread_id is required for agent creation")

    pool_key = f"{thread_id}:{sandbox_type}"
    pool = app_obj.state.agent_pool
    if pool_key in pool:
        return pool[pool_key]

    # For local sandbox, check if thread has custom cwd
    workspace_root = None
    if sandbox_type == "local":
        cwd = app_obj.state.thread_cwd.get(thread_id)
        if cwd:
            workspace_root = Path(cwd).resolve()

    # @@@ agent-init-thread - LeonAgent.__init__ uses run_until_complete, must run in thread
    agent = await asyncio.to_thread(_create_agent_sync, sandbox_type, workspace_root)
    pool[pool_key] = agent
    return agent


def _resolve_thread_sandbox(app_obj: FastAPI, thread_id: str) -> str:
    """Look up sandbox type for a thread: memory cache → SQLite → default 'local'."""
    mapping = app_obj.state.thread_sandbox
    if thread_id in mapping:
        return mapping[thread_id]
    detected = lookup_sandbox_for_thread(thread_id)
    if detected:
        mapping[thread_id] = detected
        return detected
    return "local"


# --- Sandbox provider helpers (for management endpoints) ---


def _init_providers_and_managers() -> tuple[dict, dict]:
    """Load sandbox providers and managers from config files."""
    from sandbox.local import LocalSessionProvider

    providers: dict[str, Any] = {
        "local": LocalSessionProvider(default_cwd=str(LOCAL_WORKSPACE_ROOT)),
    }
    if not SANDBOXES_DIR.exists():
        managers = {name: SandboxManager(provider=p, db_path=SANDBOX_DB_PATH) for name, p in providers.items()}
        return providers, managers

    for config_file in SANDBOXES_DIR.glob("*.json"):
        name = config_file.stem
        try:
            config = SandboxConfig.load(name)
            if config.provider == "agentbay":
                from sandbox.providers.agentbay import AgentBayProvider

                key = config.agentbay.api_key or os.getenv("AGENTBAY_API_KEY")
                if key:
                    providers["agentbay"] = AgentBayProvider(
                        api_key=key,
                        region_id=config.agentbay.region_id,
                        default_context_path=config.agentbay.context_path,
                        image_id=config.agentbay.image_id,
                    )
            elif config.provider == "docker":
                from sandbox.providers.docker import DockerProvider

                providers["docker"] = DockerProvider(
                    image=config.docker.image,
                    mount_path=config.docker.mount_path,
                )
            elif config.provider == "e2b":
                from sandbox.providers.e2b import E2BProvider

                key = config.e2b.api_key or os.getenv("E2B_API_KEY")
                if key:
                    providers["e2b"] = E2BProvider(
                        api_key=key,
                        template=config.e2b.template,
                        default_cwd=config.e2b.cwd,
                        timeout=config.e2b.timeout,
                    )
            elif config.provider == "daytona":
                from sandbox.providers.daytona import DaytonaProvider

                key = config.daytona.api_key or os.getenv("DAYTONA_API_KEY")
                if key:
                    providers["daytona"] = DaytonaProvider(
                        api_key=key,
                        api_url=config.daytona.api_url,
                        target=config.daytona.target,
                        default_cwd=config.daytona.cwd,
                    )
        except Exception as e:
            print(f"[sandbox] Failed to load {name}: {e}")

    managers = {name: SandboxManager(provider=p, db_path=SANDBOX_DB_PATH) for name, p in providers.items()}
    return providers, managers


def _load_all_sessions(managers: dict) -> list[dict]:
    """Load sessions from all managers in parallel."""
    sessions: list[dict] = []
    if not managers:
        return sessions
    for provider_name, manager in managers.items():
        rows = manager.list_sessions()
        for row in rows:
            sessions.append(
                {
                    "session_id": row["session_id"],
                    "thread_id": row["thread_id"],
                    "provider": row.get("provider", provider_name),
                    "status": row.get("status", "running"),
                    "created_at": row.get("created_at"),
                    "last_active": row.get("last_active"),
                    "lease_id": row.get("lease_id"),
                    "instance_id": row.get("instance_id"),
                    "chat_session_id": row.get("chat_session_id"),
                    "source": row.get("source", "unknown"),
                    "inspect_visible": row.get("inspect_visible", True),
                }
            )

    # @@@stable-session-order - Keep deterministic ordering across refreshes/providers.
    def _to_ts(value: Any) -> float:
        if not value or not isinstance(value, str):
            return 0.0
        try:
            return datetime.fromisoformat(value).timestamp()
        except Exception:
            return 0.0

    sessions.sort(
        key=lambda row: (
            -_to_ts(row.get("created_at")),
            -_to_ts(row.get("last_active")),
            str(row.get("provider") or ""),
            str(row.get("thread_id") or ""),
            str(row.get("session_id") or ""),
        )
    )
    return sessions


def _find_session_and_manager(
    sessions: list[dict],
    managers: dict,
    session_id: str,
    provider_name: str | None = None,
) -> tuple[dict | None, Any | None]:
    """Find session by ID/prefix (+optional provider), return (session, manager)."""
    candidates: list[dict] = []
    for s in sessions:
        if provider_name and s.get("provider") != provider_name:
            continue
        sid = str(s.get("session_id") or "")
        if sid == session_id or sid.startswith(session_id):
            candidates.append(s)
    if not candidates:
        return None, None
    if len(candidates) == 1:
        chosen = candidates[0]
        return chosen, managers.get(chosen["provider"])
    exact = [s for s in candidates if str(s.get("session_id") or "") == session_id]
    if len(exact) == 1:
        chosen = exact[0]
        return chosen, managers.get(chosen["provider"])
    raise RuntimeError(f"Ambiguous session_id '{session_id}'. Specify provider query param.")


def _is_virtual_thread_id(thread_id: str | None) -> bool:
    return bool(thread_id) and thread_id.startswith("(") and thread_id.endswith(")")


def _run_idle_reaper_once(app_obj: FastAPI) -> int:
    """External idle manager: enforce idle timeout across providers."""
    total = 0
    managed_providers: set[str] = set()

    # First use live managers from resident agents (can close live runtimes safely).
    for agent in app_obj.state.agent_pool.values():
        sandbox = getattr(agent, "_sandbox", None)
        manager = getattr(sandbox, "manager", None)
        if manager is None:
            continue
        provider_name = str(getattr(manager.provider, "name", ""))
        managed_providers.add(provider_name)
        total += manager.enforce_idle_timeouts()

    # Then cover providers without resident agent (DB-only cleanup).
    _, managers = _init_providers_and_managers()
    for provider_name, manager in managers.items():
        if provider_name in managed_providers:
            continue
        total += manager.enforce_idle_timeouts()

    return total


async def _idle_reaper_loop(app_obj: FastAPI) -> None:
    while True:
        try:
            count = await asyncio.to_thread(_run_idle_reaper_once, app_obj)
            if count > 0:
                print(f"[idle-reaper] paused+closed {count} expired chat session(s)")
        except Exception as e:
            print(f"[idle-reaper] error: {e}")
        await asyncio.sleep(IDLE_REAPER_INTERVAL_SEC)


# --- Lifespan + App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_manager = ConfigManager()
    config_manager.load_to_env()

    app.state.agent_pool: dict[str, Any] = {}
    app.state.thread_sandbox: dict[str, str] = {}
    app.state.thread_cwd: dict[str, str] = {}
    app.state.thread_locks: dict[str, asyncio.Lock] = {}
    app.state.thread_locks_guard = asyncio.Lock()
    app.state.idle_reaper_task: asyncio.Task | None = None

    try:
        app.state.idle_reaper_task = asyncio.create_task(_idle_reaper_loop(app))
        yield
    finally:
        task = app.state.idle_reaper_task
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for agent in app.state.agent_pool.values():
            try:
                agent.close()
            except Exception as e:
                print(f"[web] Agent cleanup error: {e}")


app = FastAPI(title="Leon Web Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _get_thread_lock(app_obj: FastAPI, thread_id: str) -> asyncio.Lock:
    async with app_obj.state.thread_locks_guard:
        lock = app_obj.state.thread_locks.get(thread_id)
        if lock is None:
            lock = asyncio.Lock()
            app_obj.state.thread_locks[thread_id] = lock
        return lock


# --- Helpers ---


def _extract_text_content(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts: list[str] = []
        for block in raw_content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(raw_content)


def _iter_update_messages(update_payload: Any) -> list[Any]:
    if not isinstance(update_payload, dict):
        return []
    messages: list[Any] = []
    for node_update in update_payload.values():
        if not isinstance(node_update, dict):
            continue
        node_messages = node_update.get("messages", [])
        if isinstance(node_messages, list):
            messages.extend(node_messages)
            continue
        messages.append(node_messages)
    return messages


def _serialize_message(msg: Any) -> dict[str, Any]:
    return {
        "type": msg.__class__.__name__,
        "content": getattr(msg, "content", ""),
        "tool_calls": getattr(msg, "tool_calls", []),
        "tool_call_id": getattr(msg, "tool_call_id", None),
    }


def _list_threads_from_db() -> list[dict[str, Any]]:
    """List threads with preview and updated_at extracted from checkpoint blobs."""
    thread_ids: set[str] = set()
    thread_meta: dict[str, dict[str, Any]] = {}  # thread_id -> {preview, updated_at}

    if DB_PATH.exists():
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "checkpoints" in existing:
                rows = conn.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id IS NOT NULL").fetchall()
                thread_ids.update(row["thread_id"] for row in rows if row["thread_id"])

                # Extract preview + updated_at from latest checkpoint per thread
                try:
                    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

                    serde = JsonPlusSerializer()
                    ckpt_rows = conn.execute("""
                        SELECT c.thread_id, c.type, c.checkpoint
                        FROM checkpoints c
                        INNER JOIN (
                            SELECT thread_id, MAX(checkpoint_id) as max_ckpt
                            FROM checkpoints WHERE checkpoint_ns = ''
                            GROUP BY thread_id
                        ) latest ON c.thread_id = latest.thread_id AND c.checkpoint_id = latest.max_ckpt
                        WHERE c.checkpoint_ns = ''
                    """).fetchall()
                    for tid, typ, blob in ckpt_rows:
                        try:
                            data = serde.loads_typed((typ, blob))
                            ts = data.get("ts", "")
                            msgs = data.get("channel_values", {}).get("messages", [])
                            preview = ""
                            for m in msgs:
                                if getattr(m, "type", "") == "human":
                                    preview = str(getattr(m, "content", ""))[:40]
                                    break
                            thread_meta[tid] = {"preview": preview, "updated_at": ts}
                        except Exception:
                            pass
                except ImportError:
                    pass

    if SANDBOX_DB_PATH.exists():
        with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "chat_sessions" in existing:
                rows = conn.execute(
                    "SELECT DISTINCT thread_id FROM chat_sessions WHERE thread_id IS NOT NULL"
                ).fetchall()
                thread_ids.update(row["thread_id"] for row in rows if row["thread_id"])

    results = []
    for tid in sorted(thread_ids):
        # Filter out sub-agent threads (they start with "subagent_")
        if tid.startswith("subagent_"):
            continue
        meta = thread_meta.get(tid, {})
        results.append(
            {
                "thread_id": tid,
                "preview": meta.get("preview", ""),
                "updated_at": meta.get("updated_at", ""),
            }
        )
    # Sort by updated_at descending (newest first)
    results.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return results


def _delete_thread_in_db(thread_id: str) -> None:
    ident_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def _sqlite_ident(name: str) -> str:
        if not ident_re.match(name):
            raise RuntimeError(f"Invalid sqlite identifier: {name}")
        return f'"{name}"'

    for db_path in (DB_PATH, SANDBOX_DB_PATH):
        if not db_path.exists():
            continue
        with sqlite3.connect(str(db_path)) as conn:
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            for table in existing:
                try:
                    table_ident = _sqlite_ident(table)
                except RuntimeError:
                    continue
                cols = {r[1] for r in conn.execute("PRAGMA table_info(" + table_ident + ")").fetchall()}
                if "thread_id" in cols:
                    conn.execute("DELETE FROM " + table_ident + " WHERE thread_id = ?", (thread_id,))
            conn.commit()


def _destroy_thread_resources_sync(thread_id: str, sandbox_type: str) -> bool:
    pool_key = f"{thread_id}:{sandbox_type}"
    pooled_agent = app.state.agent_pool.get(pool_key)
    if pooled_agent and hasattr(pooled_agent, "_sandbox"):
        manager = pooled_agent._sandbox.manager
    else:
        _, managers = _init_providers_and_managers()
        manager = managers.get(sandbox_type)
    if not manager:
        raise RuntimeError(f"No sandbox manager found for provider {sandbox_type}")
    return manager.destroy_thread_resources(thread_id)


def _get_terminal_timestamps(terminal_id: str) -> tuple[str | None, str | None]:
    if not SANDBOX_DB_PATH.exists():
        return None, None
    with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT created_at, updated_at FROM abstract_terminals WHERE terminal_id = ?",
            (terminal_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["created_at"], row["updated_at"]


def _get_lease_timestamps(lease_id: str) -> tuple[str | None, str | None]:
    if not SANDBOX_DB_PATH.exists():
        return None, None
    with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT created_at, updated_at FROM sandbox_leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["created_at"], row["updated_at"]


async def _get_thread_agent(thread_id: str, *, require_remote: bool = False) -> Any:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    if require_remote and sandbox_type == "local":
        raise HTTPException(400, "Local threads have no remote sandbox")
    try:
        set_current_thread_id(thread_id)
        agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    except Exception as e:
        raise HTTPException(503, f"Sandbox agent init failed for {sandbox_type}: {e}") from e
    if not hasattr(agent, "_sandbox"):
        raise HTTPException(400, "Agent has no sandbox")
    if require_remote and agent._sandbox.name == "local":
        raise HTTPException(400, "Agent has no remote sandbox")
    return agent


def _resolve_local_workspace_path(raw_path: str | None, thread_id: str | None = None) -> Path:
    # Use thread-specific workspace root if available
    if thread_id:
        thread_cwd = app.state.thread_cwd.get(thread_id)
        if thread_cwd:
            base = Path(thread_cwd).resolve()
        else:
            base = LOCAL_WORKSPACE_ROOT
    else:
        base = LOCAL_WORKSPACE_ROOT

    if not raw_path:
        return base
    requested = Path(raw_path).expanduser()
    if requested.is_absolute():
        target = requested.resolve()
    else:
        target = (base / requested).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, f"Path outside workspace: {target}") from exc
    return target


# --- Sandbox endpoints ---


@app.get("/api/sandbox/types")
async def list_sandbox_types() -> dict[str, Any]:
    types = await asyncio.to_thread(_available_sandbox_types)
    return {"types": types}


@app.get("/api/sandbox/pick-folder")
async def pick_folder() -> dict[str, Any]:
    """Open system folder picker dialog and return selected path."""
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'POSIX path of (choose folder with prompt "选择工作目录")',
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                return {"path": path}
            else:
                raise HTTPException(400, "User cancelled folder selection")
        elif sys.platform == "win32":  # Windows
            # Use PowerShell folder browser
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = "选择工作目录"
            $dialog.ShowNewFolderButton = $true
            if ($dialog.ShowDialog() -eq 'OK') {
                Write-Output $dialog.SelectedPath
            }
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                return {"path": path}
            else:
                raise HTTPException(400, "User cancelled folder selection")
        else:  # Linux
            # Try zenity first, fallback to kdialog
            try:
                result = subprocess.run(
                    ["zenity", "--file-selection", "--directory", "--title=选择工作目录"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    return {"path": path}
            except FileNotFoundError:
                # Try kdialog
                result = subprocess.run(
                    ["kdialog", "--getexistingdirectory", ".", "--title", "选择工作目录"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    return {"path": path}
            raise HTTPException(400, "User cancelled folder selection")
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Folder selection timed out")
    except Exception as e:
        raise HTTPException(500, f"Failed to open folder picker: {str(e)}")


@app.get("/api/sandbox/sessions")
async def list_sandbox_sessions() -> dict[str, Any]:
    # Read-only: standalone managers are fine for listing
    _, managers = await asyncio.to_thread(_init_providers_and_managers)
    sessions = await asyncio.to_thread(_load_all_sessions, managers)
    return {"sessions": sessions}


@app.get("/api/sandbox/sessions/{session_id}/metrics")
async def get_session_metrics(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    providers, managers = await asyncio.to_thread(_init_providers_and_managers)
    sessions = await asyncio.to_thread(_load_all_sessions, managers)
    try:
        session, _ = _find_session_and_manager(sessions, managers, session_id, provider_name=provider)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    if not session:
        raise HTTPException(404, f"Session not found: {session_id}")
    provider = providers.get(session["provider"])
    if not provider:
        return {"session_id": session["session_id"], "metrics": None}
    metrics = await asyncio.to_thread(provider.get_metrics, session["session_id"])
    web_url = None
    if hasattr(provider, "get_web_url"):
        web_url = await asyncio.to_thread(provider.get_web_url, session["session_id"])
    result: dict[str, Any] = {"session_id": session["session_id"], "metrics": None, "web_url": web_url}
    if metrics:
        result["metrics"] = {
            "cpu_percent": metrics.cpu_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "memory_total_mb": metrics.memory_total_mb,
            "disk_used_gb": metrics.disk_used_gb,
            "disk_total_gb": metrics.disk_total_gb,
            "network_rx_kbps": metrics.network_rx_kbps,
            "network_tx_kbps": metrics.network_tx_kbps,
        }
    return result


def _mutate_sandbox_session(
    *,
    session_id: str,
    action: str,
    provider_hint: str | None = None,
) -> dict[str, Any]:
    _, managers = _init_providers_and_managers()
    sessions = _load_all_sessions(managers)
    session, manager = _find_session_and_manager(sessions, managers, session_id, provider_name=provider_hint)
    if not session:
        raise RuntimeError(f"Session not found: {session_id}")

    provider_name = str(session.get("provider") or "")
    if not manager:
        raise RuntimeError(f"Provider manager unavailable: {provider_name}")

    thread_id = str(session.get("thread_id") or "")
    lease_id = session.get("lease_id")
    target_session_id = str(session.get("session_id") or session_id)

    ok = False
    mode = "lease_enforced"

    if manager and thread_id and not _is_virtual_thread_id(thread_id):
        mode = "manager_thread"
        if action == "pause":
            ok = manager.pause_session(thread_id)
        elif action == "resume":
            ok = manager.resume_session(thread_id)
        elif action == "destroy":
            ok = manager.destroy_thread_resources(thread_id)
        else:
            raise RuntimeError(f"Unknown action: {action}")
    else:
        lease = manager.lease_store.get(lease_id) if lease_id else None
        if not lease:
            adopt_lease_id = str(lease_id or f"lease-adopt-{uuid.uuid4().hex[:12]}")
            adopt_status = str(session.get("status") or "unknown")
            lease = manager.lease_store.adopt_instance(
                lease_id=adopt_lease_id,
                provider_name=provider_name,
                instance_id=target_session_id,
                status=adopt_status,
            )
            lease_id = lease.lease_id

        mode = "manager_lease"
        if action == "pause":
            ok = lease.pause_instance(manager.provider)
        elif action == "resume":
            ok = lease.resume_instance(manager.provider)
        elif action == "destroy":
            lease.destroy_instance(manager.provider)
            ok = True
        else:
            raise RuntimeError(f"Unknown action: {action}")

    if not ok:
        raise RuntimeError(f"Failed to {action} session {target_session_id}")

    return {
        "ok": True,
        "action": action,
        "session_id": target_session_id,
        "provider": provider_name,
        "thread_id": thread_id or None,
        "lease_id": lease_id,
        "mode": mode,
    }


def _extract_webhook_instance_id(payload: dict[str, Any]) -> str | None:
    """Extract provider instance/session id from webhook payload."""
    direct_keys = ("session_id", "sandbox_id", "instance_id", "id")
    for key in direct_keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in direct_keys:
            value = nested.get(key)
            if isinstance(value, str) and value:
                return value

    return None


@app.post("/api/sandbox/sessions/{session_id}/pause")
async def pause_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            _mutate_sandbox_session,
            session_id=session_id,
            action="pause",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e


@app.post("/api/sandbox/sessions/{session_id}/resume")
async def resume_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            _mutate_sandbox_session,
            session_id=session_id,
            action="resume",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e


@app.delete("/api/sandbox/sessions/{session_id}")
async def destroy_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            _mutate_sandbox_session,
            session_id=session_id,
            action="destroy",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e


@app.post("/api/webhooks/{provider_name}")
async def ingest_provider_webhook(provider_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Ingest provider webhook: persist provider event and converge lease observed state."""
    instance_id = _extract_webhook_instance_id(payload)
    if not instance_id:
        raise HTTPException(400, "Webhook payload missing instance/session id")

    event_type = str(payload.get("event") or payload.get("type") or "unknown")
    store = LeaseStore(db_path=SANDBOX_DB_PATH)
    event_store = ProviderEventStore(db_path=SANDBOX_DB_PATH)
    lease = await asyncio.to_thread(store.find_by_instance, provider_name=provider_name, instance_id=instance_id)
    matched_lease_id = lease.lease_id if lease else None

    # @@@webhook-invalidation-only - Webhook is optimization only: persist event + mark lease stale.
    await asyncio.to_thread(
        event_store.record,
        provider_name=provider_name,
        instance_id=instance_id,
        event_type=event_type,
        payload=payload,
        matched_lease_id=matched_lease_id,
    )

    if not lease:
        return {
            "ok": True,
            "provider": provider_name,
            "instance_id": instance_id,
            "event_type": event_type,
            "matched": False,
        }
    status_hint = str(payload.get("status") or payload.get("state") or payload.get("event") or "unknown").lower()
    if "pause" in status_hint:
        status_hint = "paused"
    elif "resume" in status_hint or "start" in status_hint or "running" in status_hint:
        status_hint = "running"
    elif "destroy" in status_hint or "delete" in status_hint or "stop" in status_hint:
        status_hint = "detached"
    else:
        status_hint = "unknown"

    _, managers = await asyncio.to_thread(_init_providers_and_managers)
    manager = managers.get(provider_name)
    if not manager:
        raise HTTPException(503, f"Provider manager unavailable: {provider_name}")
    # @@@webhook-invalidation-only - Webhooks are freshness invalidation, not authoritative state transitions.
    await asyncio.to_thread(lease.mark_needs_refresh)
    return {
        "ok": True,
        "provider": provider_name,
        "instance_id": instance_id,
        "event_type": event_type,
        "matched": True,
        "lease_id": lease.lease_id,
        "status_hint": status_hint,
        "needs_refresh": True,
    }


@app.get("/api/webhooks/events")
async def list_provider_events(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    store = ProviderEventStore(db_path=SANDBOX_DB_PATH)
    items = await asyncio.to_thread(store.list_recent, limit)
    return {"items": items, "count": len(items)}


# @@@ Thread-level sandbox control — routes through the agent's own sandbox so cache stays consistent
@app.post("/api/threads/{thread_id}/sandbox/pause")
async def pause_thread_sandbox(thread_id: str) -> dict[str, Any]:
    try:
        agent = await _get_thread_agent(thread_id)
        ok = await asyncio.to_thread(agent._sandbox.pause_thread, thread_id)
        if not ok:
            raise HTTPException(409, f"Failed to pause sandbox for thread {thread_id}")
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


@app.post("/api/threads/{thread_id}/sandbox/resume")
async def resume_thread_sandbox(thread_id: str) -> dict[str, Any]:
    try:
        agent = await _get_thread_agent(thread_id)
        ok = await asyncio.to_thread(agent._sandbox.resume_thread, thread_id)
        if not ok:
            raise HTTPException(409, f"Failed to resume sandbox for thread {thread_id}")
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


@app.delete("/api/threads/{thread_id}/sandbox")
async def destroy_thread_sandbox(thread_id: str) -> dict[str, Any]:
    try:
        agent = await _get_thread_agent(thread_id)
        ok = await asyncio.to_thread(agent._sandbox.manager.destroy_session, thread_id)
        if not ok:
            raise HTTPException(404, f"No sandbox session found for thread {thread_id}")
        agent._sandbox._capability_cache.pop(thread_id, None)
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


# --- New architecture endpoints: session/terminal/lease status ---


@app.get("/api/threads/{thread_id}/session")
async def get_thread_session_status(thread_id: str) -> dict[str, Any]:
    """Get ChatSession status for a thread."""
    agent = await _get_thread_agent(thread_id)

    def _get_session_and_terminal():
        mgr = agent._sandbox.manager
        terminal = mgr.terminal_store.get_active(thread_id)
        if not terminal:
            return None, None
        session = mgr.session_manager.get(thread_id, terminal.terminal_id)
        return session, terminal

    session, terminal = await asyncio.to_thread(_get_session_and_terminal)
    if not terminal:
        raise HTTPException(404, f"No session found for thread {thread_id}")
    if not session:
        return {
            "thread_id": thread_id,
            "session_id": None,
            "terminal_id": terminal.terminal_id,
            "status": "inactive",
            "started_at": None,
            "last_active_at": None,
            "expires_at": None,
        }
    expires_by_idle = session.last_active_at + timedelta(seconds=session.policy.idle_ttl_sec)
    expires_by_duration = session.started_at + timedelta(seconds=session.policy.max_duration_sec)
    expires_at = min(expires_by_idle, expires_by_duration)

    return {
        "thread_id": thread_id,
        "session_id": session.session_id,
        "terminal_id": session.terminal.terminal_id,
        "status": session.status,
        "started_at": session.started_at.isoformat(),
        "last_active_at": session.last_active_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }


@app.get("/api/threads/{thread_id}/terminal")
async def get_thread_terminal_status(thread_id: str) -> dict[str, Any]:
    """Get AbstractTerminal state for a thread."""
    agent = await _get_thread_agent(thread_id)

    def _get_terminal():
        mgr = agent._sandbox.manager
        return mgr.terminal_store.get_active(thread_id)

    terminal = await asyncio.to_thread(_get_terminal)
    if not terminal:
        raise HTTPException(404, f"No terminal found for thread {thread_id}")

    state = terminal.get_state()
    created_at, updated_at = await asyncio.to_thread(_get_terminal_timestamps, terminal.terminal_id)
    return {
        "thread_id": thread_id,
        "terminal_id": terminal.terminal_id,
        "lease_id": terminal.lease_id,
        "cwd": state.cwd,
        "env_delta": state.env_delta,
        "version": state.state_version,
        "created_at": created_at,
        "updated_at": updated_at,
    }


@app.get("/api/threads/{thread_id}/lease")
async def get_thread_lease_status(thread_id: str) -> dict[str, Any]:
    """Get SandboxLease status for a thread."""
    agent = await _get_thread_agent(thread_id)

    def _get_lease():
        mgr = agent._sandbox.manager
        terminal = mgr.terminal_store.get_active(thread_id)
        if not terminal:
            return None
        lease = mgr.lease_store.get(terminal.lease_id)
        if not lease:
            return None
        return lease

    lease = await asyncio.to_thread(_get_lease)
    if not lease:
        raise HTTPException(404, f"No lease found for thread {thread_id}")

    instance = lease.get_instance()
    created_at, updated_at = await asyncio.to_thread(_get_lease_timestamps, lease.lease_id)
    return {
        "thread_id": thread_id,
        "lease_id": lease.lease_id,
        "provider_name": lease.provider_name,
        "desired_state": lease.desired_state,
        "observed_state": lease.observed_state,
        "version": lease.version,
        "last_error": lease.last_error,
        "instance": {
            "instance_id": instance.instance_id if instance else None,
            "state": instance.status if instance else None,
            "started_at": instance.created_at.isoformat() if instance and instance.created_at else None,
        }
        if instance
        else None,
        "created_at": created_at,
        "updated_at": updated_at,
    }


@app.get("/api/threads/{thread_id}/workspace/list")
async def list_workspace_path(thread_id: str, path: str | None = Query(default=None)) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    if sandbox_type == "local":
        from middleware.filesystem.local_backend import LocalBackend

        backend = LocalBackend()
        target = _resolve_local_workspace_path(path, thread_id=thread_id)
        result = backend.list_dir(str(target))
        if result.error:
            raise HTTPException(400, result.error)
        return {
            "thread_id": thread_id,
            "path": str(target),
            "entries": [
                {"name": e.name, "is_dir": e.is_dir, "size": e.size, "children_count": e.children_count}
                for e in result.entries
            ],
        }

    agent = await _get_thread_agent(thread_id, require_remote=True)

    def _list_remote() -> dict[str, Any]:
        set_current_thread_id(thread_id)
        capability = agent._sandbox.manager.get_sandbox(thread_id)
        target = path or capability._session.terminal.get_state().cwd
        result = capability.fs.list_dir(target)
        if result.error:
            raise RuntimeError(result.error)
        return {
            "path": target,
            "entries": [
                {"name": e.name, "is_dir": e.is_dir, "size": e.size, "children_count": e.children_count}
                for e in result.entries
            ],
        }

    try:
        payload = await asyncio.to_thread(_list_remote)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    return {"thread_id": thread_id, **payload}


@app.get("/api/threads/{thread_id}/workspace/read")
async def read_workspace_file(thread_id: str, path: str = Query(...)) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    if sandbox_type == "local":
        from middleware.filesystem.local_backend import LocalBackend

        backend = LocalBackend()
        target = _resolve_local_workspace_path(path, thread_id=thread_id)
        try:
            data = backend.read_file(str(target))
        except Exception as e:
            raise HTTPException(400, str(e)) from e
        return {"thread_id": thread_id, "path": str(target), "content": data.content, "size": data.size}

    agent = await _get_thread_agent(thread_id, require_remote=True)

    def _read_remote() -> dict[str, Any]:
        set_current_thread_id(thread_id)
        capability = agent._sandbox.manager.get_sandbox(thread_id)
        data = capability.fs.read_file(path)
        return {"path": path, "content": data.content, "size": data.size}

    try:
        payload = await asyncio.to_thread(_read_remote)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return {"thread_id": thread_id, **payload}


# --- Thread endpoints ---


@app.post("/api/threads")
async def create_thread(payload: CreateThreadRequest | None = None) -> dict[str, Any]:
    sandbox_type = payload.sandbox if payload else "local"
    thread_id = str(uuid.uuid4())
    app.state.thread_sandbox[thread_id] = sandbox_type
    if payload and payload.cwd:
        app.state.thread_cwd[thread_id] = payload.cwd
    return {"thread_id": thread_id, "sandbox": sandbox_type}


@app.get("/api/threads")
async def list_threads() -> dict[str, Any]:
    threads = await asyncio.to_thread(_list_threads_from_db)
    # Enrich with sandbox info
    for t in threads:
        t["sandbox"] = _resolve_thread_sandbox(app, t["thread_id"])
    return {"threads": threads}


@app.get("/api/threads/{thread_id}")
async def get_thread_messages(thread_id: str) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    set_current_thread_id(thread_id)  # Set thread_id before accessing agent state
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.agent.aget_state(config)

    values = getattr(state, "values", {}) if state else {}
    messages = values.get("messages", []) if isinstance(values, dict) else []

    # Get sandbox session info (new architecture)
    sandbox_info: dict[str, Any] = {"type": sandbox_type, "status": None, "session_id": None}
    if hasattr(agent, "_sandbox"):
        try:
            mgr = agent._sandbox.manager
            terminal = mgr.terminal_store.get_active(thread_id)
            session = mgr.session_manager.get(thread_id, terminal.terminal_id) if terminal else None
            if session:
                sandbox_info["session_id"] = session.session_id
            if terminal:
                lease = mgr.lease_store.get(terminal.lease_id)
                if lease:
                    instance = lease.get_instance()
                    if instance:
                        sandbox_info["status"] = lease.observed_state or instance.status
                    else:
                        sandbox_info["status"] = "detached"
                sandbox_info["terminal_id"] = terminal.terminal_id
        except Exception as exc:
            sandbox_info["status"] = "error"
            sandbox_info["error"] = str(exc)

    return {
        "thread_id": thread_id,
        "messages": [_serialize_message(msg) for msg in messages],
        "sandbox": sandbox_info,
    }


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    pool_key = f"{thread_id}:{sandbox_type}"

    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        agent = app.state.agent_pool.get(pool_key)
        if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
            raise HTTPException(status_code=409, detail="Cannot delete thread while run is in progress")
        try:
            await asyncio.to_thread(_destroy_thread_resources_sync, thread_id, sandbox_type)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"Failed to destroy sandbox resources: {exc}") from exc
        await asyncio.to_thread(_delete_thread_in_db, thread_id)

    # Clean up thread-specific state
    app.state.thread_sandbox.pop(thread_id, None)
    app.state.thread_cwd.pop(thread_id, None)

    # Remove per-thread Agent from pool
    app.state.agent_pool.pop(pool_key, None)

    return {"ok": True, "thread_id": thread_id}


@app.post("/api/threads/{thread_id}/steer")
async def steer_thread(thread_id: str, payload: SteerRequest) -> dict[str, Any]:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    queue_manager = get_queue_manager()
    # Use the current default mode set by the user
    queue_manager.enqueue(payload.message)
    return {"ok": True, "thread_id": thread_id, "mode": queue_manager.get_mode().value}


class QueueModeRequest(BaseModel):
    mode: str


@app.post("/api/threads/{thread_id}/queue-mode")
async def set_thread_queue_mode(thread_id: str, payload: QueueModeRequest) -> dict[str, Any]:
    try:
        mode = QueueMode(payload.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid queue mode: {payload.mode}")
    queue_manager = get_queue_manager()
    queue_manager.set_mode(mode)
    return {"ok": True, "thread_id": thread_id, "mode": mode.value}


@app.get("/api/threads/{thread_id}/queue-mode")
async def get_thread_queue_mode(thread_id: str) -> dict[str, Any]:
    queue_manager = get_queue_manager()
    return {"mode": queue_manager.get_mode().value}


# --- Runtime status endpoint ---


@app.get("/api/threads/{thread_id}/runtime")
async def get_thread_runtime(thread_id: str) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    if not hasattr(agent, "runtime"):
        raise HTTPException(status_code=404, detail="Agent has no runtime monitor")
    return agent.runtime.get_status_dict()


# --- Run endpoint (SSE streaming) ---


@app.post("/api/threads/{thread_id}/runs")
async def run_thread(thread_id: str, payload: RunRequest) -> EventSourceResponse:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    set_current_thread_id(thread_id)
    agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        if hasattr(agent, "runtime") and not agent.runtime.transition(AgentState.ACTIVE):
            # Transition can fail for reasons other than "already running" (e.g. error/terminated states).
            state = getattr(getattr(agent, "runtime", None), "current_state", None)
            if state == AgentState.ACTIVE:
                raise HTTPException(status_code=409, detail="Thread is already running")
            raise HTTPException(status_code=409, detail=f"Thread cannot start run from state={getattr(state, 'value', state)}")

    async def event_stream() -> AsyncGenerator[dict[str, str], None]:
        try:
            config = {"configurable": {"thread_id": thread_id}}
            set_current_thread_id(thread_id)

            # @@@ Streaming parser mirrors TUI runner chunk semantics so web and CLI stay consistent.
            # Prime session before tool calls so lazy capability wrappers never race thread context propagation.
            if hasattr(agent, "_sandbox"):

                def _prime_sandbox() -> None:
                    mgr = agent._sandbox.manager
                    mgr.enforce_idle_timeouts()
                    terminal = mgr.terminal_store.get_active(thread_id)
                    existing = mgr.session_manager.get(thread_id, terminal.terminal_id) if terminal else None
                    if existing and existing.status == "paused":
                        if not agent._sandbox.resume_thread(thread_id):
                            raise RuntimeError(f"Failed to resume paused session for thread {thread_id}")
                    agent._sandbox.ensure_session(thread_id)
                    terminal = mgr.terminal_store.get_active(thread_id)
                    lease = mgr.lease_store.get(terminal.lease_id) if terminal else None
                    if lease:
                        lease_status = lease.refresh_instance_status(mgr.provider)
                        if lease_status == "paused" and mgr.provider_capability.can_resume:
                            if not agent._sandbox.resume_thread(thread_id):
                                raise RuntimeError(f"Failed to auto-resume paused sandbox for thread {thread_id}")

                await asyncio.to_thread(_prime_sandbox)

            emitted_tool_call_ids: set[str] = set()

            async for chunk in agent.agent.astream(
                {"messages": [{"role": "user", "content": payload.message}]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                if not chunk:
                    continue

                # stream_mode=["messages", "updates"] yields tuples: (mode, data)
                if not isinstance(chunk, tuple) or len(chunk) != 2:
                    continue
                mode, data = chunk

                # --- Token-level streaming from "messages" mode ---
                if mode == "messages":
                    msg_chunk, metadata = data
                    msg_class = msg_chunk.__class__.__name__
                    # Only stream AIMessageChunk tokens (not ToolMessage, HumanMessage, etc.)
                    if msg_class == "AIMessageChunk":
                        content = _extract_text_content(getattr(msg_chunk, "content", ""))
                        if content:
                            yield {
                                "event": "text",
                                "data": json.dumps({"content": content}, ensure_ascii=False),
                            }

                # --- Node-level updates from "updates" mode ---
                elif mode == "updates":
                    for msg in _iter_update_messages(data):
                        msg_class = msg.__class__.__name__
                        if msg_class == "AIMessage":
                            for tc in getattr(msg, "tool_calls", []):
                                tc_id = tc.get("id")
                                if tc_id and tc_id in emitted_tool_call_ids:
                                    continue
                                if tc_id:
                                    emitted_tool_call_ids.add(tc_id)
                                yield {
                                    "event": "tool_call",
                                    "data": json.dumps(
                                        {
                                            "id": tc.get("id"),
                                            "name": tc.get("name", "unknown"),
                                            "args": tc.get("args", {}),
                                        },
                                        ensure_ascii=False,
                                    ),
                                }
                            continue
                        if msg_class != "ToolMessage":
                            continue
                        yield {
                            "event": "tool_result",
                            "data": json.dumps(
                                {
                                    "tool_call_id": getattr(msg, "tool_call_id", None),
                                    "name": getattr(msg, "name", "unknown"),
                                    "content": str(getattr(msg, "content", "")),
                                },
                                ensure_ascii=False,
                            ),
                        }
                        if hasattr(agent, "runtime"):
                            status = agent.runtime.get_status_dict()
                            status["current_tool"] = getattr(msg, "name", None)
                            yield {
                                "event": "status",
                                "data": json.dumps(status, ensure_ascii=False),
                            }

            # --- Forward sub-agent events ---
            if hasattr(agent, "runtime"):
                for tool_call_id, events in agent.runtime.get_pending_subagent_events():
                    for event in events:
                        # Parse event data and add parent_tool_call_id
                        event_type = event.get("event", "")
                        event_data = json.loads(event.get("data", "{}"))
                        event_data["parent_tool_call_id"] = tool_call_id

                        # Emit with subagent_ prefix
                        yield {
                            "event": f"subagent_{event_type}",
                            "data": json.dumps(event_data, ensure_ascii=False),
                        }

            # Final status before done
            if hasattr(agent, "runtime"):
                yield {
                    "event": "status",
                    "data": json.dumps(agent.runtime.get_status_dict(), ensure_ascii=False),
                }
            yield {"event": "done", "data": json.dumps({"thread_id": thread_id})}
        except Exception as e:
            import traceback

            traceback.print_exc()
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
        finally:
            if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
                agent.runtime.transition(AgentState.IDLE)

    return EventSourceResponse(event_stream())


class TaskAgentRequest(BaseModel):
    subagent_type: str
    prompt: str
    description: str | None = None
    model: str | None = None
    max_turns: int | None = None


@app.post("/api/threads/{thread_id}/task-agent/stream")
async def stream_task_agent(thread_id: str, payload: TaskAgentRequest) -> EventSourceResponse:
    """Stream Task agent execution with real-time progress updates."""
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    sandbox_type = _resolve_thread_sandbox(app, thread_id)

    async def event_stream() -> AsyncGenerator[dict[str, str], None]:
        agent = None
        try:
            set_current_thread_id(thread_id)
            agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)

            # Get TaskMiddleware from agent
            task_middleware = None
            if hasattr(agent, "middleware"):
                for mw in agent.middleware:
                    if mw.__class__.__name__ == "TaskMiddleware":
                        task_middleware = mw
                        break

            if not task_middleware:
                yield {
                    "event": "task_error",
                    "data": json.dumps({"error": "TaskMiddleware not available"}, ensure_ascii=False),
                }
                return

            # Build task params
            from middleware.task.types import TaskParams

            params: TaskParams = {
                "SubagentType": payload.subagent_type,
                "Prompt": payload.prompt,
            }
            if payload.description:
                params["Description"] = payload.description
            if payload.model:
                params["Model"] = payload.model
            if payload.max_turns:
                params["MaxTurns"] = payload.max_turns

            # Stream task execution
            async for event in task_middleware.run_task_streaming(params):
                yield event

        except Exception as e:
            import traceback

            traceback.print_exc()
            yield {
                "event": "task_error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_stream())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
