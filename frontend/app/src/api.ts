export type StreamEventType = "text" | "tool_call" | "tool_result" | "status" | "done" | "error" | "cancelled" | "task_start" | "task_text" | "task_tool_call" | "task_tool_result" | "task_done" | "task_error" | "subagent_task_start" | "subagent_task_text" | "subagent_task_tool_call" | "subagent_task_tool_result" | "subagent_task_done" | "subagent_task_error";

export interface StreamEvent {
  type: StreamEventType;
  data?: unknown;
}

// Task agent streaming event data types
export interface TaskStartData {
  task_id: string;
  subagent_type: string;
  description: string;
}

export interface TaskTextData {
  task_id: string;
  content: string;
}

export interface TaskToolCallData {
  task_id: string;
  id: string;
  name: string;
  args: unknown;
}

export interface TaskToolResultData {
  task_id: string;
  tool_call_id: string;
  name: string;
  content: string;
}

export interface TaskDoneData {
  task_id: string;
  thread_id?: string;
  status: string;
}

export interface SubagentTaskStartData extends TaskStartData {
  parent_tool_call_id: string;
}

export interface SubagentTaskTextData extends TaskTextData {
  parent_tool_call_id: string;
}

export interface SubagentTaskToolCallData extends TaskToolCallData {
  parent_tool_call_id: string;
}

export interface SubagentTaskToolResultData extends TaskToolResultData {
  parent_tool_call_id: string;
}

export interface SubagentTaskDoneData extends TaskDoneData {
  parent_tool_call_id: string;
}

export interface SubagentTaskErrorData extends TaskErrorData {
  parent_tool_call_id: string;
}

export interface TaskErrorData {
  task_id: string;
  error: string;
}

export type QueueMode = "steer" | "followup" | "collect" | "steer_backlog" | "interrupt";

export interface ThreadSummary {
  thread_id: string;
  sandbox?: string;
  messages?: BackendMessage[];
  sandbox_info?: SandboxInfo;
  preview?: string;
  updated_at?: string;
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
  lease_id?: string | null;
  instance_id?: string | null;
  chat_session_id?: string | null;
  source?: string;
}

export interface SandboxInfo {
  type: string;
  status: string | null;
  session_id: string | null;
  terminal_id?: string | null;
}

export interface BackendMessage {
  type: string;
  content: unknown;
  tool_calls?: unknown[];
  tool_call_id?: string | null;
}

// --- Legacy types (kept for compatibility during migration) ---

export type ChatRole = "user" | "assistant" | "tool_call" | "tool_result";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  name?: string;
  args?: unknown;
  toolCallId?: string | null;
  timestamp?: number;
}

// --- New grouped message types ---

export interface ToolStep {
  id: string;
  name: string;
  args: unknown;
  result?: string;
  status: "calling" | "done" | "error" | "cancelled";
  timestamp: number;
  subagent_stream?: {
    task_id: string;
    thread_id: string;
    text: string;
    tool_calls: Array<{ id: string; name: string; args: unknown }>;
    status: "running" | "completed" | "error";
    error?: string;
  };
}

export interface TextSegment {
  type: "text";
  content: string;
}

export interface ToolSegment {
  type: "tool";
  step: ToolStep;
}

export type TurnSegment = TextSegment | ToolSegment;

export interface AssistantTurn {
  id: string;
  role: "assistant";
  segments: TurnSegment[];
  timestamp: number;
}

export interface UserMessage {
  id: string;
  role: "user";
  content: string;
  timestamp: number;
}

export type ChatEntry = UserMessage | AssistantTurn;

export interface StreamStatus {
  state: { state: string; flags: Record<string, boolean> };
  tokens: { total_tokens: number; input_tokens: number; output_tokens: number; cost: number };
  context: { message_count: number; estimated_tokens: number; usage_percent: number; near_limit: boolean };
  current_tool?: string;
}

export interface ChatSettings {
  turnGrouping: "merged" | "separate";
}

export const DEFAULT_CHAT_SETTINGS: ChatSettings = { turnGrouping: "merged" };

// --- Existing infra types ---

export interface SessionStatus {
  thread_id: string;
  session_id: string;
  terminal_id: string;
  status: string;
  started_at: string;
  last_active_at: string;
  expires_at: string;
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

export interface WorkspaceEntry {
  name: string;
  is_dir: boolean;
  size: number;
  children_count?: number | null;
}

export interface WorkspaceListResult {
  thread_id: string;
  path: string;
  entries: WorkspaceEntry[];
}

export interface WorkspaceFileResult {
  thread_id: string;
  path: string;
  content: string;
  size: number;
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

function toThreads(payload: unknown): ThreadSummary[] {
  if (payload && typeof payload === "object" && Array.isArray((payload as { threads?: unknown }).threads)) {
    return (payload as { threads: ThreadSummary[] }).threads;
  }
  if (Array.isArray(payload)) {
    return payload as ThreadSummary[];
  }
  throw new Error("Unexpected /api/threads response shape");
}

// --- New: mapBackendEntries for grouped ChatEntry[] ---

function extractTextContent(raw: unknown): string {
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) {
    return raw
      .map((block) => {
        if (typeof block === "string") return block;
        if (block && typeof block === "object" && (block as { type?: string }).type === "text") {
          return (block as { text?: string }).text ?? "";
        }
        return "";
      })
      .join("");
  }
  return String(raw ?? "");
}

export function mapBackendEntries(payload: unknown): ChatEntry[] {
  if (!Array.isArray(payload)) return [];
  const entries: ChatEntry[] = [];
  const now = Date.now();
  let currentTurn: AssistantTurn | null = null;

  for (let i = 0; i < payload.length; i += 1) {
    const msg = payload[i] as BackendMessage | undefined;
    if (!msg || typeof msg !== "object") continue;

    if (msg.type === "HumanMessage") {
      currentTurn = null;
      entries.push({
        id: `hist-user-${i}`,
        role: "user",
        content: extractTextContent(msg.content),
        timestamp: now,
      });
      continue;
    }

    if (msg.type === "AIMessage") {
      const textContent = extractTextContent(msg.content);
      const toolCalls = Array.isArray(msg.tool_calls) ? msg.tool_calls : [];

      if (toolCalls.length > 0) {
        // AIMessage with tool_calls
        const newSegments: TurnSegment[] = [];
        if (textContent) {
          newSegments.push({ type: "text", content: textContent });
        }
        for (let j = 0; j < toolCalls.length; j++) {
          const call = toolCalls[j] as { id?: string; name?: string; args?: unknown };
          newSegments.push({
            type: "tool",
            step: {
              id: call.id ?? `hist-tc-${i}-${j}`,
              name: call.name ?? "unknown",
              args: call.args ?? {},
              status: "done",
              timestamp: now,
            },
          });
        }
        if (currentTurn) {
          // Append to existing turn (multi-step agent loop)
          currentTurn.segments.push(...newSegments);
        } else {
          const turn: AssistantTurn = {
            id: `hist-turn-${i}`,
            role: "assistant",
            segments: newSegments,
            timestamp: now,
          };
          currentTurn = turn;
          entries.push(turn);
        }
      } else if (currentTurn) {
        // AIMessage without tool_calls after a tool turn → append text segment
        if (textContent) {
          currentTurn.segments.push({ type: "text", content: textContent });
        }
      } else {
        // Standalone AIMessage
        const turn: AssistantTurn = {
          id: `hist-turn-${i}`,
          role: "assistant",
          segments: textContent ? [{ type: "text", content: textContent }] : [],
          timestamp: now,
        };
        currentTurn = turn;
        entries.push(turn);
      }
      continue;
    }

    if (msg.type === "ToolMessage") {
      // Find matching ToolStep in current turn's segments
      if (currentTurn) {
        const toolCallId = msg.tool_call_id;
        const seg = currentTurn.segments.find(
          (s): s is ToolSegment => s.type === "tool" && s.step.id === toolCallId,
        );
        if (seg) {
          seg.step.result = extractTextContent(msg.content);
          seg.step.status = "done";
        }
      }
    }
  }

  return entries;
}

// Legacy — kept for reference, use mapBackendEntries instead
export function mapBackendMessages(payload: unknown): ChatMessage[] {
  if (!Array.isArray(payload)) return [];
  const out: ChatMessage[] = [];
  const now = Date.now();
  for (let i = 0; i < payload.length; i += 1) {
    const msg = payload[i] as BackendMessage | undefined;
    if (!msg || typeof msg !== "object") continue;
    const rawContent = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content ?? "", null, 2);
    if (msg.type === "HumanMessage") {
      out.push({ id: `hist-user-${i}`, role: "user", content: rawContent, timestamp: now });
      continue;
    }
    if (msg.type === "AIMessage") {
      out.push({ id: `hist-ai-${i}`, role: "assistant", content: rawContent, timestamp: now });
      continue;
    }
    if (msg.type === "ToolMessage") {
      out.push({ id: `hist-tool-${i}`, role: "tool_result", content: rawContent, toolCallId: msg.tool_call_id ?? null, timestamp: now });
    }
  }
  return out;
}

// --- API functions ---

export async function listThreads(): Promise<ThreadSummary[]> {
  const payload = await request<unknown>("/api/threads");
  return toThreads(payload);
}

export async function createThread(sandbox: string, cwd?: string): Promise<ThreadSummary> {
  const body: Record<string, string> = { sandbox };
  if (cwd) body.cwd = cwd;
  return request<ThreadSummary>("/api/threads", { method: "POST", body: JSON.stringify(body) });
}

export async function deleteThread(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
}

export async function getThread(threadId: string): Promise<{ thread_id: string; messages: BackendMessage[]; sandbox: SandboxInfo }> {
  return request(`/api/threads/${encodeURIComponent(threadId)}`);
}

export async function listSandboxTypes(): Promise<SandboxType[]> {
  const payload = await request<{ types: SandboxType[] }>("/api/sandbox/types");
  return payload.types;
}

export async function pickFolder(): Promise<string | null> {
  try {
    const payload = await request<{ path: string }>("/api/sandbox/pick-folder");
    return payload.path;
  } catch (err) {
    // User cancelled or error occurred
    console.log("Folder selection cancelled or failed:", err);
    return null;
  }
}

export async function listSandboxSessions(): Promise<SandboxSession[]> {
  const payload = await request<{ sessions: SandboxSession[] }>("/api/sandbox/sessions");
  const toTs = (value?: string): number => {
    if (!value) return 0;
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
  };
  return [...payload.sessions].sort((a, b) => {
    const createdDiff = toTs(b.created_at) - toTs(a.created_at);
    if (createdDiff !== 0) return createdDiff;
    const activeDiff = toTs(b.last_active) - toTs(a.last_active);
    if (activeDiff !== 0) return activeDiff;
    const providerDiff = a.provider.localeCompare(b.provider);
    if (providerDiff !== 0) return providerDiff;
    const threadDiff = a.thread_id.localeCompare(b.thread_id);
    if (threadDiff !== 0) return threadDiff;
    return a.session_id.localeCompare(b.session_id);
  });
}

export async function pauseThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox/pause`, { method: "POST" });
}

export async function resumeThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox/resume`, { method: "POST" });
}

export async function destroyThreadSandbox(threadId: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/sandbox`, { method: "DELETE" });
}

export async function pauseSandboxSession(sessionId: string, provider: string): Promise<void> {
  await request(
    `/api/sandbox/sessions/${encodeURIComponent(sessionId)}/pause?provider=${encodeURIComponent(provider)}`,
    { method: "POST" },
  );
}

export async function resumeSandboxSession(sessionId: string, provider: string): Promise<void> {
  await request(
    `/api/sandbox/sessions/${encodeURIComponent(sessionId)}/resume?provider=${encodeURIComponent(provider)}`,
    { method: "POST" },
  );
}

export async function destroySandboxSession(sessionId: string, provider: string): Promise<void> {
  await request(
    `/api/sandbox/sessions/${encodeURIComponent(sessionId)}?provider=${encodeURIComponent(provider)}`,
    { method: "DELETE" },
  );
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

export async function listWorkspace(threadId: string, path?: string): Promise<WorkspaceListResult> {
  const q = path ? `?path=${encodeURIComponent(path)}` : "";
  return request(`/api/threads/${encodeURIComponent(threadId)}/workspace/list${q}`);
}

export async function readWorkspaceFile(threadId: string, path: string): Promise<WorkspaceFileResult> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/workspace/read?path=${encodeURIComponent(path)}`);
}

export async function getThreadRuntime(threadId: string): Promise<StreamStatus> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/runtime`);
}

export async function steerThread(threadId: string, message: string): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/steer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export async function setQueueMode(threadId: string, mode: QueueMode): Promise<void> {
  await request(`/api/threads/${encodeURIComponent(threadId)}/queue-mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
}

export async function getQueueMode(threadId: string): Promise<{ mode: QueueMode }> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/queue-mode`);
}

function normalizeStreamType(raw: string): StreamEventType {
  if (
    raw === "text" ||
    raw === "tool_call" ||
    raw === "tool_result" ||
    raw === "status" ||
    raw === "done" ||
    raw === "error" ||
    raw === "cancelled" ||
    raw === "task_start" ||
    raw === "task_text" ||
    raw === "task_tool_call" ||
    raw === "task_tool_result" ||
    raw === "task_done" ||
    raw === "task_error"
  ) {
    return raw;
  }
  return "text";
}

function tryParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export async function startRun(threadId: string, message: string, onEvent: (event: StreamEvent) => void, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
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
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const decoded = decoder.decode(value, { stream: true });
    buffer += decoded;
    // SSE events are separated by blank lines; handle both \r\n and \n line endings
    const chunks = buffer.split(/\r?\n\r?\n/);
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      let eventType = "text";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      const dataRaw = dataLines.join("\n");
      onEvent({ type: normalizeStreamType(eventType), data: tryParse(dataRaw) });
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

export interface TaskAgentRequest {
  subagent_type: string;
  prompt: string;
  description?: string;
  model?: string;
  max_turns?: number;
}

export async function streamTaskAgent(
  threadId: string,
  request: TaskAgentRequest,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/task-agent/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Task agent stream failed ${response.status}: ${body || response.statusText}`);
  }
  if (!response.body) {
    throw new Error("Task agent response has no body stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const decoded = decoder.decode(value, { stream: true });
    buffer += decoded;
    const chunks = buffer.split(/\r?\n\r?\n/);
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      let eventType = "text";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      const dataRaw = dataLines.join("\n");
      onEvent({ type: normalizeStreamType(eventType), data: tryParse(dataRaw) });
    }
  }
}

// --- Data Platform (Operator Console) ---

export interface DpRun {
  run_id: string;
  thread_id: string;
  sandbox: string;
  input_message: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

export interface DpRunEvent {
  event_id: number;
  run_id: string;
  thread_id: string;
  event_type: string;
  payload: unknown;
  created_at: string;
}

export interface OperatorSearchHit {
  type: string;
  id: string;
  summary?: string;
  updated_at?: string;
  thread_id?: string;
  run_id?: string;
  provider?: string;
  terminal_id?: string;
  instance_id?: string;
}

export interface OperatorSandboxSession {
  thread_id: string;
  chat_session_id: string;
  terminal_id: string;
  lease_id: string;
  chat_status: string;
  started_at: string;
  last_active_at: string;
  provider_name: string;
  observed_state: string;
  last_error: string | null;
  cwd: string;
  last_command:
    | {
        command_id: string;
        status: string;
        exit_code: number | null;
      }
    | null;
}

export async function operatorSearch(opts: {
  q: string;
  limit?: number;
}): Promise<{ q: string; items: OperatorSearchHit[]; count: number }> {
  const q = opts.q.trim();
  if (!q) throw new Error("operatorSearch: q is required");
  const limit = opts.limit ?? 50;
  return request(`/api/operator/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(String(limit))}`);
}

export async function operatorSandboxes(opts?: {
  limit?: number;
}): Promise<{ items: OperatorSandboxSession[]; count: number }> {
  const limit = opts?.limit ?? 50;
  return request(`/api/operator/sandboxes?limit=${encodeURIComponent(String(limit))}`);
}

export async function operatorThreadDiagnostics(opts: { thread_id: string }): Promise<unknown> {
  const threadId = opts.thread_id.trim();
  if (!threadId) throw new Error("operatorThreadDiagnostics: thread_id is required");
  return request(`/api/operator/threads/${encodeURIComponent(threadId)}/diagnostics`);
}

export async function operatorDashboardsOverview(opts?: {
  window_hours?: number;
  stuck_after_sec?: number;
}): Promise<unknown> {
  const windowHours = opts?.window_hours ?? 24;
  const stuckAfterSec = opts?.stuck_after_sec ?? 600;
  return request(
    `/api/operator/dashboards/overview?window_hours=${encodeURIComponent(String(windowHours))}&stuck_after_sec=${encodeURIComponent(String(stuckAfterSec))}`,
  );
}

export async function listDpThreadRuns(opts: {
  thread_id: string;
  limit?: number;
  offset?: number;
}): Promise<{ thread_id: string; items: DpRun[] }> {
  const threadId = opts.thread_id.trim();
  if (!threadId) throw new Error("listDpThreadRuns: thread_id is required");
  const limit = opts.limit ?? 50;
  const offset = opts.offset ?? 0;
  return request(
    `/api/threads/${encodeURIComponent(threadId)}/runs?limit=${encodeURIComponent(String(limit))}&offset=${encodeURIComponent(String(offset))}`,
  );
}

export async function getDpRunEvents(opts: {
  run_id: string;
  after_event_id?: number;
  limit?: number;
}): Promise<{ run_id: string; items: DpRunEvent[]; next_after_event_id: number }> {
  const runId = opts.run_id.trim();
  if (!runId) throw new Error("getDpRunEvents: run_id is required");
  const after = opts.after_event_id ?? 0;
  const limit = opts.limit ?? 200;
  return request(
    `/api/runs/${encodeURIComponent(runId)}/events?after_event_id=${encodeURIComponent(String(after))}&limit=${encodeURIComponent(String(limit))}`,
  );
}
