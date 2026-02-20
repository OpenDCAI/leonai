import type { StreamEvent, StreamEventType } from "./types";

const VALID_EVENT_TYPES = new Set<StreamEventType>([
  "text", "tool_call", "tool_result", "status", "done", "error", "cancelled",
  "task_start", "task_text", "task_tool_call", "task_tool_result", "task_done", "task_error",
  "subagent_task_start", "subagent_task_text", "subagent_task_tool_call",
  "subagent_task_tool_result", "subagent_task_done", "subagent_task_error",
]);

function normalizeStreamType(raw: string): StreamEventType {
  return VALID_EVENT_TYPES.has(raw as StreamEventType) ? (raw as StreamEventType) : "text";
}

function tryParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function extractSeq(data: unknown): number | undefined {
  if (typeof data === "object" && data !== null) {
    const seq = (data as Record<string, unknown>)._seq;
    if (typeof seq === "number") return seq;
  }
  return undefined;
}

function parseSSEChunk(chunk: string): { eventType: string; dataRaw: string } | null {
  if (!chunk.trim()) return null;
  let eventType = "text";
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) eventType = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  return { eventType, dataRaw: dataLines.join("\n") };
}

export function processChunk(
  chunk: string,
  onEvent: (event: StreamEvent) => void,
  seq: number,
): { seq: number; terminal: boolean } {
  const parsed = parseSSEChunk(chunk);
  if (!parsed || (!parsed.dataRaw && parsed.eventType === "text")) return { seq, terminal: false };
  const type = normalizeStreamType(parsed.eventType);
  const data = tryParse(parsed.dataRaw);
  const newSeq = extractSeq(data) ?? seq;
  onEvent({ type, data });
  return { seq: newSeq, terminal: type === "done" || type === "cancelled" };
}
