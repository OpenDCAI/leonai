import { CheckCircle2, ChevronDown, ChevronRight, Loader2, Square, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Activity, ToolStep } from "../../api";
import { DEFAULT_BADGE, TOOL_BADGE_STYLES } from "../chat-area/constants";
import { getToolRenderer } from "../tool-renderers";

const ACTIVITY_VISIBLE_AFTER_DONE_MS = 30_000;

interface StepsViewProps {
  steps: ToolStep[];
  activities: Activity[];
  focusedStepId: string | null;
  onFocusStep: (id: string | null) => void;
  onCancelCommand?: (commandId: string) => void;
  onCancelTask?: (taskId: string) => void;
}

export function StepsView({
  steps,
  activities,
  focusedStepId,
  onFocusStep,
  onCancelCommand,
  onCancelTask,
}: StepsViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const visibleActivities = activities.filter(
    (a) => a.status === "running" || Date.now() - a.startTime < ACTIVITY_VISIBLE_AFTER_DONE_MS,
  );

  // Auto-scroll to focused step
  useEffect(() => {
    if (!focusedStepId || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-step-id="${focusedStepId}"]`);
    if (el) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [focusedStepId]);

  if (steps.length === 0 && visibleActivities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
        暂无工具调用
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto bg-white">
      {/* Running Activities */}
      {visibleActivities.length > 0 && (
        <ActivitySection
          activities={visibleActivities}
          onCancelCommand={onCancelCommand}
          onCancelTask={onCancelTask}
        />
      )}

      {/* Step message flow — chronological order */}
      <div className="px-3 py-2 space-y-2">
        {steps.map((step) => (
          <StepCard
            key={step.id}
            step={step}
            isFocused={step.id === focusedStepId}
            onFocus={() => onFocusStep(step.id)}
          />
        ))}
      </div>
    </div>
  );
}

/* -- Step card (message-style) -- */

function StepCard({
  step,
  isFocused,
  onFocus,
}: {
  step: ToolStep;
  isFocused: boolean;
  onFocus: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const badge = TOOL_BADGE_STYLES[step.name] ?? { ...DEFAULT_BADGE, label: step.name };
  const Renderer = getToolRenderer(step);

  // Auto-expand when focused from chat area jump
  useEffect(() => {
    if (isFocused) setExpanded(true);
  }, [isFocused]);

  return (
    <div
      data-step-id={step.id}
      className={`rounded-lg border transition-colors ${
        isFocused ? "border-blue-300 bg-blue-50/30" : "border-[#f0f0f0] hover:border-[#e0e0e0]"
      }`}
    >
      {/* Header — click to toggle */}
      <div
        className="flex items-center gap-1.5 px-3 py-2 cursor-pointer"
        onClick={() => { setExpanded((v) => !v); onFocus(); }}
      >
        <StatusIcon status={step.status} />
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}
        >
          {badge.label || step.name}
        </span>
        <div className="flex-1 min-w-0 text-xs text-[#737373] truncate font-mono">
          {getStepSummary(step)}
        </div>
        {expanded
          ? <ChevronDown className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-[#d4d4d4] flex-shrink-0" />}
      </div>

      {/* Detail — only when expanded */}
      {expanded && (
        <div className="px-3 pb-2">
          <div className="text-xs">
            <Renderer step={step} expanded={true} />
          </div>
          {step.result && (
            <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[11px] text-[#525252] bg-[#fafafa] rounded p-2 max-h-[300px] overflow-y-auto border border-[#f0f0f0]">
              {step.result}
            </pre>
          )}
          {step.status === "cancelled" && (
            <div className="mt-1 text-[11px] text-[#a3a3a3] italic">
              {step.result || "已取消"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* -- Activity section -- */

function ActivitySection({
  activities,
  onCancelCommand,
  onCancelTask,
}: {
  activities: Activity[];
  onCancelCommand?: (commandId: string) => void;
  onCancelTask?: (taskId: string) => void;
}) {
  return (
    <div className="border-b border-[#e5e5e5] bg-[#fafafa]">
      <div className="px-3 py-1.5">
        <div className="text-[10px] text-[#a3a3a3] font-medium uppercase tracking-wide">
          进行中
        </div>
      </div>
      {activities.map((activity) => (
        <ActivityItem
          key={activity.id}
          activity={activity}
          onCancel={() => {
            if (activity.type === "command" && activity.commandId) {
              onCancelCommand?.(activity.commandId);
            } else if (activity.type === "background_task" && activity.taskId) {
              onCancelTask?.(activity.taskId);
            }
          }}
        />
      ))}
    </div>
  );
}

function ActivityItem({
  activity,
  onCancel,
}: {
  activity: Activity;
  onCancel: () => void;
}) {
  return (
    <div className="px-3 py-2 border-b border-[#f5f5f5]">
      <div className="flex items-center gap-2">
        <ActivityStatusIcon status={activity.status} />
        <span className="text-[11px] font-mono text-[#525252] truncate flex-1 min-w-0">
          {activity.label}
        </span>
        {activity.status === "running" ? (
          <button
            onClick={onCancel}
            className="flex-shrink-0 p-0.5 rounded hover:bg-red-50 text-red-400 hover:text-red-600 transition-colors"
            title="取消"
          >
            <Square className="w-3 h-3" />
          </button>
        ) : (
          <span className="text-[10px] text-[#a3a3a3] flex-shrink-0">
            {formatRelativeTime(activity.startTime)}
          </span>
        )}
      </div>
      {activity.outputPreview && (
        <pre className="mt-1 ml-5.5 text-[10px] text-[#737373] font-mono truncate max-w-full overflow-hidden">
          {activity.outputPreview.slice(-200)}
        </pre>
      )}
    </div>
  );
}

/* -- Shared helpers -- */

function StatusIcon({ status }: { status: ToolStep["status"] }) {
  switch (status) {
    case "calling":
      return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />;
    case "done":
      return <CheckCircle2 className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />;
    case "error":
      return <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />;
    case "cancelled":
      return <XCircle className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />;
  }
}

function ActivityStatusIcon({ status }: { status: Activity["status"] }) {
  switch (status) {
    case "running":
      return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />;
    case "done":
      return <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />;
    case "error":
      return <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />;
    case "cancelled":
      return <XCircle className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />;
  }
}

function formatRelativeTime(startTime: number): string {
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  if (elapsed < 60) return `${elapsed}s`;
  const mins = Math.floor(elapsed / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  return `${hours}h`;
}

function getStepSummary(step: ToolStep): string {
  const args = step.args as Record<string, unknown> | null;
  if (!args) return step.name;

  const filePath =
    (args.FilePath as string) ??
    (args.file_path as string) ??
    (args.path as string);
  if (filePath) {
    const parts = filePath.split("/");
    return parts[parts.length - 1] || filePath;
  }

  const cmd =
    (args.CommandLine as string) ??
    (args.command as string) ??
    (args.cmd as string);
  if (cmd) {
    return cmd.length > 60 ? cmd.slice(0, 57) + "..." : cmd;
  }

  const pattern =
    (args.Pattern as string) ??
    (args.pattern as string) ??
    (args.query as string) ??
    (args.SearchPath as string);
  if (pattern) {
    return pattern.length > 60 ? pattern.slice(0, 57) + "..." : pattern;
  }

  const desc = (args.description as string) ?? (args.prompt as string);
  if (desc) {
    return desc.length > 60 ? desc.slice(0, 57) + "..." : desc;
  }

  return step.name;
}
