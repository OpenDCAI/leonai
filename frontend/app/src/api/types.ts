export type StreamEventType = "text" | "tool_call" | "tool_result" | "status" | "done" | "error" | "cancelled" | "task_start" | "task_text" | "task_tool_call" | "task_tool_result" | "task_done" | "task_error" | "subagent_task_start" | "subagent_task_text" | "subagent_task_tool_call" | "subagent_task_tool_result" | "subagent_task_done" | "subagent_task_error";

export interface StreamEvent {
  type: StreamEventType;
  data?: unknown;
}

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

export interface TaskErrorData {
  task_id: string;
  error: string;
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

export type QueueMode = "steer" | "followup" | "collect" | "steer_backlog" | "interrupt";

export interface ThreadSummary {
  thread_id: string;
  sandbox?: string;
  messages?: BackendMessage[];
  sandbox_info?: SandboxInfo;
  preview?: string;
  updated_at?: string;
  running?: boolean;
}

export interface SandboxType {
  name: string;
  provider?: string;
  available: boolean;
  reason?: string;
  capability?: {
    can_pause: boolean;
    can_resume: boolean;
    can_destroy: boolean;
    supports_webhook: boolean;
    supports_status_probe: boolean;
    eager_instance_binding: boolean;
    inspect_visible: boolean;
    runtime_kind: string;
    mount: {
      supports_mount: boolean;
      supports_copy: boolean;
      supports_read_only: boolean;
    };
  };
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
  id?: string;
  type: string;
  content: unknown;
  tool_calls?: unknown[];
  tool_call_id?: string | null;
}

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
  messageIds?: string[];
  role: "assistant";
  segments: TurnSegment[];
  timestamp: number;
  streaming?: boolean;
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
  last_seq?: number;
}

export interface ChatSettings {
  turnGrouping: "merged" | "separate";
}

export const DEFAULT_CHAT_SETTINGS: ChatSettings = { turnGrouping: "merged" };

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

export interface TaskAgentRequest {
  subagent_type: string;
  prompt: string;
  description?: string;
  model?: string;
  max_turns?: number;
}
