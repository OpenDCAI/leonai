"""
Remote store/queue — HTTP clients for the Docker SQLite service.

Implements SessionStore and MessageQueue ABCs by calling the
FastAPI service at the configured URL.
"""

import httpx

from sandbox.message_queue import Message, MessageQueue
from sandbox.provider import SessionInfo
from sandbox.session_store import SessionStore

DEFAULT_URL = "http://localhost:8100"


class RemoteSessionStore(SessionStore):
    def __init__(self, base_url: str = DEFAULT_URL):
        self._url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._url, timeout=10)

    def get(self, thread_id: str) -> dict | None:
        r = self._client.get(f"/sessions/{thread_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def get_all(self) -> list[dict]:
        r = self._client.get("/sessions")
        r.raise_for_status()
        return r.json()

    def save(self, thread_id: str, info: SessionInfo, context_id: str | None) -> None:
        r = self._client.post("/sessions", json={
            "thread_id": thread_id,
            "provider": info.provider,
            "session_id": info.session_id,
            "context_id": context_id,
            "status": info.status,
        })
        r.raise_for_status()

    def update_status(self, thread_id: str, status: str) -> None:
        r = self._client.patch(
            f"/sessions/{thread_id}/status",
            json={"status": status},
        )
        r.raise_for_status()

    def touch(self, thread_id: str) -> None:
        r = self._client.patch(f"/sessions/{thread_id}/touch")
        r.raise_for_status()

    def delete(self, thread_id: str) -> None:
        r = self._client.delete(f"/sessions/{thread_id}")
        r.raise_for_status()

    def close(self) -> None:
        self._client.close()


class RemoteMessageQueue(MessageQueue):
    def __init__(self, base_url: str = DEFAULT_URL):
        self._url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._url, timeout=10)

    def enqueue(self, queue: str, payload: dict) -> str:
        r = self._client.post("/queue", json={"queue": queue, "payload": payload})
        r.raise_for_status()
        return r.json()["id"]

    def claim(self, queue: str) -> Message | None:
        r = self._client.post(f"/queue/{queue}/claim")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        return Message(
            id=d["id"],
            queue=d["queue"],
            payload=d["payload"],
            status=d["status"],
            created_at=d.get("created_at"),
            claimed_at=d.get("claimed_at"),
        )

    def complete(self, message_id: str) -> None:
        r = self._client.post(f"/queue/messages/{message_id}/complete")
        r.raise_for_status()

    def fail(self, message_id: str, error: str = "") -> None:
        r = self._client.post(
            f"/queue/messages/{message_id}/fail",
            json={"error": error},
        )
        r.raise_for_status()

    def peek(self, queue: str, limit: int = 10) -> list[Message]:
        r = self._client.get(f"/queue/{queue}", params={"limit": limit})
        r.raise_for_status()
        return [
            Message(
                id=d["id"],
                queue=d["queue"],
                payload=d["payload"],
                status=d["status"],
                created_at=d.get("created_at"),
                claimed_at=d.get("claimed_at"),
            )
            for d in r.json()
        ]

    def close(self) -> None:
        self._client.close()
