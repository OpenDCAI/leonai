import type { StreamEvent, TaskAgentRequest } from "./types";
import { processChunk } from "./sse-processor";

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
      const result = processChunk(chunk, onEvent, seq);
      seq = result.seq;
      if (result.terminal) return { lastSeq: seq, finished: true };
    }
  }
  return { lastSeq: seq, finished: false };
}

async function postJSON<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(`POST ${url} failed ${res.status}: ${await res.text()}`);
  return res.json();
}

/** Start an agent run (fire-and-forget). */
export async function postRun(
  threadId: string,
  message: string,
  signal?: AbortSignal,
  options?: { model?: string; enable_trajectory?: boolean },
): Promise<{ run_id: string; thread_id: string }> {
  return postJSON(`/api/threads/${encodeURIComponent(threadId)}/runs`, { message, ...options }, signal);
}

async function connectOnce(
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  after: number,
  signal?: AbortSignal,
): Promise<{ after: number; done: boolean }> {
  const url = `/api/threads/${encodeURIComponent(threadId)}/runs/events?after=${after}`;
  const res = await fetch(url, { signal });
  if (!res.ok) {
    onEvent({ type: "error", data: { error: `SSE connect failed: ${res.status}` } });
    return { after, done: true };
  }
  if (!res.body) return { after, done: true };
  const { lastSeq, finished } = await consumeSSEStream(res.body.getReader(), onEvent, after);
  return { after: lastSeq, done: finished };
}

/** Subscribe to SSE event stream with built-in reconnection. */
export async function streamEvents(
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
  startAfter = 0,
): Promise<void> {
  let after = startAfter;
  let attempts = 0;

  while (!signal?.aborted) {
    try {
      const result = await connectOnce(threadId, onEvent, after, signal);
      after = result.after;
      attempts = 0;
      if (result.done) return;
    } catch {
      if (signal?.aborted) return;
      await new Promise((r) => setTimeout(r, Math.min(1000 * 2 ** attempts, 30000)));
      attempts++;
    }
  }
}

export async function cancelRun(threadId: string): Promise<void> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/runs/cancel`, { method: "POST" });
  if (!res.ok) throw new Error(`Cancel failed: ${res.statusText}`);
}

/** Start a task agent and subscribe to its event stream. */
export async function runTaskAgent(
  threadId: string,
  taskRequest: TaskAgentRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await postJSON(`/api/threads/${encodeURIComponent(threadId)}/task-agent/runs`, taskRequest, signal);
  await streamEvents(threadId, onEvent, signal);
}
