import { useEffect, useRef } from "react";
import { streamActivityEvents } from "../api/streaming";
import type { StreamEvent } from "../api/types";

/**
 * Subscribe to activity SSE when main SSE is closed but background activities remain.
 */
export function useActivitySSE(
  threadId: string | undefined,
  enabled: boolean,
  onEvent: (event: StreamEvent) => void,
): void {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!threadId || !enabled) return;

    const controller = new AbortController();
    streamActivityEvents(threadId, (ev) => onEventRef.current(ev), controller.signal).catch((err) => console.warn("[useActivitySSE] stream ended:", err));

    return () => controller.abort();
  }, [threadId, enabled]);
}
