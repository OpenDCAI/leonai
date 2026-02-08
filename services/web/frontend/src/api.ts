import { createParser, type EventSourceMessage } from "eventsource-parser";

export type StreamEventType = "text" | "tool_call" | "tool_result" | "done" | "error";

export interface StreamEvent {
  type: StreamEventType;
  data?: unknown;
}

export interface ThreadSummary {
  thread_id: string;
  messages?: ChatMessage[];
  title?: string;
  sandbox?: string;
}

export interface SandboxType {
  name: string;
  available: boolean;
  reason?: string;
}

export interface SandboxSession {
  session_id: string;
  thread_id: string;
  provider: string;
  status: string;
  created_at?: string;
  last_active?: string;
}

export interface SandboxInfo {
  type: string;
  status: string | null;
  session_id: string | null;
}

export interface SandboxMetrics {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  network_rx_kbps: number;
  network_tx_kbps: number;
}

export type ChatMessageRole = "user" | "assistant" | "tool_call" | "tool_result";

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  name?: string;
  args?: unknown;
  toolCallId?: string;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function toArrayThreads(payload: unknown): ThreadSummary[] {
  if (Array.isArray(payload)) {
    return payload as ThreadSummary[];
  }

  if (payload && typeof payload === "object" && Array.isArray((payload as { threads?: unknown }).threads)) {
    return (payload as { threads: ThreadSummary[] }).threads;
  }

  throw new Error("Unexpected /api/threads response shape");
}

function normalizeStreamType(rawType: string): StreamEventType {
  if (rawType === "text" || rawType === "tool_call" || rawType === "tool_result" || rawType === "done" || rawType === "error") {
    return rawType;
  }

  if (rawType === "message" || rawType === "token" || rawType === "delta") {
    return "text";
  }

  throw new Error(`Unknown stream event type: ${rawType}`);
}

function safeParseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const payload = await request<unknown>("/api/threads");
  return toArrayThreads(payload);
}

export async function createThread(sandbox: string = "local"): Promise<ThreadSummary> {
  return request<ThreadSummary>("/api/threads", {
    method: "POST",
    body: JSON.stringify({ sandbox }),
  });
}

export async function getThread(id: string): Promise<ThreadSummary> {
  return request<ThreadSummary>(`/api/threads/${encodeURIComponent(id)}`);
}

export async function deleteThread(id: string): Promise<void> {
  await request<void>(`/api/threads/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function steer(threadId: string, message: string): Promise<unknown> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/steer`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function startRun(
  threadId: string,
  message: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Run failed ${response.status}: ${body || response.statusText}`);
  }

  if (!response.body) {
    throw new Error("Run response has no body stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  // @@@sse-parse - Streaming payload schema can vary by backend; parse raw SSE and normalize event names explicitly.
  const parser = createParser({
    onEvent(evt: EventSourceMessage) {
      const type = normalizeStreamType(evt.event || "text");
      const parsed = safeParseJson(evt.data);
      onEvent({ type, data: parsed });
    },
  });

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    parser.feed(decoder.decode(value, { stream: true }));
  }
}

// --- Sandbox API ---

export async function listSandboxTypes(): Promise<SandboxType[]> {
  const res = await request<{ types: SandboxType[] }>("/api/sandbox/types");
  return res.types;
}

export async function listSandboxSessions(): Promise<SandboxSession[]> {
  const res = await request<{ sessions: SandboxSession[] }>("/api/sandbox/sessions");
  return res.sessions;
}

// Thread-level sandbox control (routes through agent's sandbox, keeps cache consistent)
export async function pauseThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox/pause`, { method: "POST" });
}

export async function resumeThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox/resume`, { method: "POST" });
}

export async function destroyThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox`, { method: "DELETE" });
}

export async function getSessionMetrics(sessionId: string): Promise<{ metrics: SandboxMetrics | null; web_url: string | null }> {
  return request(`/api/sandbox/sessions/${encodeURIComponent(sessionId)}/metrics`);
}

// --- New architecture endpoints ---

export interface SessionStatus {
  thread_id: string;
  session_id: string;
  terminal_id: string;
  status: string;
  created_at: string;
  last_active_at: string;
  expires_at: string | null;
}

export interface TerminalStatus {
  thread_id: string;
  terminal_id: string;
  lease_id: string;
  cwd: string;
  env_delta: Record<string, string>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LeaseStatus {
  thread_id: string;
  lease_id: string;
  provider_name: string;
  instance: {
    instance_id: string | null;
    state: string | null;
    started_at: string | null;
  } | null;
  created_at: string;
  updated_at: string;
}

export async function getThreadSession(threadId: string): Promise<SessionStatus> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/session`);
}

export async function getThreadTerminal(threadId: string): Promise<TerminalStatus> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/terminal`);
}

export async function getThreadLease(threadId: string): Promise<LeaseStatus> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/lease`);
}
