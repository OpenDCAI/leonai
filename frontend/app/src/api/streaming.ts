import type { StreamEvent, StreamEventType, TaskAgentRequest } from "./types";

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

/** Read an SSE response body, dispatch events, return { lastSeq, finished }. */
async function consumeSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
  startSeq: number,
): Promise<{ lastSeq: number; finished: boolean }> {
  const decoder = new TextDecoder();
  let buffer = "";
  let seq = startSeq;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split(/\r?\n\r?\n/);
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const parsed = parseSSEChunk(chunk);
      if (!parsed || (!parsed.dataRaw && parsed.eventType === "text")) continue;
      const type = normalizeStreamType(parsed.eventType);
      const data = tryParse(parsed.dataRaw);
      if (typeof data === "object" && data !== null && typeof (data as Record<string, unknown>)._seq === "number") {
        seq = (data as Record<string, unknown>)._seq as number;
      }
      onEvent({ type, data });
      if (type === "done" || type === "cancelled") return { lastSeq: seq, finished: true };
    }
  }
  return { lastSeq: seq, finished: false };
}

/** Start an agent run (fire-and-forget). */
export async function postRun(
  threadId: string,
  message: string,
  signal?: AbortSignal,
  options?: { model?: string; enable_trajectory?: boolean },
): Promise<{ run_id: string; thread_id: string }> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...options }),
    signal,
  });
  if (!res.ok) throw new Error(`Run failed ${res.status}: ${await res.text()}`);
  return res.json();
}

/** Subscribe to SSE event stream with built-in reconnection. */
export async function streamEvents(
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let after = 0;
  let attempts = 0;

  while (!signal?.aborted) {
    try {
      const url = `/api/threads/${encodeURIComponent(threadId)}/runs/events?after=${after}`;
      const res = await fetch(url, { signal });
      if (!res.ok) {
        onEvent({ type: "error", data: { error: `SSE connect failed: ${res.status}` } });
        break;
      }
      if (!res.body) break;
      attempts = 0;

      const { lastSeq, finished } = await consumeSSEStream(res.body.getReader(), onEvent, after);
      after = lastSeq;
      if (finished) return;
    } catch {
      if (signal?.aborted) return;
      const delay = Math.min(1000 * 2 ** attempts, 30000);
      attempts++;
      await new Promise((r) => setTimeout(r, delay));
    }
  }
}

export async function cancelRun(threadId: string): Promise<void> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/runs/cancel`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to cancel run: ${response.statusText}`);
  }
}

/** Start a task agent and subscribe to its event stream. */
export async function runTaskAgent(
  threadId: string,
  taskRequest: TaskAgentRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/task-agent/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(taskRequest),
    signal,
  });
  if (!res.ok) throw new Error(`Task agent failed ${res.status}: ${await res.text()}`);
  await streamEvents(threadId, onEvent, signal);
}
