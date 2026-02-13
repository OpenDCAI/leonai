"""
Real end-to-end tests simulating frontend interactions with backend API.

NO MOCKS - Tests real HTTP API calls to backend endpoints, exactly as
the frontend would do. This is the 100% equivalent of frontend operations.

Tests the terminal persistence architecture through real API calls.
"""

import asyncio
import os
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
    """Run one SSE cycle and fail loudly on stream error event."""
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
        # @@@sse-event-pairing - SSE lines are split into event/data, we must pair them in order.
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


class TestBackendAPIE2E:
    """Real E2E tests via backend HTTP API - exactly as frontend does."""

    @pytest.mark.asyncio
    async def test_create_thread_with_e2b(self, api_base_url):
        """Test: Create thread with E2B sandbox."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Frontend: POST /api/threads with sandbox type
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "e2b"})
            assert response.status_code == 200
            data = response.json()
            assert "thread_id" in data
            assert data["sandbox"] == "e2b"

    @pytest.mark.asyncio
    async def test_session_terminal_lease_status_endpoints(self, api_base_url):
        """Test: Session/Terminal/Lease status endpoints with strict 200 assertions."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            try:
                await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: session ready")

                response = await client.get(f"{api_base_url}/api/threads/{thread_id}/session")
                assert response.status_code == 200

                response = await client.get(f"{api_base_url}/api/threads/{thread_id}/terminal")
                assert response.status_code == 200

                response = await client.get(f"{api_base_url}/api/threads/{thread_id}/lease")
                assert response.status_code == 200
            finally:
                await client.delete(f"{api_base_url}/api/threads/{thread_id}")

    @pytest.mark.asyncio
    async def test_pause_resume_sandbox(self, api_base_url):
        """Test: Pause and resume sandbox via API with strict 200 assertions."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            try:
                await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: sandbox ready")

                response = await client.post(f"{api_base_url}/api/threads/{thread_id}/sandbox/pause")
                assert response.status_code == 200

                response = await client.post(f"{api_base_url}/api/threads/{thread_id}/sandbox/resume")
                assert response.status_code == 200
            finally:
                await client.delete(f"{api_base_url}/api/threads/{thread_id}")

    @pytest.mark.asyncio
    async def test_list_threads(self, api_base_url):
        """Test: List all threads."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Frontend: GET /api/threads
            response = await client.get(f"{api_base_url}/api/threads")
            assert response.status_code == 200
            data = response.json()
            assert "threads" in data
            # Note: Threads are only persisted to DB when they have chat sessions
            # Creating a thread via POST /api/threads only stores it in memory

    @pytest.mark.asyncio
    async def test_get_thread_messages(self, api_base_url):
        """Test: Get thread messages with strict 200 assertion."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            try:
                await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: message ready")
                response = await client.get(f"{api_base_url}/api/threads/{thread_id}")
                assert response.status_code == 200
                data = response.json()
                assert "messages" in data
            finally:
                await client.delete(f"{api_base_url}/api/threads/{thread_id}")

    @pytest.mark.asyncio
    async def test_delete_thread(self, api_base_url):
        """Test: Delete thread with strict 200 assertion."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            assert response.status_code == 200
            thread_id = response.json()["thread_id"]

            await _run_until_done(client, api_base_url, thread_id, "Reply with exactly: delete ready")
            response = await client.delete(f"{api_base_url}/api/threads/{thread_id}")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_sandbox_types(self, api_base_url):
        """Test: List available sandbox types."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Frontend: GET /api/sandbox/types
            response = await client.get(f"{api_base_url}/api/sandbox/types")
            assert response.status_code == 200
            data = response.json()
            assert "types" in data
            types = data["types"]

            # Should have at least 'local'
            type_names = [t["name"] for t in types]
            assert "local" in type_names

    @pytest.mark.asyncio
    async def test_list_sandbox_sessions(self, api_base_url):
        """Test: List all sandbox sessions."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Frontend: GET /api/sandbox/sessions
            response = await client.get(f"{api_base_url}/api/sandbox/sessions")
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data

    @pytest.mark.asyncio
    async def test_multiple_threads_with_different_sandboxes(self, api_base_url):
        """Test: Create multiple threads with different sandbox types."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create E2B thread
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "e2b"})
            e2b_thread_id = response.json()["thread_id"]
            assert response.json()["sandbox"] == "e2b"

            # Create local thread
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "local"})
            local_thread_id = response.json()["thread_id"]
            assert response.json()["sandbox"] == "local"

            # Verify threads were created with correct sandbox types
            assert e2b_thread_id != local_thread_id

    @pytest.mark.asyncio
    async def test_steer_message(self, api_base_url):
        """Test: Send steering message."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create thread
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "e2b"})
            thread_id = response.json()["thread_id"]

            # Frontend: POST /api/threads/{id}/steer
            response = await client.post(
                f"{api_base_url}/api/threads/{thread_id}/steer", json={"message": "Test steering message"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data or "status" in data


class TestBackendAPIAgentBay:
    """E2E tests with AgentBay sandbox."""

    @pytest.mark.skipif(not os.getenv("AGENTBAY_API_KEY"), reason="AGENTBAY_API_KEY not set")
    @pytest.mark.asyncio
    async def test_create_thread_with_agentbay(self, api_base_url):
        """Test: Create thread with AgentBay sandbox."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "agentbay"})
            assert response.status_code == 200
            data = response.json()
            assert data["sandbox"] == "agentbay"


class TestBackendAPIDaytona:
    """E2E tests with Daytona sandbox."""

    @pytest.mark.skipif(not os.getenv("DAYTONA_API_KEY"), reason="DAYTONA_API_KEY not set")
    @pytest.mark.asyncio
    async def test_create_thread_with_daytona(self, api_base_url):
        """Test: Create thread with Daytona sandbox."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_base_url}/api/threads", json={"sandbox": "daytona"})
            assert response.status_code == 200
            data = response.json()
            assert data["sandbox"] == "daytona"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
