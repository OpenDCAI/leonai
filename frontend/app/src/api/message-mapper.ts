import type { AssistantTurn, BackendMessage, ChatEntry, ConversationMessage, NoticeMessage, NotificationType, ToolSegment, TurnSegment } from "./types";

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

/** Strip <system-reminder>...</system-reminder> blocks from text content. */
function stripSystemReminders(text: string): string {
  return text.replace(/<system-reminder>[\s\S]*?<\/system-reminder>/g, "").trim();
}

/** Unescape HTML entities (&#x27; &#39; &amp; &lt; &gt; &quot;). */
function unescapeHtml(s: string): string {
  return s.replace(/&#x27;/g, "'").replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
}

/** Extract plain text content from <incoming-message> XML wrapper. */
function extractIncomingMessageContent(raw: string): string {
  const match = raw.match(/<incoming-message[^>]*>([\s\S]*?)<\/incoming-message>/);
  return match ? match[1].trim() : raw;
}


function buildToolSegments(toolCalls: unknown[], msgIndex: number, now: number): TurnSegment[] {
  // @@@logbook-reply-flat - skip logbook_reply (absorbed into flat ConversationMessage)
  return toolCalls
    .filter((raw) => (raw as { name?: string }).name !== "logbook_reply")
    .map((raw, j) => {
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
  currentRunId: string | null;
  now: number;
}

function handleHuman(msg: BackendMessage, i: number, state: MapState): void {
  // System-injected messages (steer reminders, task notifications) → notice
  if (msg.metadata?.source === "system") {
    const content = extractTextContent(msg.content);

    // @@@unified-conversation - detect <incoming-message> XML even in steer path
    // (agent-to-agent via queue loses conversation_meta but content is still XML)
    const incomingMatch = content.match(/<incoming-message\s+sender="([^"]*)"(?:\s+conversation="([^"]*)")?>([\s\S]*?)<\/incoming-message>/);
    if (incomingMatch) {
      state.currentTurn = null;
      state.currentRunId = null;
      state.entries.push({
        id: msg.id ?? `hist-conv-${i}`,
        role: "conversation",
        direction: "incoming",
        senderName: unescapeHtml(incomingMatch[1]),
        content: unescapeHtml(incomingMatch[3].trim()),
        conversationId: incomingMatch[2],
        timestamp: state.now,
      } as ConversationMessage);
      return;
    }

    const msgRunId = (msg.metadata?.run_id as string) || null;
    const ntype = msg.metadata?.notification_type as NotificationType | undefined;

    if (state.currentTurn && msgRunId && msgRunId === state.currentRunId) {
      // Same run_id → fold into current assistant turn as a notice segment
      state.currentTurn.segments.push({ type: "notice", content, notification_type: ntype });
      return;
    }
    if (state.currentTurn && !msgRunId) {
      // No run_id (legacy) → fold into current turn if active
      state.currentTurn.segments.push({ type: "notice", content, notification_type: ntype });
      return;
    }
    // Different run_id or no current turn → standalone notice entry (Turn boundary)
    state.currentTurn = null;
    state.currentRunId = null;
    const notice: NoticeMessage = {
      id: msg.id ?? `hist-notice-${i}`,
      role: "notice",
      content,
      notification_type: ntype,
      timestamp: state.now,
    };
    state.entries.push(notice);
    return;
  }

  // @@@conversation-metadata - conversation-delivered messages → top-level ConversationMessage
  if (msg.metadata?.source === "conversation") {
    const raw = extractTextContent(msg.content);
    const content = extractIncomingMessageContent(raw);
    const entry: ConversationMessage = {
      id: msg.id ?? `hist-conv-${i}`,
      role: "conversation",
      direction: "incoming",
      senderName: msg.metadata.sender_name as string,
      senderId: msg.metadata.sender_id as string,
      senderType: msg.metadata.sender_type as string | undefined,
      content,
      conversationId: msg.metadata.conversation_id as string,
      timestamp: state.now,
    };
    // Break current turn — each conversation exchange needs its own AssistantTurn
    state.currentTurn = null;
    state.currentRunId = null;
    state.entries.push(entry);
    return;
  }

  // Normal user message → breaks current turn
  state.currentTurn = null;
  state.currentRunId = null;
  state.entries.push({
    id: msg.id ?? `hist-user-${i}`,
    role: "user",
    content: extractTextContent(msg.content),
    timestamp: state.now,
  });
}

function handleAI(msg: BackendMessage, i: number, state: MapState): void {
  const textContent = stripSystemReminders(extractTextContent(msg.content));
  const toolCalls = Array.isArray(msg.tool_calls) ? msg.tool_calls : [];
  const msgId = msg.id ?? `hist-turn-${i}`;
  const msgRunId = (msg.metadata?.run_id as string) || null;

  // @@@logbook-reply-flat - extract logbook_reply as flat ConversationMessage BEFORE the turn
  const lastIncoming = [...state.entries].reverse().find(
    (e): e is ConversationMessage => e.role === "conversation" && e.direction === "incoming",
  );
  for (const tc of toolCalls) {
    const call = tc as { name?: string; args?: Record<string, unknown> };
    if (call.name === "logbook_reply" && call.args?.content) {
      state.entries.push({
        id: `${msgId}-conv-${call.args.conversation_id || "reply"}`,
        role: "conversation",
        direction: "outgoing",
        senderName: "",
        recipientName: (call.args.to as string) || lastIncoming?.senderName,
        content: call.args.content as string,
        conversationId: call.args.conversation_id as string | undefined,
        timestamp: state.now,
      } as ConversationMessage);
    }
  }

  const segments: TurnSegment[] = [];
  if (textContent) segments.push({ type: "text", content: textContent });
  if (toolCalls.length > 0) segments.push(...buildToolSegments(toolCalls, i, state.now));

  // Group by run_id: same run_id = same Turn
  if (state.currentTurn && msgRunId && msgRunId === state.currentRunId) {
    appendToTurn(state.currentTurn, msgId, segments);
  } else if (state.currentTurn && !msgRunId && !state.currentRunId) {
    // Legacy: no run_id on either → merge consecutive (backward compat)
    appendToTurn(state.currentTurn, msgId, segments);
  } else {
    // New run_id or first message → new Turn
    state.currentTurn = createTurn(msgId, segments, state.now);
    state.currentRunId = msgRunId;
    state.entries.push(state.currentTurn);
  }

}

function handleTool(msg: BackendMessage, _i: number, state: MapState): void {
  if (!state.currentTurn) return;
  const seg = state.currentTurn.segments.find(
    (s): s is ToolSegment => s.type === "tool" && s.step.id === msg.tool_call_id,
  );
  // @@@logbook-reply-flat - logbook_reply has no ToolSegment (skipped in buildToolSegments)
  if (!seg) return;

  const contentStr = extractTextContent(msg.content);
  seg.step.result = contentStr;
  seg.step.status = "done";

  // Restore subagent_stream from persisted metadata (history replay path)
  let taskId = msg.metadata?.task_id as string | undefined;
  let threadId = (msg.metadata?.subagent_thread_id as string | undefined)
    || (taskId ? `subagent-${taskId}` : undefined);

  if (!taskId && seg.step.name === "Agent") {
    try {
      const parsed = JSON.parse(contentStr) as Record<string, unknown>;
      if (parsed?.task_id) {
        taskId = parsed.task_id as string;
        threadId = (parsed.thread_id as string | undefined) || `subagent-${taskId}`;
      }
    } catch { /* not JSON, foreground agent text result */ }
  }

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

const MSG_HANDLERS: Record<string, (msg: BackendMessage, i: number, state: MapState) => void> = {
  HumanMessage: handleHuman,
  AIMessage: handleAI,
  ToolMessage: handleTool,
};

export function mapBackendEntries(payload: unknown): ChatEntry[] {
  if (!Array.isArray(payload)) return [];
  const state: MapState = { entries: [], currentTurn: null, currentRunId: null, now: Date.now() };

  for (let i = 0; i < payload.length; i += 1) {
    const msg = payload[i] as BackendMessage | undefined;
    if (!msg || typeof msg !== "object") continue;
    MSG_HANDLERS[msg.type]?.(msg, i, state);
  }

  return state.entries;
}
