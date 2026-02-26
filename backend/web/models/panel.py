"""Pydantic models for panel API (Members, Tasks, Library, Profile)."""

from pydantic import BaseModel


# ── Members ──

class MemberConfigPayload(BaseModel):
    prompt: str | None = None
    rules: list[dict] | None = None
    tools: list[dict] | None = None
    mcps: list[dict] | None = None
    skills: list[dict] | None = None
    subAgents: list[dict] | None = None


class CreateMemberRequest(BaseModel):
    name: str
    description: str = ""


class UpdateMemberRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class PublishMemberRequest(BaseModel):
    bump_type: str = "patch"  # patch | minor | major
    notes: str = ""


# ── Tasks ──

class CreateTaskRequest(BaseModel):
    title: str = "新任务"
    description: str = ""
    assignee_id: str = ""
    priority: str = "medium"
    deadline: str = ""


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    status: str | None = None
    priority: str | None = None
    progress: int | None = None
    deadline: str | None = None


class BulkTaskStatusRequest(BaseModel):
    ids: list[str]
    status: str


# ── Library ──

class CreateResourceRequest(BaseModel):
    name: str
    desc: str = ""
    category: str = ""


class UpdateResourceRequest(BaseModel):
    name: str | None = None
    desc: str | None = None
    category: str | None = None


# ── Profile ──

class UpdateProfileRequest(BaseModel):
    name: str | None = None
    initials: str | None = None
    email: str | None = None


# ── Backward compatibility aliases ──

StaffConfigPayload = MemberConfigPayload
CreateStaffRequest = CreateMemberRequest
UpdateStaffRequest = UpdateMemberRequest
PublishStaffRequest = PublishMemberRequest
