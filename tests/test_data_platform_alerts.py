from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from services.web.data_platform import alerts
from services.web.data_platform.store import create_run, ensure_tables


def _set_started_at(db_path: Path, run_id: str, started_at: str) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE dp_runs SET started_at = ? WHERE run_id = ?", (started_at, run_id))
    conn.commit()
    conn.close()


def test_scan_and_alert_once_sends_once(monkeypatch) -> None:
    with TemporaryDirectory() as td:
        dp_db_path = Path(td) / "dp.db"
        ensure_tables(dp_db_path)
        run_id = create_run(db_path=dp_db_path, thread_id="t1", sandbox="local", input_message="hello")
        _set_started_at(dp_db_path, run_id, "2020-01-01T00:00:00")

        sent_payloads = []

        async def _fake_post(url: str, payload: dict):
            sent_payloads.append((url, payload))

        monkeypatch.setattr(alerts, "_post_json", _fake_post)

        n1 = asyncio.run(
            alerts.scan_and_alert_once(
                dp_db_path=dp_db_path,
                webhook_url="http://example.com/webhook",
                stuck_after_sec=10,
                max_runs=50,
            )
        )
        assert n1 == 1
        assert len(sent_payloads) == 1
        assert sent_payloads[0][1]["run"]["run_id"] == run_id

        n2 = asyncio.run(
            alerts.scan_and_alert_once(
                dp_db_path=dp_db_path,
                webhook_url="http://example.com/webhook",
                stuck_after_sec=10,
                max_runs=50,
            )
        )
        assert n2 == 0
        assert len(sent_payloads) == 1

