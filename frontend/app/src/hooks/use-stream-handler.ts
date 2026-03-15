import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import {
  cancelRun,
  type AssistantTurn,
  type ChatEntry,
  type ConversationMessage,
  type NoticeMessage,
  type NotificationType,
  type StreamStatus,
} from "../api";
import { sendConversationMessage } from "../api/conversations";
import { processStreamEvent } from "./stream-event-handlers";
import { useThreadStream } from "./use-thread-stream";
import { makeId } from "./utils";

interface StreamHandlerDeps {
  threadId: string | null;
  /** If set, send messages through conversation API instead of thread API. */
  conversationId?: string;
  refreshThreads: () => Promise<void>;
  onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void;
  /** True while useThreadData is loading the snapshot — connection waits for this. */
  loading: boolean;
  /**
   * True when navigating from a new-chat creation (postRun already called in NewChatPage).
   * Tells useThreadStream to connect from seq=0 instead of last_seq, so we don't miss
   * events that were emitted between postRun() and ChatPage mount.
   */
  runStarted?: boolean;
}

export interface StreamHandlerState {
  runtimeStatus: StreamStatus | null;
  isRunning: boolean;
}

export interface StreamHandlerActions {
  handleSendMessage: (message: string) => Promise<void>;
  handleStopStreaming: () => Promise<void>;
}

/**
 * Reuse the last entry if it's an assistant turn (mark it streaming);
 * otherwise create a new assistant turn.
 */
function applyReconnectTurn(
  prev: ChatEntry[],
  fallbackId: string,
): { entries: ChatEntry[]; turnId: string } {
  const last = prev[prev.length - 1];
  // Only reuse if the last turn is currently streaming (true reconnect mid-run).
  // A completed turn (streaming: false) must NOT be reused — that would merge a new
  // notification-triggered run into the previous turn.
  if (last?.role === "assistant" && (last as AssistantTurn).streaming) {
    return {
      entries: prev.map((e) =>
        e.id === last.id && e.role === "assistant"
          ? { ...e, streaming: true } as AssistantTurn
          : e,
      ),
      turnId: last.id,
    };
  }
  const newTurn: AssistantTurn = {
    id: fallbackId,
    role: "assistant",
    segments: [],
    timestamp: Date.now(),
    streaming: true,
  };
  return { entries: [...prev, newTurn], turnId: fallbackId };
}

export function useStreamHandler(
  deps: StreamHandlerDeps,
): StreamHandlerState & StreamHandlerActions {
  const { threadId, conversationId, refreshThreads, onUpdate, loading, runStarted } = deps;

  // Local state for immediate UI feedback when user sends a message
  // (covers the window between flushSync and useThreadStream.isRunning becoming true)
  const [sendPending, setSendPending] = useState(false);

  const { isRunning: streamIsRunning, runtimeStatus, subscribe } =
    useThreadStream(threadId, { loading, refreshThreads, runStarted });

  const isRunning = streamIsRunning || sendPending;

  // Clear sendPending once the stream picks up
  useEffect(() => {
    if (streamIsRunning) setSendPending(false);
  }, [streamIsRunning]);

  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;
  const refreshRef = useRef(refreshThreads);
  refreshRef.current = refreshThreads;

  /**
   * Active turn ID. Set by handleSendMessage (temp then server ID).
   * For auto-reconnect, set lazily on first non-status event.
   *
   * CRITICAL: must be set SYNCHRONOUSLY, never inside a deferred React state
   * updater. When SSE replays buffered events, run_start + text arrive in the
   * same reader.read() batch. React batches the updater, so turnIdRef would
   * still be "" when the next event is processed → text lost, streaming stuck.
   * flushSync forces the updater to execute immediately.
   */
  const turnIdRef = useRef<string>("");
  // @@@optimistic-dedup - track pending optimistic entry for notice→replace
  const pendingConvRef = useRef<string | null>(null);
  /**
   * True once the server message_id has been bound to the turn entry.
   * Reset at the start of each new connection.
   */
  const hasBoundRef = useRef(false);

  // Subscribe to stream events → drive UI state
  useEffect(() => {
    console.log("[STREAM-DIAG] subscriber registered");

    /** Create or reuse an assistant turn for reconnect. Uses flushSync so
     *  turnIdRef is set BEFORE the next SSE event in the same batch. */
    function ensureReconnectTurn() {
      const fallbackId = makeId("reconnect-turn");
      flushSync(() => {
        onUpdateRef.current((prev) => {
          const { entries, turnId } = applyReconnectTurn(prev, fallbackId);
          turnIdRef.current = turnId;
          return entries;
        });
      });
    }

    return subscribe((event) => {
      console.log(`[STREAM-DIAG] event=${event.type}, turnId=${turnIdRef.current}, hasBound=${hasBoundRef.current}`);

      // notice: standalone entry inserted between turns
      if (event.type === "notice") {
        const d = (event.data ?? {}) as {
          content?: string;
          notification_type?: string;
          conversation_meta?: { sender_name: string; sender_id: string; conversation_id: string };
        };

        // @@@conversation-metadata - conversation message → top-level ConversationMessage
        if (d.conversation_meta) {
          const meta = d.conversation_meta;
          const raw = d.content ?? "";
          const match = raw.match(/<incoming-message[^>]*>([\s\S]*?)<\/incoming-message>/);
          const content = match ? match[1].trim() : raw;
          const entry: ConversationMessage = {
            id: makeId("conv"),
            role: "conversation",
            direction: "incoming",
            senderName: meta.sender_name,
            senderId: meta.sender_id,
            senderType: meta.sender_type,
            content,
            conversationId: meta.conversation_id,
            timestamp: Date.now(),
          };

          // @@@optimistic-dedup - if we have a pending optimistic entry, replace it
          const optimisticId = pendingConvRef.current;
          if (optimisticId) {
            pendingConvRef.current = null;
            onUpdateRef.current((prev) => prev.map(e =>
              e.id === optimisticId ? entry : e
            ));
            return;
          }

          // No pending → agent-to-agent message → insert as new entry
          onUpdateRef.current((prev) => [...prev, entry]);
          return;
        }

        // @@@unified-conversation - detect <incoming-message> XML even in non-meta notices
        // (agent-to-agent via steer queue loses conversation_meta)
        const rawContent = d.content ?? "";
        const xmlMatch = rawContent.match(/<incoming-message\s+sender="([^"]*)"(?:\s+conversation="([^"]*)")?>([\s\S]*?)<\/incoming-message>/);
        if (xmlMatch) {
          const unescape = (s: string) => s.replace(/&#x27;/g, "'").replace(/&#39;/g, "'").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
          const convEntry: ConversationMessage = {
            id: makeId("conv"),
            role: "conversation",
            direction: "incoming",
            senderName: unescape(xmlMatch[1]),
            content: unescape(xmlMatch[3].trim()),
            conversationId: xmlMatch[2],
            timestamp: Date.now(),
          };
          onUpdateRef.current((prev) => [...prev, convEntry]);
          return;
        }

        // Regular notice (steer, command, agent)
        const noticeEntry: NoticeMessage = {
          id: makeId("stream-notice"),
          role: "notice",
          content: rawContent,
          notification_type: d.notification_type as NotificationType | undefined,
          timestamp: Date.now(),
        };
        onUpdateRef.current((prev) => [...prev, noticeEntry]);
        return;
      }

      // run_start: ensure we have an assistant turn ready
      if (event.type === "run_start" && !turnIdRef.current) {
        ensureReconnectTurn();
        return;
      }

      // run_done: finalize current turn
      if (event.type === "run_done") {
        const doneId = turnIdRef.current;
        if (doneId) {
          onUpdateRef.current((prev) =>
            prev.map((e) =>
              e.id === doneId && e.role === "assistant"
                ? { ...e, streaming: false, endTimestamp: Date.now() } as AssistantTurn
                : e,
            ),
          );
        }
        turnIdRef.current = "";
        hasBoundRef.current = false;
        return;
      }

      // For auto-reconnect: no turn has been created by handleSendMessage.
      // Only create a turn for content events that actually render into turns.
      // task_start/task_done/task_error are background task lifecycle events —
      // they must NOT trigger turn creation (otherwise they create a spurious empty
      // turn before the notice event arrives, pushing notice below T2's content).
      const TURN_CONTENT_EVENTS = new Set(["text", "tool_call", "tool_result", "error", "cancelled", "retry"]);
      if (!turnIdRef.current && TURN_CONTENT_EVENTS.has(event.type)) {
        ensureReconnectTurn();
      }

      const { messageId } = processStreamEvent(
        event,
        turnIdRef.current,
        onUpdateRef.current,
        // runtimeStatus is managed by useThreadStream; pass no-op here
        () => {},
      );

      // Bind temporary turn ID to the server-assigned message ID (first time only)
      if (messageId && turnIdRef.current && messageId !== turnIdRef.current && !hasBoundRef.current) {
        hasBoundRef.current = true;
        const tempId = turnIdRef.current;
        turnIdRef.current = messageId;
        onUpdateRef.current((prev) =>
          prev.map((e) =>
            e.id === tempId && e.role === "assistant"
              ? { ...e, id: messageId, messageIds: [messageId] } as AssistantTurn
              : e,
          ),
        );
      }
    });
  }, [subscribe]);

  const handleSendMessage = useCallback(
    async (message: string) => {
      const tempTurnId = makeId("turn");
      const userEntry: ChatEntry = {
        id: makeId("user"),
        role: "user",
        content: message,
        timestamp: Date.now(),
      };
      const assistantTurn: AssistantTurn = {
        id: tempTurnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
        streaming: true,
      };

      // Set turn context before connect() so the subscriber knows which turn to update
      turnIdRef.current = tempTurnId;
      hasBoundRef.current = false;
      // @@@optimistic-dedup - track this entry so conversation notice can replace it
      pendingConvRef.current = userEntry.id;

      flushSync(() => {
        onUpdateRef.current((prev) => [...prev, userEntry, assistantTurn]);
        setSendPending(true);
      });

      try {
        // @@@conversation-routing - all messages go through conversation API
        if (!conversationId) throw new Error("No conversation context");
        await sendConversationMessage(conversationId, message);
        // No brain thread → no run_start event to clear sendPending.
        // Reset immediately — conversation SSE handles message arrival.
        if (!threadId) setSendPending(false);
        // Connection is persistent — no need to reconnect.
        // run_start event will confirm isRunning.
      } catch (err) {
        setSendPending(false);
        // Show error in the assistant turn
        if (err instanceof Error) {
          onUpdateRef.current((prev) =>
            prev.map((e) =>
              e.id === tempTurnId && e.role === "assistant"
                ? {
                    ...e,
                    streaming: false,
                    segments: [{ type: "text" as const, content: `\n\nError: ${err.message}` }],
                  } as AssistantTurn
                : e,
            ),
          );
        }
        turnIdRef.current = "";
        hasBoundRef.current = false;
      }
    },
    [threadId, conversationId],
  );

  const handleStopStreaming = useCallback(async () => {
    if (!threadId) return;
    try {
      await cancelRun(threadId);
    } catch (err) {
      console.error("Failed to cancel run:", err);
    }
    // Don't disconnect — persistent connection stays open.
    // cancelled + run_done events will arrive and update state.
  }, [threadId]);

  return { runtimeStatus, isRunning, handleSendMessage, handleStopStreaming };
}
