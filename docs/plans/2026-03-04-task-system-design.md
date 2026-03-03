# Task System V1 Design

## Context

Leon has three independent "task" systems that don't communicate:

| System | Location | Purpose | Storage |
|--------|----------|---------|---------|
| TodoMiddleware | `core/todo/` | Agent's internal work tracking | In-memory |
| Panel Tasks | `backend/web/services/task_service.py` | User-facing task board | SQLite |
| TaskMiddleware | `core/task/` | Sub-agent orchestration | N/A |

**Goal**: Keep Panel Tasks as the unified task store, add Cron production + Agent consumption + real-time Dashboard.

## Architecture: Lightweight In-Process (Option A)

- Cron: APScheduler running inside FastAPI process, jobs stored in SQLite
- Agent consumption: New tools for agents to claim/update/complete board tasks
- Dashboard: Enhanced existing TasksPage with Cron tab + real-time polling

```
┌──────────────── Task Production ────────────────┐
│                                                   │
│  Manual create ──┐                                │
│  Agent create ───┤──→ panel_tasks (SQLite)        │
│  Cron trigger ───┘         ↑                      │
│                      CronService                  │
└───────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────── Task Consumption ────────────────┐
│                                                   │
│  Agent IDLE → check pending tasks                 │
│    → auto-claim (or prompt user, configurable)    │
│    → execute in new/current Thread                │
│    → update progress in real-time                 │
│    → complete/fail → write result back            │
│                                                   │
└───────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────── Dashboard ───────────────────────┐
│                                                   │
│  Tasks Tab: Table/Kanban + real-time + filters    │
│  Cron Tab: Job list + edit + enable/disable       │
│  Stats: running/pending/completed/failed/today    │
│                                                   │
└───────────────────────────────────────────────────┘
```

## Data Model

### panel_tasks (extend existing)

New columns added to existing table:

```sql
thread_id TEXT DEFAULT '',        -- associated Thread (bound when Agent executes)
source TEXT DEFAULT 'manual',     -- origin: manual | cron | agent | queue
cron_job_id TEXT DEFAULT '',      -- associated Cron Job ID
result TEXT DEFAULT '',           -- execution result summary
started_at INTEGER DEFAULT 0,    -- execution start time (epoch ms)
completed_at INTEGER DEFAULT 0,  -- completion time (epoch ms)
```

### cron_jobs (new table)

```sql
CREATE TABLE cron_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    cron_expression TEXT NOT NULL,   -- standard cron: "0 9 * * *"
    task_template TEXT DEFAULT '{}', -- JSON: {title, priority, assignee_id, ...}
    enabled INTEGER DEFAULT 1,
    last_run_at INTEGER DEFAULT 0,
    next_run_at INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
)
```

## Cron System

**Tech**: APScheduler 4.x (async-native, SQLite job store)

**Lifecycle**:
1. FastAPI startup → `CronService.start()` → load enabled jobs from `cron_jobs`
2. Register each as APScheduler trigger
3. On trigger: create `panel_tasks` record from `task_template`, update `last_run_at`/`next_run_at`
4. FastAPI shutdown → `CronService.stop()` → graceful cleanup

**API** (extend `backend/web/routers/panel.py`):

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/panel/cron-jobs` | Create cron job |
| GET | `/api/panel/cron-jobs` | List all cron jobs |
| PUT | `/api/panel/cron-jobs/{id}` | Update cron job |
| DELETE | `/api/panel/cron-jobs/{id}` | Delete cron job |
| POST | `/api/panel/cron-jobs/{id}/run` | Manual trigger (debug) |

**Agent tool**: `CreateCronJob(name, description, cron_expression, task_template)` — Agent creates cron jobs, user edits on Dashboard.

## Agent Consumption

### New middleware: TaskBoardMiddleware

Location: `core/taskboard/middleware.py`

**Tools exposed to Agent**:

| Tool | Description |
|------|-------------|
| `ListBoardTasks(status?, priority?)` | Query pending tasks from board |
| `ClaimTask(task_id)` | Claim task (status→running, bind thread_id) |
| `UpdateTaskProgress(task_id, progress, note?)` | Update progress 0-100 |
| `CompleteTask(task_id, result)` | Mark complete with result summary |
| `FailTask(task_id, reason)` | Mark failed with reason |
| `CreateBoardTask(title, description, priority?, cron_expression?)` | Create task (optionally with cron schedule) |

### Idle auto-pickup

```
Agent enters IDLE state (via MonitorMiddleware callback)
  → TaskBoardMiddleware.on_idle()
  → Query panel_tasks WHERE status='pending' ORDER BY priority, created_at
  → If tasks found:
      → auto_claim=true: automatically claim highest-priority task
      → auto_claim=false: send prompt to user for confirmation
  → If no tasks: stay idle
```

Configuration: `auto_claim_tasks` setting (default: true), configurable per-agent or globally.

### Execution model

Task execution mode is a **runtime choice**, not hardcoded:
- **inline**: Execute in current Thread (user sees the process)
- **background**: Create new Thread, execute independently

The agent or user decides at claim time. `ClaimTask(task_id, mode='background')`.

## Dashboard Frontend

### Task card enhancements

- `source` badge (Manual / Cron / Agent)
- `thread_id` link (click to jump to associated conversation)
- Live execution indicator (spinner when agent is actively processing)
- `result` preview (shown after completion)

### New Cron Tab

Tab switcher at top of TasksPage: `任务看板 | 定时任务`

Cron page shows:
- Job list (name, human-readable schedule, next trigger time, enabled toggle)
- Edit panel (reuse existing right-panel pattern)
- Manual trigger button
- History: recent tasks created by this cron job

### Real-time refresh

- Polling every 5s (`fetchTasks()`) — simple, reliable
- Future: upgrade to SSE push

### Stats bar enhancement

```
Existing: 执行中 / 等待 / 完成 / 失败
Add: 今日完成 / Cron 待触发
```

## New Backend Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| CronService | `backend/web/services/cron_service.py` | APScheduler lifecycle, job CRUD, trigger logic |
| TaskBoardMiddleware | `core/taskboard/middleware.py` | Agent tools, idle callback |
| Cron API | `backend/web/routers/panel.py` (extend) | Cron job REST endpoints |
| panel_tasks migration | `backend/web/services/task_service.py` | Add new columns |

## Unchanged

- `core/todo/` — Agent internal scratchpad, untouched
- `core/task/` — Sub-agent orchestration, untouched
- TasksPage UI structure — enhanced, not rewritten

## Future (V2+)

- Chat integration: user says "帮我做X，不急" → Agent auto-creates board task
- Inbox Manager: dedicated Member agent for task triage
- SSE push for real-time dashboard (replace polling)
- Task dependencies (blocks/blockedBy on board level)
- Task templates and recurring patterns
