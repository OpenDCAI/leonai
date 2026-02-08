from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import create_leon_agent
from middleware.monitor import AgentState
from middleware.queue import QueueMode, get_queue_manager
from sandbox.config import SandboxConfig
from sandbox.manager import SandboxManager, lookup_sandbox_for_thread
from sandbox.sqlite_store import DEFAULT_DB_PATH as SANDBOX_DB_PATH
from sandbox.thread_context import set_current_thread_id
from tui.config import ConfigManager

DB_PATH = Path.home() / ".leon" / "leon.db"
SANDBOXES_DIR = Path.home() / ".leon" / "sandboxes"


# --- Request models ---

class CreateThreadRequest(BaseModel):
    sandbox: str = "local"


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
    for f in sorted(SANDBOXES_DIR.glob("*.json")):
        name = f.stem
        try:
            SandboxConfig.load(name)
            types.append({"name": name, "available": True})
        except Exception as e:
            types.append({"name": name, "available": False, "reason": str(e)})
    return types


def _create_agent_sync(sandbox_name: str) -> Any:
    """Create a LeonAgent with the given sandbox. Runs in a thread."""
    # @@@ model_name=None lets the profile.yaml value take effect instead of the factory default
    return create_leon_agent(
        model_name=None,
        workspace_root=Path.cwd(),
        sandbox=sandbox_name if sandbox_name != "local" else None,
        verbose=True,
    )


async def _get_or_create_agent(app_obj: FastAPI, sandbox_type: str, thread_id: str | None = None) -> Any:
    """Lazy agent pool — one agent per sandbox type, created on demand."""
    if thread_id:
        set_current_thread_id(thread_id)
    pool = app_obj.state.agent_pool
    if sandbox_type in pool:
        return pool[sandbox_type]
    # @@@ agent-init-thread - LeonAgent.__init__ uses run_until_complete, must run in thread
    agent = await asyncio.to_thread(_create_agent_sync, sandbox_type)
    pool[sandbox_type] = agent
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
    providers: dict[str, Any] = {}
    if not SANDBOXES_DIR.exists():
        return {}, {}

    for config_file in SANDBOXES_DIR.glob("*.json"):
        name = config_file.stem
        try:
            config = SandboxConfig.load(name)
            if config.provider == "agentbay":
                from sandbox.providers.agentbay import AgentBayProvider
                key = config.agentbay.api_key or os.getenv("AGENTBAY_API_KEY")
                if key:
                    providers["agentbay"] = AgentBayProvider(
                        api_key=key, region_id=config.agentbay.region_id,
                        default_context_path=config.agentbay.context_path,
                        image_id=config.agentbay.image_id,
                    )
            elif config.provider == "docker":
                from sandbox.providers.docker import DockerProvider
                providers["docker"] = DockerProvider(
                    image=config.docker.image, mount_path=config.docker.mount_path,
                )
            elif config.provider == "e2b":
                from sandbox.providers.e2b import E2BProvider
                key = config.e2b.api_key or os.getenv("E2B_API_KEY")
                if key:
                    providers["e2b"] = E2BProvider(
                        api_key=key, template=config.e2b.template,
                        default_cwd=config.e2b.cwd, timeout=config.e2b.timeout,
                    )
            elif config.provider == "daytona":
                from sandbox.providers.daytona import DaytonaProvider
                key = config.daytona.api_key or os.getenv("DAYTONA_API_KEY")
                if key:
                    providers["daytona"] = DaytonaProvider(
                        api_key=key, api_url=config.daytona.api_url,
                        target=config.daytona.target, default_cwd=config.daytona.cwd,
                    )
        except Exception as e:
            print(f"[sandbox] Failed to load {name}: {e}")

    managers = {name: SandboxManager(provider=p) for name, p in providers.items()}
    return providers, managers


def _load_all_sessions(managers: dict) -> list[dict]:
    """Load sessions from all managers in parallel."""
    sessions: list[dict] = []
    if not managers:
        return sessions
    from concurrent.futures import as_completed

    with ThreadPoolExecutor(max_workers=len(managers)) as pool:
        futures = {
            pool.submit(manager.list_sessions): (provider_name, manager)
            for provider_name, manager in managers.items()
        }
        for future in as_completed(futures):
            provider_name, _manager = futures[future]
            rows = future.result()
            for row in rows:
                sessions.append({
                    "session_id": row["session_id"],
                    "thread_id": row["thread_id"],
                    "provider": row.get("provider", provider_name),
                    "status": row.get("status", "running"),
                    "created_at": row.get("created_at"),
                    "last_active": row.get("last_active"),
                })
    return sessions


def _find_session_and_manager(
    sessions: list[dict], managers: dict, session_id: str,
) -> tuple[dict | None, Any | None]:
    """Find session by ID or prefix, return (session, manager)."""
    for s in sessions:
        if s["session_id"] == session_id or s["session_id"].startswith(session_id):
            return s, managers.get(s["provider"])
    return None, None


# --- Lifespan + App ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    config_manager = ConfigManager()
    config_manager.load_to_env()

    app.state.agent_pool: dict[str, Any] = {}
    app.state.thread_sandbox: dict[str, str] = {}
    app.state.thread_locks: dict[str, asyncio.Lock] = {}
    app.state.thread_locks_guard = asyncio.Lock()

    try:
        yield
    finally:
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


def _serialize_message(msg: Any) -> dict[str, Any]:
    return {
        "type": msg.__class__.__name__,
        "content": getattr(msg, "content", ""),
        "tool_calls": getattr(msg, "tool_calls", []),
        "tool_call_id": getattr(msg, "tool_call_id", None),
    }


def _list_threads_from_db() -> list[dict[str, str]]:
    thread_ids: set[str] = set()

    if DB_PATH.exists():
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "checkpoints" in existing:
                rows = conn.execute(
                    "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id IS NOT NULL"
                ).fetchall()
                thread_ids.update(row["thread_id"] for row in rows if row["thread_id"])

    if SANDBOX_DB_PATH.exists():
        with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "chat_sessions" in existing:
                rows = conn.execute(
                    "SELECT DISTINCT thread_id FROM chat_sessions WHERE thread_id IS NOT NULL"
                ).fetchall()
                thread_ids.update(row["thread_id"] for row in rows if row["thread_id"])

    return [{"thread_id": thread_id} for thread_id in sorted(thread_ids)]


def _delete_thread_in_db(thread_id: str) -> None:
    for db_path in (DB_PATH, SANDBOX_DB_PATH):
        if not db_path.exists():
            continue
        with sqlite3.connect(str(db_path)) as conn:
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            for table in existing:
                cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                if "thread_id" in cols:
                    conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,))
            conn.commit()


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


async def _get_remote_agent(thread_id: str) -> Any:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    if sandbox_type == "local":
        raise HTTPException(400, "Local threads have no remote sandbox")
    set_current_thread_id(thread_id)
    try:
        agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    except Exception as e:
        raise HTTPException(503, f"Sandbox agent init failed for {sandbox_type}: {e}") from e
    if not hasattr(agent, "_sandbox") or agent._sandbox.name == "local":
        raise HTTPException(400, "Agent has no remote sandbox")
    return agent


# --- Sandbox endpoints ---

@app.get("/api/sandbox/types")
async def list_sandbox_types() -> dict[str, Any]:
    types = await asyncio.to_thread(_available_sandbox_types)
    return {"types": types}


@app.get("/api/sandbox/sessions")
async def list_sandbox_sessions() -> dict[str, Any]:
    # Read-only: standalone managers are fine for listing
    _, managers = await asyncio.to_thread(_init_providers_and_managers)
    sessions = await asyncio.to_thread(_load_all_sessions, managers)
    return {"sessions": sessions}


@app.get("/api/sandbox/sessions/{session_id}/metrics")
async def get_session_metrics(session_id: str) -> dict[str, Any]:
    providers, managers = await asyncio.to_thread(_init_providers_and_managers)
    sessions = await asyncio.to_thread(_load_all_sessions, managers)
    session, _ = _find_session_and_manager(sessions, managers, session_id)
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


# @@@ Thread-level sandbox control — routes through the agent's own sandbox so cache stays consistent
@app.post("/api/threads/{thread_id}/sandbox/pause")
async def pause_thread_sandbox(thread_id: str) -> dict[str, Any]:
    agent = await _get_remote_agent(thread_id)
    ok = await asyncio.to_thread(agent._sandbox.pause_thread, thread_id)
    if not ok:
        raise HTTPException(409, f"Failed to pause sandbox for thread {thread_id}")
    return {"ok": ok, "thread_id": thread_id}


@app.post("/api/threads/{thread_id}/sandbox/resume")
async def resume_thread_sandbox(thread_id: str) -> dict[str, Any]:
    agent = await _get_remote_agent(thread_id)
    ok = await asyncio.to_thread(agent._sandbox.resume_thread, thread_id)
    if not ok:
        raise HTTPException(409, f"Failed to resume sandbox for thread {thread_id}")
    return {"ok": ok, "thread_id": thread_id}


@app.delete("/api/threads/{thread_id}/sandbox")
async def destroy_thread_sandbox(thread_id: str) -> dict[str, Any]:
    agent = await _get_remote_agent(thread_id)
    ok = await asyncio.to_thread(agent._sandbox.manager.destroy_session, thread_id)
    if not ok:
        raise HTTPException(404, f"No sandbox session found for thread {thread_id}")
    agent._sandbox._capability_cache.pop(thread_id, None)
    return {"ok": ok, "thread_id": thread_id}


# --- New architecture endpoints: session/terminal/lease status ---

@app.get("/api/threads/{thread_id}/session")
async def get_thread_session_status(thread_id: str) -> dict[str, Any]:
    """Get ChatSession status for a thread."""
    agent = await _get_remote_agent(thread_id)

    def _get_session():
        mgr = agent._sandbox.manager
        return mgr.session_manager.get(thread_id)

    session = await asyncio.to_thread(_get_session)
    if not session:
        raise HTTPException(404, f"No session found for thread {thread_id}")
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
    agent = await _get_remote_agent(thread_id)

    def _get_terminal():
        mgr = agent._sandbox.manager
        session = mgr.session_manager.get(thread_id)
        if not session:
            return None
        return session.terminal

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
    agent = await _get_remote_agent(thread_id)

    def _get_lease():
        mgr = agent._sandbox.manager
        session = mgr.session_manager.get(thread_id)
        if not session:
            return None
        session.lease.refresh_instance_status(mgr.provider)
        return session.lease

    lease = await asyncio.to_thread(_get_lease)
    if not lease:
        raise HTTPException(404, f"No lease found for thread {thread_id}")

    instance = lease.get_instance()
    created_at, updated_at = await asyncio.to_thread(_get_lease_timestamps, lease.lease_id)
    return {
        "thread_id": thread_id,
        "lease_id": lease.lease_id,
        "provider_name": lease.provider_name,
        "instance": {
            "instance_id": instance.instance_id if instance else None,
            "state": instance.status if instance else None,
            "started_at": instance.created_at.isoformat() if instance and instance.created_at else None,
        } if instance else None,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# --- Thread endpoints ---

@app.post("/api/threads")
async def create_thread(payload: CreateThreadRequest | None = None) -> dict[str, Any]:
    sandbox_type = payload.sandbox if payload else "local"
    thread_id = str(uuid.uuid4())
    app.state.thread_sandbox[thread_id] = sandbox_type
    return {"thread_id": thread_id, "sandbox": sandbox_type}


@app.get("/api/threads")
async def list_threads() -> dict[str, Any]:
    threads = _list_threads_from_db()
    # Enrich with sandbox info
    for t in threads:
        t["sandbox"] = _resolve_thread_sandbox(app, t["thread_id"])
    return {"threads": threads}


@app.get("/api/threads/{thread_id}")
async def get_thread_messages(thread_id: str) -> dict[str, Any]:
    sandbox_type = _resolve_thread_sandbox(app, thread_id)
    agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        set_current_thread_id(thread_id)  # Set thread_id before accessing agent state
        config = {"configurable": {"thread_id": thread_id}}
        state = await agent.agent.aget_state(config)

    values = getattr(state, "values", {}) if state else {}
    messages = values.get("messages", []) if isinstance(values, dict) else []

    # Get sandbox session info (new architecture)
    sandbox_info: dict[str, Any] = {"type": sandbox_type, "status": None, "session_id": None}
    if sandbox_type != "local" and hasattr(agent, "_sandbox"):
        try:
            mgr = agent._sandbox.manager
            session = mgr.session_manager.get(thread_id)
            if session:
                session.lease.refresh_instance_status(mgr.provider)
                instance = session.lease.get_instance()
                sandbox_info["status"] = instance.status if instance else "detached"
                sandbox_info["session_id"] = session.session_id
                sandbox_info["terminal_id"] = session.terminal.terminal_id
        except Exception:
            pass

    return {
        "thread_id": thread_id,
        "messages": [_serialize_message(msg) for msg in messages],
        "sandbox": sandbox_info,
    }


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, Any]:
    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        _delete_thread_in_db(thread_id)
    app.state.thread_sandbox.pop(thread_id, None)
    return {"ok": True, "thread_id": thread_id}


@app.post("/api/threads/{thread_id}/steer")
async def steer_thread(thread_id: str, payload: SteerRequest) -> dict[str, Any]:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    queue_manager = get_queue_manager()
    queue_manager.enqueue(payload.message, mode=QueueMode.STEER)
    return {"ok": True, "thread_id": thread_id, "mode": QueueMode.STEER.value}


# --- Run endpoint (SSE streaming) ---

@app.post("/api/threads/{thread_id}/runs")
async def run_thread(thread_id: str, payload: RunRequest) -> EventSourceResponse:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    sandbox_type = _resolve_thread_sandbox(app, thread_id)

    async def event_stream() -> AsyncGenerator[dict[str, str], None]:
        agent = None
        try:
            set_current_thread_id(thread_id)
            agent = await _get_or_create_agent(app, sandbox_type, thread_id=thread_id)
            lock = await _get_thread_lock(app, thread_id)
            async with lock:
                config = {"configurable": {"thread_id": thread_id}}
                set_current_thread_id(thread_id)

                # @@@ Streaming parser mirrors TUI runner chunk semantics so web and CLI stay consistent.
                if hasattr(agent, "_sandbox") and agent._sandbox.name != "local":
                    agent._sandbox.ensure_session(thread_id)

                if hasattr(agent, "runtime"):
                    agent.runtime.transition(AgentState.ACTIVE)

                async for chunk in agent.agent.astream(
                    {"messages": [{"role": "user", "content": payload.message}]},
                    config=config,
                    stream_mode="updates",
                ):
                    if not chunk:
                        continue

                    for _node_name, node_update in chunk.items():
                        if not isinstance(node_update, dict):
                            continue

                        messages = node_update.get("messages", [])
                        if not isinstance(messages, list):
                            messages = [messages]

                        for msg in messages:
                            msg_class = msg.__class__.__name__

                            if msg_class == "AIMessage":
                                content = _extract_text_content(getattr(msg, "content", ""))
                                if content:
                                    yield {
                                        "event": "text",
                                        "data": json.dumps({"content": content}, ensure_ascii=False),
                                    }
                                for tc in getattr(msg, "tool_calls", []):
                                    yield {
                                        "event": "tool_call",
                                        "data": json.dumps({
                                            "id": tc.get("id"),
                                            "name": tc.get("name", "unknown"),
                                            "args": tc.get("args", {}),
                                        }, ensure_ascii=False),
                                    }

                            elif msg_class == "ToolMessage":
                                yield {
                                    "event": "tool_result",
                                    "data": json.dumps({
                                        "tool_call_id": getattr(msg, "tool_call_id", None),
                                        "name": getattr(msg, "name", "unknown"),
                                        "content": str(getattr(msg, "content", "")),
                                    }, ensure_ascii=False),
                                }

            yield {"event": "done", "data": json.dumps({"thread_id": thread_id})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
        finally:
            if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
                agent.runtime.transition(AgentState.IDLE)

    return EventSourceResponse(event_stream())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
