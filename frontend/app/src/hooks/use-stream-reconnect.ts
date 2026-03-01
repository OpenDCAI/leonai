import { useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { getThreadRuntime, streamEvents, type AssistantTurn, type ChatEntry, type StreamStatus } from "../api";
import { processStreamEvent } from "./stream-event-handlers";
import { makeId } from "./utils";

interface ReconnectDeps {
  threadId: string;
  loading: boolean;
  /** When true, a run was just started — skip runtime active check. */
  runStarted?: boolean;
  /** Bump to force a reconnection attempt (e.g., when activity SSE signals new_run). */
  reconnectKey?: number;
  refreshThreads: () => Promise<void>;
  onUpdateRef: React.RefObject<(updater: (prev: ChatEntry[]) => ChatEntry[]) => void>;
  abortRef: React.RefObject<AbortController | null>;
  setRuntimeStatus: (v: StreamStatus | null) => void;
  setIsRunning: (v: boolean) => void;
  onActivityEventRef?: React.RefObject<((event: { type: string; data?: unknown }) => void) | undefined>;
}

/** Reuse the last entry if it's an assistant turn; otherwise create a new one. */
function applyReconnectTurn(
  prev: ChatEntry[],
  fallbackId: string,
): { entries: ChatEntry[]; turnId: string } {
  const last = prev[prev.length - 1];
  if (last?.role === "assistant") {
    return {
      entries: prev.map((e) =>
        e.id === last.id && e.role === "assistant"
          ? { ...e, streaming: true } as AssistantTurn : e,
      ),
      turnId: last.id,
    };
  }
  const newTurn: AssistantTurn = { id: fallbackId, role: "assistant", segments: [], timestamp: Date.now(), streaming: true };
  return { entries: [...prev, newTurn], turnId: fallbackId };
}

export function useStreamReconnect(deps: ReconnectDeps) {
  const { threadId, loading, runStarted, refreshThreads, onUpdateRef, abortRef, setRuntimeStatus, setIsRunning, onActivityEventRef } = deps;
  const runStartedRef = useRef(runStarted);
  runStartedRef.current = runStarted;

  const setTurnStreaming = (turnId: string, streaming: boolean) => {
    onUpdateRef.current((prev) =>
      prev.map((e) => e.id === turnId && e.role === "assistant" ? { ...e, streaming } as AssistantTurn : e),
    );
  };

  useEffect(() => {
    if (!threadId || loading) return;
    const ac = new AbortController();
    const fallbackId = makeId("reconnect-turn");
    const resolved = { turnId: fallbackId };

    (async () => {
      try {
        const runtime = await getThreadRuntime(threadId);
        if (runtime) setRuntimeStatus(runtime);
        const isActive = runtime?.state?.state === "active" || runStartedRef.current;
        if (!isActive) { setIsRunning(false); return; }
        if (ac.signal.aborted) return;

        flushSync(() => {
          setIsRunning(true);
          onUpdateRef.current((prev) => {
            const result = applyReconnectTurn(prev, fallbackId);
            resolved.turnId = result.turnId;
            return result.entries;
          });
        });

        if (ac.signal.aborted) return;
        abortRef.current = ac;

        await streamEvents(threadId, (event) => {
          processStreamEvent(event, resolved.turnId, onUpdateRef.current, setRuntimeStatus, onActivityEventRef?.current);
        }, ac.signal, runtime?.last_seq ?? 0);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        console.error("Reconnect failed:", error);
      } finally {
        setIsRunning(false);
        setTurnStreaming(resolved.turnId, false);
        void refreshThreads();
      }
    })();

    return () => { ac.abort(); };
  }, [threadId, loading, refreshThreads, deps.reconnectKey]);
}
