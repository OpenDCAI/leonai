"""Langfuse query tool — fetch and format session/trace data by thread ID.

Usage:
    python scripts/langfuse_query.py traces [--limit N]
    python scripts/langfuse_query.py session <thread_id>
    python scripts/langfuse_query.py trace <trace_id>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from langfuse.api.client import FernLangfuse

# Load credentials from observation.json
_OBS_FILE = Path.home() / ".leon" / "observation.json"


def _load_client() -> FernLangfuse:
    if not _OBS_FILE.exists():
        raise SystemExit("No ~/.leon/observation.json found")
    cfg = json.loads(_OBS_FILE.read_text())["langfuse"]
    return FernLangfuse(
        username=cfg["public_key"],
        password=cfg["secret_key"],
        base_url=cfg.get("host", "https://cloud.langfuse.com"),
    )


def _fmt_time(ts: datetime | None) -> str:
    return ts.strftime("%H:%M:%S.%f")[:-3] if ts else "?"


def _fmt_duration(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return "?"
    ms = (end - start).total_seconds() * 1000
    return f"{ms:.0f}ms"


def list_traces(limit: int = 10):
    client = _load_client()
    traces = client.trace.list(limit=limit)
    for t in traces.data:
        print(f"{t.id[:12]}  {_fmt_time(t.timestamp)}  {t.name or '-':<20}  session={t.session_id or '-'}")


def show_session(thread_id: str):
    client = _load_client()
    traces = client.trace.list(session_id=thread_id, limit=50)
    if not traces.data:
        print(f"No traces for session {thread_id}")
        return
    print(f"Session: {thread_id}")
    print(f"Traces: {len(traces.data)}\n")
    for t in sorted(traces.data, key=lambda x: x.timestamp or datetime.min):
        print(f"── Trace {t.id[:12]}  {_fmt_time(t.timestamp)}  {t.name or '-'}")
        obs = client.observations.get_many(trace_id=t.id, limit=100)
        for o in sorted(obs.data, key=lambda x: x.start_time or datetime.min):
            dur = _fmt_duration(o.start_time, o.end_time)
            model = o.model or ""
            tokens = ""
            if o.usage:
                tokens = f"  in={o.usage.input or 0} out={o.usage.output or 0}"
            print(f"   {o.type:<12} {_fmt_time(o.start_time)} {dur:>8}  {o.name or '-':<30} {model:<25}{tokens}")
        print()


def show_trace(trace_id: str):
    client = _load_client()
    t = client.trace.get(trace_id)
    print(f"Trace: {t.id}")
    print(f"Name: {t.name}")
    print(f"Session: {t.session_id}")
    print(f"Time: {_fmt_time(t.timestamp)}")
    print(f"Input: {json.dumps(t.input, ensure_ascii=False)[:200] if t.input else '-'}")
    print(f"Output: {json.dumps(t.output, ensure_ascii=False)[:200] if t.output else '-'}")
    print()
    obs = client.observations.list(trace_id=trace_id, limit=100)
    for o in sorted(obs.data, key=lambda x: x.start_time or datetime.min):
        dur = _fmt_duration(o.start_time, o.end_time)
        print(f"  {o.type:<12} {_fmt_time(o.start_time)} {dur:>8}  {o.name or '-'}")
        if o.input:
            print(f"    input:  {json.dumps(o.input, ensure_ascii=False)[:150]}")
        if o.output:
            print(f"    output: {json.dumps(o.output, ensure_ascii=False)[:150]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "traces":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        list_traces(limit)
    elif cmd == "session":
        if len(sys.argv) < 3:
            print("Usage: session <thread_id>")
            return
        show_session(sys.argv[2])
    elif cmd == "trace":
        if len(sys.argv) < 3:
            print("Usage: trace <trace_id>")
            return
        show_trace(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
