"""
Complete frontend flow E2E tests with strict assertions.

NO MOCKS - Real HTTP API calls exactly as frontend does.
"""

import asyncio
import time

import httpx
import pytest


@pytest.fixture
def api_base_url():
    """Backend API base URL."""
    return "http://localhost:8001"


@pytest.fixture(autouse=True)
def _require_backend(api_base_url: str):
    try:
        response = httpx.get(f"{api_base_url}/api/sandbox/types", timeout=2.0)
    except Exception:
        pytest.skip(f"backend not reachable at {api_base_url}")
    if response.status_code >= 500:
        pytest.skip(f"backend unhealthy at {api_base_url} (status={response.status_code})")


async def _run_until_done(client: httpx.AsyncClient, api_base_url: str, thread_id: str, message: str) -> None:
    seen_done = False
    error_payload: str | None = None
    async with client.stream(
        "POST",
        f"{api_base_url}/api/threads/{thread_id}/runs",
        json={"message": message},
        timeout=180.0,
    ) as response:
        assert response.status_code == 200
        event_name = ""
        # @@@sse-event-pairing - Parse SSE event/data pairs to fail on backend error events.
        async for line in response.aiter_lines():
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

    assert error_payload is None, f"SSE returned error event: {error_payload}"
    assert seen_done, "SSE stream ended without done event"

    # @@@runtime-idle-gate - `done` can arrive before runtime state transition settles.
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        status = await client.get(f"{api_base_url}/api/threads/{thread_id}/runtime")
        assert status.status_code == 200
        state = status.json().get("state", {}).get("state")
        if state == "idle":
            return
        await asyncio.sleep(0.2)
    raise AssertionError("Runtime did not reach idle state within 10 seconds after done event")


class TestCompleteFrontendFlow:
    """Complete E2E tests tracing strict frontend flow."""

    @pytest.mark.asyncio
    async def test_complete_user_journey_with_local(self, api_base_url):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{api_base_url}/api/sandbox/types")
            assert response.status_code == 200
            sandbox_types = response.json()["types"]
            assert any(t["name"] == "local" for t in sandbox_types)

            response = await client.get(f"{api_base_url}/api/threads")
            assert response.status_code == 200
            assert "threads" in response.json()

            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread = response.json()
            thread_id = thread["thread_id"]
            assert thread["sandbox"] == "local"

            try:
                await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: frontend flow ready")

                response = await client.get(f"{api_base_url}/api/threads/{thread_id}")
                assert response.status_code == 200
                thread_data = response.json()
                assert "messages" in thread_data

                # @@@promise-all-strictness - Frontend fetches these in parallel; all must return 200 after runtime init.
                session_response, terminal_response, lease_response = await asyncio.gather(
                    client.get(f"{api_base_url}/api/threads/{thread_id}/session"),
                    client.get(f"{api_base_url}/api/threads/{thread_id}/terminal"),
                    client.get(f"{api_base_url}/api/threads/{thread_id}/lease"),
                )
                assert session_response.status_code == 200
                assert terminal_response.status_code == 200
                assert lease_response.status_code == 200

                response = await client.post(f"{api_base_url}/api/threads/{thread_id}/sandbox/pause")
                assert response.status_code == 200
                response = await client.post(f"{api_base_url}/api/threads/{thread_id}/sandbox/resume")
                assert response.status_code == 200
            finally:
                response = await client.delete(f"{api_base_url}/api/threads/{thread_id}")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_status_panel_parallel_fetch(self, api_base_url):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            try:
                await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: panel ready")

                session_resp, terminal_resp, lease_resp = await asyncio.gather(
                    client.get(f"{api_base_url}/api/threads/{thread_id}/session"),
                    client.get(f"{api_base_url}/api/threads/{thread_id}/terminal"),
                    client.get(f"{api_base_url}/api/threads/{thread_id}/lease"),
                )

                assert session_resp.status_code == 200
                assert terminal_resp.status_code == 200
                assert lease_resp.status_code == 200
            finally:
                response = await client.delete(f"{api_base_url}/api/threads/{thread_id}")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_steer_message_flow(self, api_base_url):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            try:
                response = await client.post(
                    f"{api_base_url}/api/threads/{thread_id}/steer", json={"message": "Test steering message"}
                )
                assert response.status_code == 200
                result = response.json()
                assert "ok" in result or "status" in result
            finally:
                response = await client.delete(f"{api_base_url}/api/threads/{thread_id}")
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
