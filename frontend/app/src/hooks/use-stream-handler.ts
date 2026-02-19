import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelRun,
  getThreadRuntime,
  observeRun,
  startRun,
  type AssistantTurn,
  type ChatEntry,
  type StreamStatus,
} from "../api";
import { processStreamEvent } from "./stream-event-handlers";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface StreamHandlerDeps {
  threadId: string;
  refreshThreads: () => Promise<void>;
  onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void;
  /** Resolves when thread snapshot is loaded (entries populated with stable IDs). */
  loadThread: (threadId: string) => Promise<void>;
  /** True while useThreadData is loading the snapshot — reconnect waits for this. */
  loading: boolean;
}

export interface StreamHandlerState {
  isStreaming: boolean;
  streamTurnId: string | null;
  runtimeStatus: StreamStatus | null;
}

export interface StreamHandlerActions {
  handleSendMessage: (message: string) => Promise<void>;
  handleStopStreaming: () => Promise<void>;
}

export function useStreamHandler(deps: StreamHandlerDeps): StreamHandlerState & StreamHandlerActions {
  const { threadId, refreshThreads, onUpdate, loading } = deps;

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const handleSendMessage = useCallback(
    async (message: string) => {
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const tempTurnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: tempTurnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
      };

      onUpdateRef.current((prev) => [...prev, userEntry, assistantTurn]);

      setStreamTurnId(tempTurnId);
      setIsStreaming(true);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let boundTurnId = tempTurnId;
      let hasBound = false;

      try {
        await startRun(threadId, message, (event) => {
          // Rebind turn ID to the first message_id from backend
          const { messageId } = processStreamEvent(
            event, boundTurnId, onUpdateRef.current, setIsStreaming, setRuntimeStatus,
          );
          if (!hasBound && messageId) {
            hasBound = true;
            boundTurnId = messageId;
            // Rename the temp turn to the stable message_id
            onUpdateRef.current((prev) =>
              prev.map((e) =>
                e.id === tempTurnId && e.role === "assistant"
                  ? { ...e, id: messageId, messageIds: [messageId] } as AssistantTurn
                  : e,
              ),
            );
            setStreamTurnId(messageId);
          }
        }, abortController.signal);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          // Aborted by user or thread switch
        } else {
          throw error;
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
        setStreamTurnId(null);
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
    setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 500);
  }, [threadId]);

  // Reconnect: after snapshot is loaded (loading=false), check if agent is active → observeRun
  useEffect(() => {
    if (!threadId || loading) return;

    const ac = new AbortController();

    (async () => {
      try {
        // Snapshot is already loaded by useThreadData — entries have stable IDs

        // Check if agent is still running
        const runtime = await getThreadRuntime(threadId);
        const state = runtime?.state?.state;
        if (state !== "ACTIVE") return;

        if (ac.signal.aborted) return;

        // Find the last assistant turn from loaded entries (has stable message_id)
        let turnId: string | null = null;
        onUpdateRef.current((prev) => {
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].role === "assistant") {
              turnId = prev[i].id;
              break;
            }
          }
          // If no assistant turn exists yet, create one
          if (!turnId) {
            turnId = makeId("reconnect-turn");
            const newTurn: AssistantTurn = {
              id: turnId,
              role: "assistant",
              segments: [],
              timestamp: Date.now(),
            };
            return [...prev, newTurn];
          }
          return prev;
        });

        if (!turnId || ac.signal.aborted) return;

        setStreamTurnId(turnId);
        setIsStreaming(true);
        abortControllerRef.current = ac;

        // Observe with dedup — SSE events match snapshot entries by message_id
        await observeRun(threadId, (event) => {
          processStreamEvent(event, turnId!, onUpdateRef.current, setIsStreaming, setRuntimeStatus);
        }, ac.signal);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        console.error("Reconnect failed:", error);
      } finally {
        setIsStreaming(false);
        setStreamTurnId(null);
        void refreshThreads();
      }
    })();

    return () => {
      ac.abort();
    };
  }, [threadId, loading, refreshThreads]);

  // Refresh sidebar when streaming state changes (shows/hides spinner)
  const prevStreaming = useRef(isStreaming);
  useEffect(() => {
    if (prevStreaming.current !== isStreaming) {
      prevStreaming.current = isStreaming;
      void refreshThreads();
    }
  }, [isStreaming, refreshThreads]);

  return { isStreaming, streamTurnId, runtimeStatus, handleSendMessage, handleStopStreaming };
}
