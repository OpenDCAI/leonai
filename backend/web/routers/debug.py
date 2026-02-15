"""Debug logging endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/debug", tags=["debug"])


class LogMessage(BaseModel):
    message: str
    timestamp: str


@router.post("/log")
async def log_frontend_message(payload: LogMessage) -> dict:
    """Receive frontend console logs and write to file."""
    with open("/tmp/leon-frontend-console.log", "a") as f:
        f.write(f"[{payload.timestamp}] {payload.message}\n")
    return {"status": "ok"}
