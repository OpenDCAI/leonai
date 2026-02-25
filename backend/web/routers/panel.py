"""Panel API router — Staff, Tasks, Library, Profile."""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.web.models.panel import (
    BulkTaskStatusRequest,
    CreateResourceRequest,
    CreateStaffRequest,
    CreateTaskRequest,
    PublishStaffRequest,
    StaffConfigPayload,
    UpdateProfileRequest,
    UpdateResourceRequest,
    UpdateStaffRequest,
    UpdateTaskRequest,
)
from backend.web.services import panel_service as svc

router = APIRouter(prefix="/api/panel", tags=["panel"])


# ── Staff ──

@router.get("/staff")
async def list_staff() -> dict[str, Any]:
    items = await asyncio.to_thread(svc.list_staff)
    return {"items": items}


@router.get("/staff/{staff_id}")
async def get_staff(staff_id: str) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.get_staff, staff_id)
    if not item:
        raise HTTPException(404, "Staff not found")
    return item


@router.post("/staff")
async def create_staff(req: CreateStaffRequest) -> dict[str, Any]:
    return await asyncio.to_thread(svc.create_staff, req.name, req.description)


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, req: UpdateStaffRequest) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.update_staff, staff_id, **req.model_dump())
    if not item:
        raise HTTPException(404, "Staff not found")
    return item

@router.put("/staff/{staff_id}/config")
async def update_staff_config(staff_id: str, req: StaffConfigPayload) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.update_staff_config, staff_id, req.model_dump())
    if not item:
        raise HTTPException(404, "Staff not found")
    return item


@router.put("/staff/{staff_id}/publish")
async def publish_staff(staff_id: str, req: PublishStaffRequest) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.publish_staff, staff_id, req.bump_type)
    if not item:
        raise HTTPException(404, "Staff not found")
    return item


@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: str) -> dict[str, Any]:
    ok = await asyncio.to_thread(svc.delete_staff, staff_id)
    if not ok:
        raise HTTPException(404, "Staff not found")
    return {"success": True}


# ── Tasks ──

@router.get("/tasks")
async def list_tasks() -> dict[str, Any]:
    items = await asyncio.to_thread(svc.list_tasks)
    return {"items": items}


@router.post("/tasks")
async def create_task(req: CreateTaskRequest) -> dict[str, Any]:
    return await asyncio.to_thread(svc.create_task, **req.model_dump())


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, req: UpdateTaskRequest) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.update_task, task_id, **req.model_dump())
    if not item:
        raise HTTPException(404, "Task not found")
    return item


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict[str, Any]:
    ok = await asyncio.to_thread(svc.delete_task, task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"success": True}


@router.put("/tasks/bulk-status")
async def bulk_update_status(req: BulkTaskStatusRequest) -> dict[str, Any]:
    count = await asyncio.to_thread(svc.bulk_update_task_status, req.ids, req.status)
    return {"updated": count}


# ── Library ──

@router.get("/library/{resource_type}")
async def list_library(resource_type: str) -> dict[str, Any]:
    items = await asyncio.to_thread(svc.list_library, resource_type)
    return {"items": items}


@router.post("/library/{resource_type}")
async def create_resource(resource_type: str, req: CreateResourceRequest) -> dict[str, Any]:
    return await asyncio.to_thread(svc.create_resource, resource_type, req.name, req.desc, req.category)


@router.put("/library/{resource_type}/{resource_id}")
async def update_resource(resource_type: str, resource_id: str, req: UpdateResourceRequest) -> dict[str, Any]:
    item = await asyncio.to_thread(svc.update_resource, resource_type, resource_id, **req.model_dump())
    if not item:
        raise HTTPException(404, "Resource not found")
    return item


@router.delete("/library/{resource_type}/{resource_id}")
async def delete_resource(resource_type: str, resource_id: str) -> dict[str, Any]:
    ok = await asyncio.to_thread(svc.delete_resource, resource_type, resource_id)
    if not ok:
        raise HTTPException(404, "Resource not found")
    return {"success": True}


@router.get("/library/{resource_type}/{resource_name}/used-by")
async def get_used_by(resource_type: str, resource_name: str) -> dict[str, Any]:
    count = await asyncio.to_thread(svc.get_resource_used_by, resource_type, resource_name)
    return {"count": count}


# ── Profile ──

@router.get("/profile")
async def get_profile() -> dict[str, Any]:
    return await asyncio.to_thread(svc.get_profile)


@router.put("/profile")
async def update_profile(req: UpdateProfileRequest) -> dict[str, Any]:
    return await asyncio.to_thread(svc.update_profile, **req.model_dump())
