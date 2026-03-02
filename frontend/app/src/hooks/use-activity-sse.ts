import { useEffect, useRef, useState } from "react";
import { streamActivityEvents } from "../api/streaming";
import type { StreamEvent } from "../api/types";

/** Grace period (ms) to keep activity SSE open after all tasks finish,
 *  so that a follow-up `new_run` event from continue_handler is not missed. */
const GRACE_MS = 5_000;

/**
 * Subscribe to activity SSE when main SSE is closed but background activities remain.
 * Stays connected for a short grace period after the last activity finishes.
 */
export function useActivitySSE(
  threadId: string | undefined,
  enabled: boolean,
  onEvent: (event: StreamEvent) => void,
): void {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  // Keep SSE alive for GRACE_MS after `enabled` flips to false
  const [graceActive, setGraceActive] = useState(false);
  const prevEnabled = useRef(enabled);

  useEffect(() => {
    if (prevEnabled.current && !enabled) {
      // enabled just flipped off → start grace period
      setGraceActive(true);
      const timer = setTimeout(() => setGraceActive(false), GRACE_MS);
      return () => clearTimeout(timer);
    }
    prevEnabled.current = enabled;
  }, [enabled]);

  // Reset grace when enabled turns back on (new_run reconnected main SSE)
  useEffect(() => {
    if (enabled) setGraceActive(false);
  }, [enabled]);

  const shouldConnect = enabled || graceActive;

  useEffect(() => {
    if (!threadId || !shouldConnect) return;

    const controller = new AbortController();
    streamActivityEvents(threadId, (ev) => onEventRef.current(ev), controller.signal).catch((err) => console.warn("[useActivitySSE] stream ended:", err));

    return () => controller.abort();
  }, [threadId, shouldConnect]);
}
