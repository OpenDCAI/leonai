from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import store


@dataclass
class RunLedger:
    """Persisted event ledger for a single run.

    This keeps the frontend thin:
    - live SSE delivers events as usual
    - persisted events allow refresh + cursor-based rehydration
    """

    db_path: Path
    run_id: str
    thread_id: str

    _text_buffer: list[str]
    _finalized: bool

    @classmethod
    def start(cls, *, db_path: Path, thread_id: str, sandbox: str, input_message: str) -> "RunLedger":
        run_id = store.create_run(db_path=db_path, thread_id=thread_id, sandbox=sandbox, input_message=input_message)
        ledger = cls(db_path=db_path, run_id=run_id, thread_id=thread_id, _text_buffer=[], _finalized=False)
        ledger.record("run", {"run_id": run_id, "thread_id": thread_id})
        return ledger

    # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_run_ledger_basic.md`

    def record(self, event_type: str, payload: dict[str, Any]) -> int:
        return store.insert_event(
            db_path=self.db_path,
            run_id=self.run_id,
            thread_id=self.thread_id,
            event_type=event_type,
            payload=payload,
        )

    def emit(self, event_type: str, payload: dict[str, Any], *, persist: bool = True) -> dict[str, str]:
        if persist:
            self.record(event_type, payload)
        return {"event": event_type, "data": json.dumps(payload, ensure_ascii=False)}

    def buffer_text(self, content: str) -> None:
        if not content:
            return
        self._text_buffer.append(content)

    def flush_text(self) -> None:
        if not self._text_buffer:
            return
        text = "".join(self._text_buffer)
        self._text_buffer.clear()
        # Persist coalesced assistant text for refresh; we intentionally do not store every token chunk.
        self.record("text_full", {"content": text})

    def finalize(self, *, status: str, error: str | None = None) -> None:
        if self._finalized:
            return
        self.flush_text()
        store.finalize_run(db_path=self.db_path, run_id=self.run_id, status=status, error=error)
        self._finalized = True
