import { useCallback, useState } from "react";
import type { Activity } from "../api";

interface StreamEvent {
  type: string;
  data?: unknown;
}

export function useActivities() {
  const [activities, setActivities] = useState<Activity[]>([]);

  const handleActivityEvent = useCallback((event: StreamEvent) => {
    const data = (event.data ?? {}) as Record<string, unknown>;

    if (event.type === "command_progress") {
      setActivities((prev) => {
        const id = data.command_id as string;
        const existing = prev.find((a) => a.commandId === id);
        const activity: Activity = {
          id: existing?.id ?? `cmd-${id}`,
          type: "command",
          label: (data.command_line as string) ?? "command",
          status: data.done ? "done" : "running",
          startTime: existing?.startTime ?? Date.now(),
          outputPreview: (data.output_preview as string) ?? "",
          commandId: id,
        };
        return existing
          ? prev.map((a) => (a.commandId === id ? activity : a))
          : [...prev, activity];
      });
    } else if (event.type === "background_task_start") {
      setActivities((prev) => [
        ...prev,
        {
          id: `task-${data.task_id}`,
          type: "background_task",
          label: `Sub-agent ${data.task_id}`,
          status: "running",
          startTime: Date.now(),
          taskId: data.task_id as string,
        },
      ]);
    } else if (event.type === "background_task_text") {
      setActivities((prev) =>
        prev.map((a) =>
          a.taskId === data.task_id
            ? { ...a, outputPreview: ((a.outputPreview ?? "") + (data.content as string)).slice(-500) }
            : a,
        ),
      );
    } else if (event.type === "background_task_done") {
      setActivities((prev) =>
        prev.map((a) => (a.taskId === data.task_id ? { ...a, status: "done" as const } : a)),
      );
    } else if (event.type === "background_task_error") {
      setActivities((prev) =>
        prev.map((a) => (a.taskId === data.task_id ? { ...a, status: "error" as const } : a)),
      );
    }
  }, []);

  const cancelCommand = useCallback(async (threadId: string, commandId: string) => {
    await fetch(`/api/threads/${threadId}/commands/${commandId}/cancel`, { method: "POST" });
    setActivities((prev) =>
      prev.map((a) => (a.commandId === commandId ? { ...a, status: "cancelled" as const } : a)),
    );
  }, []);

  const cancelTask = useCallback(async (threadId: string, taskId: string) => {
    await fetch(`/api/threads/${threadId}/tasks/${taskId}/cancel`, { method: "POST" });
    setActivities((prev) =>
      prev.map((a) => (a.taskId === taskId ? { ...a, status: "cancelled" as const } : a)),
    );
  }, []);

  return { activities, handleActivityEvent, cancelCommand, cancelTask };
}
