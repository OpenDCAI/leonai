import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelRun,
  postRun,
  streamEvents,
  type AssistantTurn,
  type ChatEntry,
  type StreamStatus,
} from "../api";
import { processStreamEvent } from "./stream-event-handlers";
import { useStreamReconnect } from "./use-stream-reconnect";
import { makeId } from "./utils";

interface StreamHandlerDeps {
  threadId: string;
  refreshThreads: () => Promise<void>;
  onUpdate: (updater: (prev: ChatEntry[]) => ChatEntry[]) => void;
  /** True while useThreadData is loading the snapshot — reconnect waits for this. */
  loading: boolean;
}

export interface StreamHandlerState {
  runtimeStatus: StreamStatus | null;
  isRunning: boolean;
}

export interface StreamHandlerActions {
  handleSendMessage: (message: string) => Promise<void>;
  handleStopStreaming: () => Promise<void>;
}

export function useStreamHandler(deps: StreamHandlerDeps): StreamHandlerState & StreamHandlerActions {
  const { threadId, refreshThreads, onUpdate, loading } = deps;

  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  // Abort in-flight stream on unmount (key-based remount resets all state)
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
      setIsRunning(true);

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
        setIsRunning(false);
        onUpdateRef.current((prev) => prev.map((e) =>
          e.id === boundTurnId && e.role === "assistant" ? { ...e, streaming: false } as AssistantTurn : e,
        ));
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

  useStreamReconnect({ threadId, loading, refreshThreads, onUpdateRef, abortRef, setRuntimeStatus, setIsRunning });

  return { runtimeStatus, isRunning, handleSendMessage, handleStopStreaming };
}
