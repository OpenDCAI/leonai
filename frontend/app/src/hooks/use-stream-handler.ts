import { useCallback, useRef, useState } from "react";
import {
  cancelRun,
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
}

export interface StreamHandlerState {
  isStreaming: boolean;
  streamTurnId: string | null;
  runtimeStatus: StreamStatus | null;
}

export interface StreamHandlerActions {
  handleSendMessage: (message: string, onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void) => Promise<void>;
  handleStopStreaming: () => Promise<void>;
}

export function useStreamHandler(deps: StreamHandlerDeps): StreamHandlerState & StreamHandlerActions {
  const { threadId, refreshThreads } = deps;

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = useCallback(
    async (message: string, onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void) => {
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const turnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: turnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
      };

      console.log('[handleSendMessage] Adding user message:', message);
      // Initialize entries with user message and assistant turn
      onUpdate((prev) => {
        console.log('[handleSendMessage] Previous entries count:', prev.length);
        return [...prev, userEntry, assistantTurn];
      });

      setStreamTurnId(turnId);
      setIsStreaming(true);
      // Don't reset runtimeStatus here - keep previous status if exists

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        await startRun(threadId, message, (event) => {
          processStreamEvent(event, turnId, onUpdate, setIsStreaming, setRuntimeStatus);
        }, abortController.signal);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          // Aborted by user
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

  return { isStreaming, streamTurnId, runtimeStatus, handleSendMessage, handleStopStreaming };
}
