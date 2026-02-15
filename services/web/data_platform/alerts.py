from __future__ import annotations

import asyncio
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from . import store


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return int(default)
    return int(raw)


def _webhook_url() -> str | None:
    url = (os.getenv("LEON_ALERT_WEBHOOK_URL") or "").strip()
    return url or None


async def _post_json(url: str, payload: dict[str, Any]) -> None:
    # Explicitly ignore env proxies: local infra often sets a system proxy that breaks loopback URLs.
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()


async def scan_and_alert_once(
    *,
    dp_db_path: Path,
    webhook_url: str,
    stuck_after_sec: int,
    max_runs: int = 50,
) -> int:
    """Scan stuck runs and send webhook alerts once per run (persisted via dp_run_events)."""
    stuck = store.list_stuck_runs(db_path=dp_db_path, stuck_after_sec=stuck_after_sec, limit=max_runs)
    sent = 0
    for r in stuck:
        if store.has_event_type(db_path=dp_db_path, run_id=r.run_id, event_type="alert_sent"):
            continue
        payload = {
            "type": "stuck_run",
            "sent_at": _now_iso(),
            "stuck_after_sec": int(stuck_after_sec),
            "run": {
                "run_id": r.run_id,
                "thread_id": r.thread_id,
                "sandbox": r.sandbox,
                "input_message": r.input_message,
                "status": r.status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "error": r.error,
            },
        }
        await _post_json(webhook_url, payload)
        u = urlsplit(webhook_url)
        store.insert_event(
            db_path=dp_db_path,
            run_id=r.run_id,
            thread_id=r.thread_id,
            event_type="alert_sent",
            payload={"sent_at": payload["sent_at"], "webhook": {"host": u.netloc, "path": u.path}},
        )
        sent += 1
    return sent


async def alerts_loop(app_obj: Any, *, dp_db_path: Path) -> None:
    # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_dashboards_and_alerts.md`
    interval_sec = _env_int("LEON_ALERT_INTERVAL_SEC", 30)
    stuck_after_sec = _env_int("LEON_ALERT_STUCK_AFTER_SEC", 600)
    max_runs = _env_int("LEON_ALERT_MAX_RUNS_PER_TICK", 50)

    while True:
        try:
            url = _webhook_url()
            if not url:
                # Fail loudly if misconfigured: the task should not be running without a webhook URL.
                raise RuntimeError("LEON_ALERT_WEBHOOK_URL is required to run alerts_loop")
            sent = await scan_and_alert_once(
                dp_db_path=dp_db_path,
                webhook_url=url,
                stuck_after_sec=stuck_after_sec,
                max_runs=max_runs,
            )
            if sent:
                print(f"[alerts] sent {sent} stuck-run alert(s)")
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(interval_sec)
