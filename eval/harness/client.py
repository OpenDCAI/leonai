"""SSE client for Leon backend API.

Consumes SSE streams from /api/threads/{id}/runs endpoint,
collecting text chunks, tool calls, tool results, and status snapshots.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from eval.models import TrajectoryCapture


class EvalClient:
    """HTTP + SSE client for driving Leon agent evaluation."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def create_thread(self, sandbox: str = "local", cwd: str | None = None) -> str:
        """Create a new thread. Returns thread_id."""
        payload: dict[str, Any] = {"sandbox": sandbox}
        if cwd:
            payload["cwd"] = cwd
        resp = await self._client.post("/api/threads", json=payload)
        resp.raise_for_status()
        return resp.json()["thread_id"]

    async def run_message(
        self,
        thread_id: str,
        message: str,
        enable_trajectory: bool = True,
    ) -> TrajectoryCapture:
        """Send a message and consume the SSE stream. Returns TrajectoryCapture."""
        capture = TrajectoryCapture()
        payload = {"message": message, "enable_trajectory": enable_trajectory}

        async with self._client.stream(
            "POST",
            f"/api/threads/{thread_id}/runs",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            event_type = ""
            data_buf = ""

            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    data_buf = ""
                elif line.startswith("data:"):
                    data_buf = line[5:].strip()
                elif line == "" and event_type and data_buf:
                    # End of SSE event
                    self._process_event(capture, event_type, data_buf)
                    event_type = ""
                    data_buf = ""

        return capture

    def _process_event(self, capture: TrajectoryCapture, event_type: str, data: str) -> None:
        """Route an SSE event into the appropriate capture bucket."""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            parsed = {"raw": data}

        if event_type == "text":
            content = parsed.get("content", "")
            if content:
                capture.text_chunks.append(content)
        elif event_type == "tool_call":
            capture.tool_calls.append(parsed)
        elif event_type == "tool_result":
            capture.tool_results.append(parsed)
        elif event_type == "status":
            capture.status_snapshots.append(parsed)
            capture.final_status = parsed
        elif event_type in ("done", "cancelled", "error"):
            capture.terminal_event = event_type
            if event_type == "error":
                capture.final_status = parsed

    async def get_runtime(self, thread_id: str) -> dict:
        """Get runtime status for a thread."""
        resp = await self._client.get(f"/api/threads/{thread_id}/runtime")
        resp.raise_for_status()
        return resp.json()

    async def delete_thread(self, thread_id: str) -> None:
        """Delete a thread and its resources."""
        resp = await self._client.delete(f"/api/threads/{thread_id}")
        resp.raise_for_status()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
