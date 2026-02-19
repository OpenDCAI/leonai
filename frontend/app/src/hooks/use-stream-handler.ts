import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelRun,
  getThreadRuntime,
  postRun,
  streamEvents,
  type AssistantTurn,
  type ChatEntry,
  type StreamStatus,
} from "../api";
import { processStreamEvent } from "./stream-event-handlers";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Mark a turn's streaming field in the entries array. */
function setTurnStreaming(
  onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void,
  turnId: string,
  streaming: boolean,
) {
  onUpdate((prev) =>
    prev.map((e) =>
      e.id === turnId && e.role === "assistant"
        ? { ...e, streaming } as AssistantTurn
        : e,
    ),
  );
}

interface StreamHandlerDeps {
  threadId: string;
  refreshThreads: () => Promise<void>;
  onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void;
  /** True while useThreadData is loading the snapshot — reconnect waits for this. */
  loading: boolean;
}

export interface StreamHandlerState {
  runtimeStatus: StreamStatus | null;
}

export interface StreamHandlerActions {
  handleSendMessage: (message: string) => Promise<void>;
  handleStopStreaming: () => Promise<void>;
}

export function useStreamHandler(deps: StreamHandlerDeps): StreamHandlerState & StreamHandlerActions {
  const { threadId, refreshThreads, onUpdate, loading } = deps;

  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  // Abort current stream when thread changes
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, [threadId]);

  // Graceful cleanup on page unload
  useEffect(() => {
    const cleanup = () => abortRef.current?.abort();
    window.addEventListener("beforeunload", cleanup);
    return () => window.removeEventListener("beforeunload", cleanup);
  }, []);

  const handleSendMessage = useCallback(
    async (message: string) => {
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const tempTurnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: tempTurnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
        streaming: true,
      };

      onUpdateRef.current((prev) => [...prev, userEntry, assistantTurn]);

      const ac = new AbortController();
      abortRef.current = ac;

      let boundTurnId = tempTurnId;
      let hasBound = false;

      try {
        await postRun(threadId, message, ac.signal);
        await streamEvents(threadId, (event) => {
          const { messageId } = processStreamEvent(
            event, boundTurnId, onUpdateRef.current, setRuntimeStatus,
          );
          if (!hasBound && messageId) {
            hasBound = true;
            boundTurnId = messageId;
            onUpdateRef.current((prev) =>
              prev.map((e) =>
                e.id === tempTurnId && e.role === "assistant"
                  ? { ...e, id: messageId, messageIds: [messageId] } as AssistantTurn
                  : e,
              ),
            );
          }
        }, ac.signal);
      } catch (e) {
        if (e instanceof Error && e.name !== "AbortError") {
          onUpdateRef.current((prev) =>
            prev.map((entry) =>
              entry.id === boundTurnId && entry.role === "assistant"
                ? { ...entry, segments: [...(entry as AssistantTurn).segments, { type: "text" as const, content: `\n\nError: ${(e as Error).message}` }] } as AssistantTurn
                : entry,
            ),
          );
        }
      } finally {
        abortRef.current = null;
        setTurnStreaming(onUpdateRef.current, boundTurnId, false);
        await refreshThreads();
      }
    },
    [threadId, refreshThreads],
  );

  const handleStopStreaming = useCallback(async () => {
    try {
      await cancelRun(threadId);
    } catch (e) {
      console.error("Failed to cancel run:", e);
    }
    setTimeout(() => abortRef.current?.abort(), 500);
  }, [threadId]);

  // Reconnect: after snapshot is loaded, check if agent is active → streamEvents
  useEffect(() => {
    if (!threadId || loading) return;

    const ac = new AbortController();

    (async () => {
      let turnId: string | null = null;
      try {
        const runtime = await getThreadRuntime(threadId);
        const state = runtime?.state?.state;
        if (state !== "active") return;

        if (ac.signal.aborted) return;

        // Find the last assistant turn or create one
        onUpdateRef.current((prev) => {
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].role === "assistant") {
              turnId = prev[i].id;
              break;
            }
          }
          if (!turnId) {
            turnId = makeId("reconnect-turn");
            const newTurn: AssistantTurn = {
              id: turnId,
              role: "assistant",
              segments: [],
              timestamp: Date.now(),
              streaming: true,
            };
            return [...prev, newTurn];
          }
          return prev.map((e) =>
            e.id === turnId && e.role === "assistant"
              ? { ...e, streaming: true } as AssistantTurn
              : e,
          );
        });

        if (!turnId || ac.signal.aborted) return;

        abortRef.current = ac;

        await streamEvents(threadId, (event) => {
          processStreamEvent(event, turnId!, onUpdateRef.current, setRuntimeStatus);
        }, ac.signal);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        console.error("Reconnect failed:", error);
      } finally {
        if (turnId) setTurnStreaming(onUpdateRef.current, turnId, false);
        void refreshThreads();
      }
    })();

    return () => { ac.abort(); };
  }, [threadId, loading, refreshThreads]);

  return { runtimeStatus, handleSendMessage, handleStopStreaming };
}
