import { flushSync } from "react-dom";
import {
  type AssistantTurn,
  type ChatEntry,
  type StreamStatus,
  type ToolSegment,
} from "../api";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export type UpdateEntries = (updater: (prev: ChatEntry[]) => ChatEntry[]) => void;
export type StreamEvent = { type: string; data?: unknown };

export function processStreamEvent(
  event: StreamEvent,
  turnId: string,
  onUpdate: UpdateEntries,
  setIsStreaming: (v: boolean) => void,
  setRuntimeStatus: (v: StreamStatus | null) => void,
) {
  switch (event.type) {
    case "text":
      handleTextEvent(event, turnId, onUpdate);
      return;
    case "tool_call":
      handleToolCallEvent(event, turnId, onUpdate);
      return;
    case "tool_result":
      handleToolResultEvent(event, turnId, onUpdate);
      return;
    case "status": {
      const status = event.data as StreamStatus | undefined;
      if (status) setRuntimeStatus(status);
      return;
    }
    case "error":
      handleErrorEvent(event, turnId, onUpdate);
      return;
    case "cancelled":
      handleCancelledEvent(event, turnId, onUpdate, setIsStreaming);
      return;
    default:
      if (event.type.startsWith("subagent_")) {
        handleSubagentEvent(event, turnId, onUpdate);
      }
  }
}

function updateTurnSegments(
  onUpdate: UpdateEntries,
  turnId: string,
  updater: (turn: AssistantTurn) => AssistantTurn,
) {
  onUpdate((prev) =>
    prev.map((e) =>
      e.id === turnId && e.role === "assistant" ? updater(e as AssistantTurn) : e,
    ),
  );
}

function handleTextEvent(event: StreamEvent, turnId: string, onUpdate: UpdateEntries) {
  const payload = event.data as { content?: string } | string | undefined;
  const chunk = typeof payload === "string" ? payload : payload?.content ?? "";
  flushSync(() => {
    updateTurnSegments(onUpdate, turnId, (turn) => {
      const segs = [...turn.segments];
      const last = segs[segs.length - 1];
      if (last && last.type === "text") {
        segs[segs.length - 1] = { type: "text", content: last.content + chunk };
      } else {
        segs.push({ type: "text", content: chunk });
      }
      return { ...turn, segments: segs };
    });
  });
}

function handleToolCallEvent(event: StreamEvent, turnId: string, onUpdate: UpdateEntries) {
  const payload = (event.data ?? {}) as { id?: string; name?: string; args?: unknown };
  const seg: ToolSegment = {
    type: "tool",
    step: {
      id: payload.id ?? makeId("tc"),
      name: payload.name ?? "tool",
      args: payload.args ?? {},
      status: "calling",
      timestamp: Date.now(),
    },
  };
  updateTurnSegments(onUpdate, turnId, (turn) => ({
    ...turn,
    segments: [...turn.segments, seg],
  }));
}

function handleToolResultEvent(event: StreamEvent, turnId: string, onUpdate: UpdateEntries) {
  const payload = (event.data ?? {}) as { content?: string; tool_call_id?: string; name?: string };

  const updateResult = () => {
    updateTurnSegments(onUpdate, turnId, (turn) => ({
      ...turn,
      segments: turn.segments.map((s) => {
        if (s.type !== "tool" || s.step.id !== payload.tool_call_id) return s;
        return { ...s, step: { ...s.step, result: payload.content ?? "", status: "done" as const } };
      }),
    }));
  };

  // Ensure "calling" state is visible for at least 200ms before showing result
  onUpdate((prev) => {
    const turn = prev.find((e) => e.id === turnId && e.role === "assistant") as AssistantTurn | undefined;
    if (turn) {
      const toolSeg = turn.segments.find(
        (s) => s.type === "tool" && s.step.id === payload.tool_call_id,
      ) as ToolSegment | undefined;
      if (toolSeg) {
        const elapsed = Date.now() - toolSeg.step.timestamp;
        if (elapsed < 200) {
          setTimeout(updateResult, 200 - elapsed);
          return prev;
        }
      }
    }
    return prev.map((e) => {
      if (e.id !== turnId || e.role !== "assistant") return e;
      const t = e as AssistantTurn;
      return {
        ...t,
        segments: t.segments.map((s) => {
          if (s.type !== "tool" || s.step.id !== payload.tool_call_id) return s;
          return { ...s, step: { ...s.step, result: payload.content ?? "", status: "done" as const } };
        }),
      };
    });
  });
}

function handleErrorEvent(event: StreamEvent, turnId: string, onUpdate: UpdateEntries) {
  const text = typeof event.data === "string" ? event.data : JSON.stringify(event.data ?? "Unknown error");
  updateTurnSegments(onUpdate, turnId, (turn) => ({
    ...turn,
    segments: [...turn.segments, { type: "text", content: `\n\nError: ${text}` }],
  }));
}

function handleCancelledEvent(
  event: StreamEvent,
  turnId: string,
  onUpdate: UpdateEntries,
  setIsStreaming: (v: boolean) => void,
) {
  setIsStreaming(false);
  const cancelledToolCallIds = (event.data as any)?.cancelled_tool_call_ids || [];
  updateTurnSegments(onUpdate, turnId, (turn) => ({
    ...turn,
    segments: turn.segments.map((seg) => {
      if (seg.type === "tool" && cancelledToolCallIds.includes(seg.step.id)) {
        return { ...seg, step: { ...seg.step, status: "cancelled" as const, result: "任务被用户取消" } };
      }
      return seg;
    }),
  }));
}

function handleSubagentEvent(event: StreamEvent, turnId: string, onUpdate: UpdateEntries) {
  const data = event.data as any;
  const parentToolCallId = data?.parent_tool_call_id;
  if (!parentToolCallId) return;

  updateTurnSegments(onUpdate, turnId, (turn) => ({
    ...turn,
    segments: turn.segments.map((s) => {
      if (s.type !== "tool" || s.step.id !== parentToolCallId) return s;

      const step = { ...s.step };
      if (!step.subagent_stream) {
        step.subagent_stream = {
          task_id: "", thread_id: "", text: "", tool_calls: [], status: "running",
        };
      }

      const stream = { ...step.subagent_stream };
      if (event.type === "subagent_task_start") {
        stream.task_id = data.task_id || "";
        stream.thread_id = data.thread_id || "";
        stream.status = "running";
      } else if (event.type === "subagent_task_text") {
        stream.text += data.content || "";
      } else if (event.type === "subagent_task_tool_call") {
        stream.tool_calls = [...stream.tool_calls, {
          id: data.tool_call_id || "", name: data.name || "", args: data.args || {},
        }];
      } else if (event.type === "subagent_task_done") {
        stream.status = "completed";
      } else if (event.type === "subagent_task_error") {
        stream.status = "error";
        stream.error = data.error || "Unknown error";
      }

      return { ...s, step: { ...step, subagent_stream: stream } };
    }),
  }));
}
