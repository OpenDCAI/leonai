"""User settings management endpoints."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_FILE = Path.home() / ".leon" / "settings.json"


class UserSettings(BaseModel):
    default_workspace: str | None = None
    recent_workspaces: list[str] = []


class WorkspaceRequest(BaseModel):
    workspace: str


class DirectoryItem(BaseModel):
    name: str
    path: str
    is_dir: bool


class ModelConfigRequest(BaseModel):
    model: str
    thread_id: str | None = None


def load_settings() -> UserSettings:
    """Load user settings from disk."""
    if not SETTINGS_FILE.exists():
        return UserSettings()

    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return UserSettings(**data)
    except Exception:
        return UserSettings()


def save_settings(settings: UserSettings) -> None:
    """Save user settings to disk."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)


@router.get("")
async def get_settings() -> UserSettings:
    """Get user settings."""
    return load_settings()


@router.get("/browse")
async def browse_filesystem(path: str = Query(default="~")) -> dict[str, Any]:
    """Browse filesystem directories."""
    try:
        # Expand ~ and resolve path
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path does not exist")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # Get parent directory
        parent = str(target_path.parent) if target_path.parent != target_path else None

        # List directories only
        items: list[DirectoryItem] = []
        try:
            for item in sorted(target_path.iterdir(), key=lambda x: x.name.lower()):
                if item.is_dir() and not item.name.startswith("."):
                    items.append(DirectoryItem(name=item.name, path=str(item), is_dir=True))
        except PermissionError:
            pass

        return {"current_path": str(target_path), "parent_path": parent, "items": [item.model_dump() for item in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace")
async def set_default_workspace(request: WorkspaceRequest) -> dict[str, Any]:
    """Set default workspace path."""
    # Validate path exists
    workspace_path = Path(request.workspace).expanduser().resolve()
    if not workspace_path.exists():
        raise HTTPException(status_code=400, detail="Workspace path does not exist")

    if not workspace_path.is_dir():
        raise HTTPException(status_code=400, detail="Workspace path is not a directory")

    settings = load_settings()
    settings.default_workspace = str(workspace_path)

    # Add to recent workspaces
    workspace_str = str(workspace_path)
    if workspace_str in settings.recent_workspaces:
        settings.recent_workspaces.remove(workspace_str)
    settings.recent_workspaces.insert(0, workspace_str)
    settings.recent_workspaces = settings.recent_workspaces[:5]  # Keep only 5 recent

    save_settings(settings)
    return {"success": True, "workspace": workspace_str}


@router.post("/workspace/recent")
async def add_recent_workspace(request: WorkspaceRequest) -> dict[str, Any]:
    """Add a workspace to recent list."""
    workspace_path = Path(request.workspace).expanduser().resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid workspace path")

    settings = load_settings()
    workspace_str = str(workspace_path)

    if workspace_str in settings.recent_workspaces:
        settings.recent_workspaces.remove(workspace_str)
    settings.recent_workspaces.insert(0, workspace_str)
    settings.recent_workspaces = settings.recent_workspaces[:5]

    save_settings(settings)
    return {"success": True}


@router.post("/config")
async def update_model_config(request: ModelConfigRequest, req: Request) -> dict[str, Any]:
    """Update model configuration for agent.

    Supports dynamic model switching with virtual model names (leon:*).
    Updates are applied immediately without recreating the agent.
    """
    from backend.web.services.agent_pool import update_agent_config

    try:
        result = await update_agent_config(app_obj=req.app, model=request.model, thread_id=request.thread_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
