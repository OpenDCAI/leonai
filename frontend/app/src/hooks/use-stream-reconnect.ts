import { useEffect, useRef } from "react";
import { getThreadRuntime, streamEvents, type AssistantTurn, type ChatEntry, type StreamStatus } from "../api";
import { processStreamEvent } from "./stream-event-handlers";
import { makeId } from "./utils";

interface ReconnectDeps {
  threadId: string;
  loading: boolean;
  refreshThreads: () => Promise<void>;
  onUpdateRef: React.RefObject<(updater: (prev: ChatEntry[]) => ChatEntry[]) => void>;
  abortRef: React.RefObject<AbortController | null>;
  setRuntimeStatus: (v: StreamStatus | null) => void;
  setIsRunning: (v: boolean) => void;
}

function findOrCreateReconnectTurn(
  prev: ChatEntry[],
): { entries: ChatEntry[]; turnId: string } {
  for (let i = prev.length - 1; i >= 0; i--) {
    if (prev[i].role === "assistant") {
      return {
        entries: prev.map((e) =>
          e.id === prev[i].id && e.role === "assistant"
            ? { ...e, streaming: true } as AssistantTurn : e,
        ),
        turnId: prev[i].id,
      };
    }
  }
  const turnId = makeId("reconnect-turn");
  const newTurn: AssistantTurn = { id: turnId, role: "assistant", segments: [], timestamp: Date.now(), streaming: true };
  return { entries: [...prev, newTurn], turnId };
}

export function useStreamReconnect(deps: ReconnectDeps) {
  const { threadId, loading, refreshThreads, onUpdateRef, abortRef, setRuntimeStatus, setIsRunning } = deps;
  const setTurnStreaming = (turnId: string, streaming: boolean) => {
    onUpdateRef.current((prev) =>
      prev.map((e) => e.id === turnId && e.role === "assistant" ? { ...e, streaming } as AssistantTurn : e),
    );
  };

  useEffect(() => {
    if (!threadId || loading) return;
    const ac = new AbortController();

    (async () => {
      let turnId: string | null = null;
      try {
        const runtime = await getThreadRuntime(threadId);
        if (runtime) setRuntimeStatus(runtime);
        if (runtime?.state?.state !== "active") { setIsRunning(false); return; }
        if (ac.signal.aborted) return;

        setIsRunning(true);
        onUpdateRef.current((prev) => {
          const result = findOrCreateReconnectTurn(prev);
          turnId = result.turnId;
          return result.entries;
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
        setIsRunning(false);
        if (turnId) setTurnStreaming(turnId, false);
        void refreshThreads();
      }
    })();

    return () => { ac.abort(); };
  }, [threadId, loading, refreshThreads]);
}
