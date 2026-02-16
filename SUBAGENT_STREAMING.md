# Sub-Agent Real-Time Streaming Implementation

## Overview
This document describes the implementation of real-time streaming for sub-agent task execution in the Leon AI system.

## Architecture

### Backend Changes

#### 1. AgentRuntime (`middleware/monitor/runtime.py`)
- Added `_subagent_event_buffer: dict[str, list[dict]]` to buffer sub-agent events by parent tool_call_id
- Added `emit_subagent_event(parent_tool_call_id, event)` to buffer events
- Added `get_pending_subagent_events()` to retrieve and clear buffered events

#### 2. TaskResult (`middleware/task/types.py`)
- Added `thread_id: str | None` field to track sub-agent thread ID

#### 3. SubagentRunner (`middleware/task/subagent.py`)
- Updated `task_start` event to include `thread_id` field
- Updated `task_done` event to include `thread_id` field
- Updated `_execute_agent` to return `thread_id` in TaskResult

#### 4. TaskMiddleware (`middleware/task/middleware.py`)
- Added `agent` field to store parent agent reference
- Added `set_agent(agent)` method to set parent agent reference
- Modified `_handle_task` to:
  - Use streaming mode via `runner.run_streaming()`
  - Buffer all sub-agent events to agent runtime via `agent.runtime.emit_subagent_event()`
  - Extract task_id and thread_id from events
  - Return final TaskResult with thread_id

#### 5. LeonAgent (`agent.py`)
- Added call to `self._task_middleware.set_agent(self)` after agent creation

#### 6. Web Service (`services/web/main.py`)
- Added sub-agent event forwarding in main streaming loop:
  - Retrieves pending events via `agent.runtime.get_pending_subagent_events()`
  - Adds `parent_tool_call_id` to event data
  - Emits events with `subagent_` prefix (e.g., `subagent_task_start`)

### Frontend Changes

#### 1. API Types (`frontend/app/src/api.ts`)
- Added new event types: `subagent_task_start`, `subagent_task_text`, `subagent_task_tool_call`, `subagent_task_tool_result`, `subagent_task_done`, `subagent_task_error`
- Added interfaces: `SubagentTaskStartData`, `SubagentTaskTextData`, `SubagentTaskToolCallData`, `SubagentTaskToolResultData`, `SubagentTaskDoneData`, `SubagentTaskErrorData`
- Added `thread_id` field to `TaskDoneData`
- Added `subagent_stream` field to `ToolStep`:
  ```typescript
  subagent_stream?: {
    task_id: string;
    thread_id: string;
    text: string;
    tool_calls: Array<{ id: string; name: string; args: unknown }>;
    status: "running" | "completed" | "error";
    error?: string;
  };
  ```

#### 2. App Component (`frontend/app/src/App.tsx`)
- Added sub-agent event handler in streaming loop:
  - Extracts `parent_tool_call_id` from event data
  - Finds parent tool call in chat entries
  - Initializes `subagent_stream` if not present
  - Updates stream state based on event type:
    - `subagent_task_start`: Sets task_id, thread_id, status
    - `subagent_task_text`: Appends text content
    - `subagent_task_tool_call`: Adds tool call to array
    - `subagent_task_done`: Sets status to "completed"
    - `subagent_task_error`: Sets status to "error" and error message

#### 3. TaskRenderer (`frontend/app/src/components/tool-renderers/TaskRenderer.tsx`)
- Updated to display real-time streaming data:
  - Shows "streaming..." indicator when sub-agent is running
  - Displays sub-agent thread_id and status indicator
  - Shows streaming text content
  - Lists tool calls made by sub-agent
  - Shows error messages if sub-agent fails
  - Uses blue background (#f0f9ff) to distinguish streaming output

## Event Flow

1. **Parent agent calls Task tool**
   - TaskMiddleware receives tool call with tool_call_id
   - Starts streaming sub-agent execution

2. **Sub-agent emits events**
   - Events flow through SubagentRunner.run_streaming()
   - TaskMiddleware buffers events via agent.runtime.emit_subagent_event(tool_call_id, event)

3. **Parent agent streaming loop**
   - After each chunk, web service calls agent.runtime.get_pending_subagent_events()
   - Adds parent_tool_call_id to each event
   - Emits events with subagent_ prefix

4. **Frontend receives events**
   - App.tsx handles subagent_* events
   - Finds parent tool call by parent_tool_call_id
   - Updates subagent_stream state
   - TaskRenderer displays real-time updates

## Benefits

1. **Real-time visibility**: Users see sub-agent progress as it happens
2. **Better UX**: No more waiting for sub-agent to complete before seeing output
3. **Debugging**: Tool calls and errors are visible immediately
4. **Consistency**: Uses same streaming infrastructure as main agent

## Testing

To test the implementation:

1. Start the backend: `cd services/web && uv run uvicorn main:app --reload --port 8001`
2. Start the frontend: `cd frontend/app && npm run dev`
3. Create a thread and send a message that triggers a Task tool call
4. Observe real-time streaming in the TaskRenderer component

## Future Enhancements

1. Add sub-agent output to ComputerPanel AgentsView
2. Support nested sub-agents (sub-agent calling another sub-agent)
3. Add pause/resume controls for sub-agent execution
4. Add sub-agent metrics to runtime status
