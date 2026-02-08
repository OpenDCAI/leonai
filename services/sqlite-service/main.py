"""
SQLite Service — standalone HTTP API for SessionStore + MessageQueue.

Runs in Docker, persists to a volume-mounted SQLite file.
LEON clients talk to this via RemoteSessionStore / RemoteMessageQueue.
"""

import json
import sqlite3
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = Path("/data/leon.db")


# ==================== DB layer ====================

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS sandbox_sessions (
                thread_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                session_id TEXT NOT NULL,
                context_id TEXT,
                status TEXT DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS message_queue (
                id TEXT PRIMARY KEY,
                queue TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                claimed_at TIMESTAMP
            )
        """)
        _conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mq_queue_status
            ON message_queue (queue, status, created_at)
        """)
        _conn.commit()
    return _conn


# ==================== Pydantic models ====================


class SessionSaveRequest(BaseModel):
    thread_id: str
    provider: str
    session_id: str
    context_id: str | None = None
    status: str = "running"


class StatusUpdateRequest(BaseModel):
    status: str


class EnqueueRequest(BaseModel):
    queue: str
    payload: dict


class FailRequest(BaseModel):
    error: str = ""


# ==================== App ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_conn()
    yield
    if _conn:
        _conn.close()


app = FastAPI(title="LEON SQLite Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================== Session endpoints ====================


@app.get("/sessions/{thread_id}")
def session_get(thread_id: str):
    conn = get_conn()
    with _lock:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sandbox_sessions WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return dict(row)


@app.get("/sessions")
def session_get_all():
    conn = get_conn()
    with _lock:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM sandbox_sessions").fetchall()
    return [dict(r) for r in rows]


@app.post("/sessions")
def session_save(req: SessionSaveRequest):
    conn = get_conn()
    now = datetime.now().isoformat()
    with _lock:
        conn.execute(
            """
            INSERT OR REPLACE INTO sandbox_sessions
            (thread_id, provider, session_id, context_id, status, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (req.thread_id, req.provider, req.session_id, req.context_id, req.status, now, now),
        )
        conn.commit()
    return {"ok": True}


@app.patch("/sessions/{thread_id}/status")
def session_update_status(thread_id: str, req: StatusUpdateRequest):
    conn = get_conn()
    now = datetime.now().isoformat()
    with _lock:
        conn.execute(
            "UPDATE sandbox_sessions SET status = ?, last_active = ? WHERE thread_id = ?",
            (req.status, now, thread_id),
        )
        conn.commit()
    return {"ok": True}


@app.patch("/sessions/{thread_id}/touch")
def session_touch(thread_id: str):
    conn = get_conn()
    now = datetime.now().isoformat()
    with _lock:
        conn.execute(
            "UPDATE sandbox_sessions SET last_active = ? WHERE thread_id = ?",
            (now, thread_id),
        )
        conn.commit()
    return {"ok": True}


@app.delete("/sessions/{thread_id}")
def session_delete(thread_id: str):
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM sandbox_sessions WHERE thread_id = ?", (thread_id,))
        conn.commit()
    return {"ok": True}


# ==================== Queue endpoints ====================


@app.post("/queue")
def queue_enqueue(req: EnqueueRequest):
    conn = get_conn()
    msg_id = uuid.uuid4().hex[:12]
    with _lock:
        conn.execute(
            "INSERT INTO message_queue (id, queue, payload) VALUES (?, ?, ?)",
            (msg_id, req.queue, json.dumps(req.payload)),
        )
        conn.commit()
    return {"id": msg_id}


@app.post("/queue/{queue_name}/claim")
def queue_claim(queue_name: str):
    conn = get_conn()
    with _lock:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id FROM message_queue
            WHERE queue = ? AND status = 'pending'
            ORDER BY created_at ASC LIMIT 1
            """,
            (queue_name,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="queue empty")

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE message_queue SET status = 'claimed', claimed_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        conn.commit()

        full = conn.execute("SELECT * FROM message_queue WHERE id = ?", (row["id"],)).fetchone()
    return _msg_to_dict(full)


@app.post("/queue/messages/{message_id}/complete")
def queue_complete(message_id: str):
    conn = get_conn()
    with _lock:
        conn.execute(
            "UPDATE message_queue SET status = 'completed' WHERE id = ?", (message_id,)
        )
        conn.commit()
    return {"ok": True}


@app.post("/queue/messages/{message_id}/fail")
def queue_fail(message_id: str, req: FailRequest):
    conn = get_conn()
    with _lock:
        conn.execute(
            "UPDATE message_queue SET status = 'failed', error = ? WHERE id = ?",
            (req.error, message_id),
        )
        conn.commit()
    return {"ok": True}


@app.get("/queue/{queue_name}")
def queue_peek(queue_name: str, limit: int = 10):
    conn = get_conn()
    with _lock:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM message_queue
            WHERE queue = ? AND status = 'pending'
            ORDER BY created_at ASC LIMIT ?
            """,
            (queue_name, limit),
        ).fetchall()
    return [_msg_to_dict(r) for r in rows]


def _msg_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "queue": row["queue"],
        "payload": json.loads(row["payload"]),
        "status": row["status"],
        "error": row["error"],
        "created_at": row["created_at"],
        "claimed_at": row["claimed_at"],
    }
