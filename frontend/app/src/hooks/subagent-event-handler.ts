import type { AssistantTurn, ToolStep } from "../api";
import type { UpdateEntries, StreamEvent } from "./stream-event-handlers";

type EventPayload = Record<string, unknown>;
type SubagentStream = NonNullable<ToolStep["subagent_stream"]>;
type Mutator = (stream: SubagentStream, data: EventPayload) => void;

const MUTATORS: Record<string, Mutator> = {
  subagent_task_start: (s, d) => { s.task_id = (d.task_id as string) || ""; s.thread_id = (d.thread_id as string) || ""; s.status = "running"; },
  subagent_task_text: (s, d) => { s.text += (d.content as string) || ""; },
  subagent_task_tool_call: (s, d) => { s.tool_calls = [...s.tool_calls, { id: (d.tool_call_id as string) || "", name: (d.name as string) || "", args: d.args || {} }]; },
  subagent_task_done: (s) => { s.status = "completed"; },
  subagent_task_error: (s, d) => { s.status = "error"; s.error = (d.error as string) || "Unknown error"; },
};

const DEFAULT_STREAM: SubagentStream = { task_id: "", thread_id: "", text: "", tool_calls: [], status: "running" };

export function handleSubagentEvent(
  event: StreamEvent,
  turnId: string,
  onUpdate: UpdateEntries,
) {
  const data = event.data as EventPayload;
  const parentId = data?.parent_tool_call_id as string;
  const mutator = MUTATORS[event.type];
  if (!parentId || !mutator) return;

  onUpdate((prev) =>
    prev.map((e) => {
      if (e.id !== turnId || e.role !== "assistant") return e;
      const t = e as AssistantTurn;
      return { ...t, segments: t.segments.map((s) => {
        if (s.type !== "tool" || s.step.id !== parentId) return s;
        const stream = { ...(s.step.subagent_stream ?? DEFAULT_STREAM) };
        mutator(stream, data);
        return { ...s, step: { ...s.step, subagent_stream: stream } };
      }) };
    }),
  );
}
