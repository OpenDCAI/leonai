"""
E2E test: run execution must survive SSE disconnect (refresh) and allow join/replay.

This test is intentionally close to how the web frontend should behave:
- Start run via POST /api/threads/{id}/runs (SSE)
- Disconnect early (simulating refresh/tab close)
- Confirm backend runtime still ACTIVE and exposes active_run_id
- Join via POST /api/threads/{id}/runs/{run_id}/join (SSE) and finish
"""

import asyncio
import json
import time

import httpx
import pytest


@pytest.fixture
def api_base_url() -> str:
    return "http://localhost:8001"


@pytest.fixture(autouse=True)
def _require_backend(api_base_url: str):
    try:
        response = httpx.get(f"{api_base_url}/api/sandbox/types", timeout=2.0, trust_env=False)
    except Exception:
        pytest.skip(f"backend not reachable at {api_base_url}")
    if response.status_code >= 500:
        pytest.skip(f"backend unhealthy at {api_base_url} (status={response.status_code})")


async def _read_sse_until(
    response: httpx.Response,
    *,
    stop_on_events: set[str],
    max_seconds: float = 10.0,
) -> dict[str, list[str]]:
    """Collect SSE data lines until we see an event in stop_on_events."""
    event_name = ""
    seen: dict[str, list[str]] = {}
    deadline = time.monotonic() + max_seconds

    async for line in response.aiter_lines():
        if time.monotonic() > deadline:
            break
        if not line:
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line.split(":", 1)[1].strip()
        seen.setdefault(event_name, []).append(payload)
        if event_name in stop_on_events:
            break

    return seen


async def _wait_runtime_state(
    client: httpx.AsyncClient,
    api_base_url: str,
    thread_id: str,
    *,
    want: str,
    timeout_sec: float = 10.0,
) -> dict:
    deadline = time.monotonic() + timeout_sec
    last_payload: dict | None = None
    while time.monotonic() < deadline:
        resp = await client.get(f"{api_base_url}/api/threads/{thread_id}/runtime")
        assert resp.status_code == 200
        payload = resp.json()
        last_payload = payload
        state = payload.get("state", {}).get("state")
        if state == want:
            return payload
        await asyncio.sleep(0.2)
    raise AssertionError(f"runtime did not reach state={want} within {timeout_sec}s, last={last_payload}")


class TestRunAttachResumeE2E:
    @pytest.mark.asyncio
    async def test_disconnect_does_not_stop_run_and_join_finishes(self, api_base_url: str):
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert resp.status_code == 200
            thread_id = resp.json()["thread_id"]

            try:
                # Start a run that should last long enough to simulate refresh.
                msg = (
                    "Use the run_command tool exactly once with:\n"
                    "- CommandLine: sleep 5; echo RUN_OK\n"
                    "- Timeout: 30\n"
                    "After the command completes, reply with exactly: done"
                )

                run_id: str | None = None
                async with client.stream(
                    "POST",
                    f"{api_base_url}/api/threads/{thread_id}/runs",
                    json={"message": msg},
                    timeout=180.0,
                ) as sse:
                    assert sse.status_code == 200
                    seen = await _read_sse_until(sse, stop_on_events={"tool_call"}, max_seconds=10.0)
                    for raw in seen.get("status", []):
                        try:
                            payload = json.loads(raw)
                        except Exception:
                            continue
                        rid = payload.get("active_run_id")
                        if rid:
                            run_id = rid
                            break

                # SSE disconnected here (refresh). Run must continue.
                runtime = await _wait_runtime_state(client, api_base_url, thread_id, want="active", timeout_sec=3.0)
                run_id = run_id or runtime.get("active_run_id")
                assert run_id, f"expected active_run_id in runtime, got: {runtime}"

                # Join and finish.
                seen_done = False
                error_payload: str | None = None
                async with client.stream(
                    "POST",
                    f"{api_base_url}/api/threads/{thread_id}/runs/{run_id}/join",
                    params={"cursor": 0},
                    timeout=180.0,
                ) as join:
                    assert join.status_code == 200
                    event_name = ""
                    async for line in join.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("event:"):
                            event_name = line.split(":", 1)[1].strip()
                            continue
                        if not line.startswith("data:"):
                            continue
                        payload = line.split(":", 1)[1].strip()
                        if event_name == "error":
                            error_payload = payload
                            break
                        if event_name == "done":
                            seen_done = True
                            break

                assert error_payload is None, f"join stream returned error event: {error_payload}"
                assert seen_done, "join stream ended without done event"

                await _wait_runtime_state(client, api_base_url, thread_id, want="idle", timeout_sec=15.0)
            finally:
                await client.delete(f"{api_base_url}/api/threads/{thread_id}")
