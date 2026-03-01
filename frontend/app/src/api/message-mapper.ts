import type { AssistantTurn, BackendMessage, ChatEntry, NoticeMessage, ToolSegment, TurnSegment } from "./types";

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

function buildToolSegments(toolCalls: unknown[], msgIndex: number, now: number): TurnSegment[] {
  return toolCalls.map((raw, j) => {
    const call = raw as { id?: string; name?: string; args?: unknown };
    return {
      type: "tool" as const,
      step: {
        id: call.id ?? `hist-tc-${msgIndex}-${j}`,
        name: call.name ?? "unknown",
        args: call.args ?? {},
        status: "calling" as const,
        timestamp: now,
      },
    };
  });
}

function createTurn(msgId: string, segments: TurnSegment[], now: number): AssistantTurn {
  return { id: msgId, messageIds: [msgId], role: "assistant", segments, timestamp: now };
}

function appendToTurn(turn: AssistantTurn, msgId: string, segments: TurnSegment[]): void {
  turn.segments.push(...segments);
  turn.messageIds?.push(msgId);
}

interface MapState {
  entries: ChatEntry[];
  currentTurn: AssistantTurn | null;
  now: number;
}

function handleHuman(msg: BackendMessage, i: number, state: MapState): void {
  // System-injected messages (steer reminders, task notifications) → notice
  if (msg.metadata?.source === "system") {
    const content = extractTextContent(msg.content);
    if (state.currentTurn) {
      // Fold into current assistant turn as a notice segment
      state.currentTurn.segments.push({ type: "notice", content });
      return;
    }
    // No current turn → standalone notice entry (fallback)
    const notice: NoticeMessage = {
      id: msg.id ?? `hist-notice-${i}`,
      role: "notice",
      content,
      timestamp: state.now,
    };
    state.entries.push(notice);
    return;
  }

  // Normal user message → breaks current turn
  state.currentTurn = null;
  state.entries.push({
    id: msg.id ?? `hist-user-${i}`,
    role: "user",
    content: extractTextContent(msg.content),
    timestamp: state.now,
  });
}

function handleAI(msg: BackendMessage, i: number, state: MapState): void {
  const textContent = extractTextContent(msg.content);
  const toolCalls = Array.isArray(msg.tool_calls) ? msg.tool_calls : [];
  const msgId = msg.id ?? `hist-turn-${i}`;

  const segments: TurnSegment[] = [];
  if (textContent) segments.push({ type: "text", content: textContent });
  if (toolCalls.length > 0) segments.push(...buildToolSegments(toolCalls, i, state.now));

  if (state.currentTurn) {
    appendToTurn(state.currentTurn, msgId, segments);
  } else {
    state.currentTurn = createTurn(msgId, segments, state.now);
    state.entries.push(state.currentTurn);
  }
}

function handleTool(msg: BackendMessage, _i: number, state: MapState): void {
  if (!state.currentTurn) return;
  const seg = state.currentTurn.segments.find(
    (s): s is ToolSegment => s.type === "tool" && s.step.id === msg.tool_call_id,
  );
  if (seg) {
    seg.step.result = extractTextContent(msg.content);
    seg.step.status = "done";

    // Restore subagent_stream from persisted metadata (history replay path)
    const taskId = msg.metadata?.task_id as string | undefined;
    const threadId = (msg.metadata?.subagent_thread_id as string | undefined)
      || (taskId ? `subagent_${taskId}` : undefined);
    if (threadId && !seg.step.subagent_stream) {
      seg.step.subagent_stream = {
        task_id: taskId || "",
        thread_id: threadId,
        description: (msg.metadata?.description as string) || undefined,
        text: "",
        tool_calls: [],
        status: "completed",
      };
    }
  }
}

const MSG_HANDLERS: Record<string, (msg: BackendMessage, i: number, state: MapState) => void> = {
  HumanMessage: handleHuman,
  AIMessage: handleAI,
  ToolMessage: handleTool,
};

export function mapBackendEntries(payload: unknown): ChatEntry[] {
  if (!Array.isArray(payload)) return [];
  const state: MapState = { entries: [], currentTurn: null, now: Date.now() };

  for (let i = 0; i < payload.length; i += 1) {
    const msg = payload[i] as BackendMessage | undefined;
    if (!msg || typeof msg !== "object") continue;
    MSG_HANDLERS[msg.type]?.(msg, i, state);
  }

  return state.entries;
}
