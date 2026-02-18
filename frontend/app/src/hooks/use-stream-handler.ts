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
  const { threadId, refreshThreads, onUpdate } = deps;

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  // Keep a stable ref to onUpdate for use inside effects/async callbacks
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const handleSendMessage = useCallback(
    async (message: string) => {
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const turnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: turnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
      };

      onUpdateRef.current((prev) => [...prev, userEntry, assistantTurn]);

      setStreamTurnId(turnId);
      setIsStreaming(true);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        await startRun(threadId, message, (event) => {
          processStreamEvent(event, turnId, onUpdateRef.current, setIsStreaming, setRuntimeStatus);
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

  // Reconnect to an in-progress run when threadId changes or on mount
  useEffect(() => {
    if (!threadId) return;

    const ac = new AbortController();

    (async () => {
      try {
        const runtime = await getThreadRuntime(threadId);
        const state = runtime?.state?.state;
        if (state !== "ACTIVE") return;

        // Agent is running — reconnect via observe
        const turnId = makeId("reconnect-turn");
        const assistantTurn: AssistantTurn = {
          id: turnId,
          role: "assistant",
          segments: [],
          timestamp: Date.now(),
        };

        onUpdateRef.current((prev) => [...prev, assistantTurn]);
        setStreamTurnId(turnId);
        setIsStreaming(true);
        abortControllerRef.current = ac;

        await observeRun(threadId, (event) => {
          processStreamEvent(event, turnId, onUpdateRef.current, setIsStreaming, setRuntimeStatus);
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
  }, [threadId, refreshThreads]);

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
