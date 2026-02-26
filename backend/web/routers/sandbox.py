"""Sandbox management endpoints."""

import asyncio
import subprocess
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.web.services.sandbox_service import (
    available_sandbox_types,
    find_session_and_manager,
    init_providers_and_managers,
    load_all_sessions,
    mutate_sandbox_session,
)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


@router.get("/types")
async def list_sandbox_types() -> dict[str, Any]:
    """List available sandbox types."""
    types = await asyncio.to_thread(available_sandbox_types)
    return {"types": types}


@router.get("/pick-folder")
async def pick_folder() -> dict[str, Any]:
    """Open system folder picker dialog and return selected path."""
    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'POSIX path of (choose folder with prompt "选择工作目录")',
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                return {"path": path}
            else:
                raise HTTPException(400, "User cancelled folder selection")
        elif sys.platform == "win32":  # Windows
            # Use PowerShell folder browser
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = "选择工作目录"
            $dialog.ShowNewFolderButton = $true
            if ($dialog.ShowDialog() -eq 'OK') {
                Write-Output $dialog.SelectedPath
            }
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                return {"path": path}
            else:
                raise HTTPException(400, "User cancelled folder selection")
        else:  # Linux
            # Try zenity first, fallback to kdialog
            try:
                result = subprocess.run(
                    ["zenity", "--file-selection", "--directory", "--title=选择工作目录"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    return {"path": path}
            except FileNotFoundError:
                # Try kdialog
                result = subprocess.run(
                    ["kdialog", "--getexistingdirectory", ".", "--title", "选择工作目录"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    return {"path": path}
            raise HTTPException(400, "User cancelled folder selection")
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Folder selection timed out")
    # @@@http_passthrough - keep explicit business/status errors from selection branches intact
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to open folder picker: {str(e)}") from e


@router.get("/sessions")
async def list_sandbox_sessions() -> dict[str, Any]:
    """List all sandbox sessions across providers."""
    # Read-only: standalone managers are fine for listing
    _, managers = await asyncio.to_thread(init_providers_and_managers)
    sessions = await asyncio.to_thread(load_all_sessions, managers)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/metrics")
async def get_session_metrics(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    """Get metrics for a specific sandbox session."""
    providers, managers = await asyncio.to_thread(init_providers_and_managers)
    sessions = await asyncio.to_thread(load_all_sessions, managers)
    try:
        session, _ = find_session_and_manager(sessions, managers, session_id, provider_name=provider)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    if not session:
        raise HTTPException(404, f"Session not found: {session_id}")
    provider_obj = providers.get(session["provider"])
    if not provider_obj:
        return {"session_id": session["session_id"], "metrics": None}
    metrics = await asyncio.to_thread(provider_obj.get_metrics, session["session_id"])
    web_url = None
    if hasattr(provider_obj, "get_web_url"):
        web_url = await asyncio.to_thread(provider_obj.get_web_url, session["session_id"])
    result: dict[str, Any] = {"session_id": session["session_id"], "metrics": None, "web_url": web_url}
    if metrics:
        result["metrics"] = {
            "cpu_percent": metrics.cpu_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "memory_total_mb": metrics.memory_total_mb,
            "disk_used_gb": metrics.disk_used_gb,
            "disk_total_gb": metrics.disk_total_gb,
            "network_rx_kbps": metrics.network_rx_kbps,
            "network_tx_kbps": metrics.network_tx_kbps,
        }
    return result


@router.post("/sessions/{session_id}/pause")
async def pause_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    """Pause a sandbox session."""
    try:
        return await asyncio.to_thread(
            mutate_sandbox_session,
            session_id=session_id,
            action="pause",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e


@router.post("/sessions/{session_id}/resume")
async def resume_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    """Resume a paused sandbox session."""
    try:
        return await asyncio.to_thread(
            mutate_sandbox_session,
            session_id=session_id,
            action="resume",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e


@router.delete("/sessions/{session_id}")
async def destroy_sandbox_session(session_id: str, provider: str | None = Query(default=None)) -> dict[str, Any]:
    """Destroy a sandbox session."""
    try:
        return await asyncio.to_thread(
            mutate_sandbox_session,
            session_id=session_id,
            action="destroy",
            provider_hint=provider,
        )
    except RuntimeError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status, message) from e
