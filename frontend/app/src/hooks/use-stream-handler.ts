import { useCallback, useRef, useState } from "react";
import {
  cancelRun,
  createThread,
  startRun,
  type AssistantTurn,
  type ChatEntry,
  type StreamStatus,
  type ThreadSummary,
} from "../api";
import { processStreamEvent } from "./stream-event-handlers";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface StreamHandlerDeps {
  activeThreadId: string | null;
  selectedSandbox: string;
  setEntries: React.Dispatch<React.SetStateAction<ChatEntry[]>>;
  setThreads: React.Dispatch<React.SetStateAction<ThreadSummary[]>>;
  setActiveThreadId: (id: string | null) => void;
  loadThread: (threadId: string) => Promise<void>;
  refreshThreads: () => Promise<void>;
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
  const { activeThreadId, selectedSandbox, setEntries, setThreads, setActiveThreadId, loadThread, refreshThreads } = deps;

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = useCallback(
    async (message: string) => {
      let threadId = activeThreadId;
      if (!threadId) {
        const created = await createThread(selectedSandbox);
        setThreads((prev) => [created, ...prev]);
        setActiveThreadId(created.thread_id);
        threadId = created.thread_id;
      }
      if (!threadId) return;

      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const turnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: turnId,
        role: "assistant",
        segments: [],
        timestamp: Date.now(),
      };
      setEntries((prev) => [...prev, userEntry, assistantTurn]);
      setStreamTurnId(turnId);
      setIsStreaming(true);
      setRuntimeStatus(null);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let aborted = false;
      try {
        await startRun(threadId, message, (event) => {
          processStreamEvent(event, turnId, setEntries, setIsStreaming, setRuntimeStatus);
        }, abortController.signal);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          aborted = true;
        } else {
          throw error;
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
        setStreamTurnId(null);
        if (!aborted) {
          await loadThread(threadId);
        }
        await refreshThreads();
      }
    },
    [activeThreadId, loadThread, refreshThreads, selectedSandbox, setEntries, setThreads, setActiveThreadId],
  );

  const handleStopStreaming = useCallback(async () => {
    if (activeThreadId) {
      try {
        await cancelRun(activeThreadId);
      } catch (e) {
        console.error("Failed to cancel run:", e);
      }
    }
    setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 500);
  }, [activeThreadId]);

  return { isStreaming, streamTurnId, runtimeStatus, handleSendMessage, handleStopStreaming };
}
