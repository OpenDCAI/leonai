import { CheckCircle2, Loader2, Square, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
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
  const detailRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(320);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const focused = steps.find((s) => s.id === focusedStepId) ?? null;

  // Newest first for the list
  const reversedSteps = [...steps].reverse();

  // Filter activities: show running ones + recently completed (within 30s)
  const visibleActivities = activities.filter(
    (a) => a.status === "running" || Date.now() - a.startTime < ACTIVITY_VISIBLE_AFTER_DONE_MS,
  );

  // Auto-scroll list to focused item
  useEffect(() => {
    if (!focusedStepId || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-step-id="${focusedStepId}"]`);
    if (el) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [focusedStepId]);

  // Resizable divider handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      dragStartX.current = e.clientX;
      dragStartWidth.current = leftWidth;
    },
    [leftWidth],
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - dragStartX.current;
      const newWidth = Math.max(200, Math.min(600, dragStartWidth.current + delta));
      setLeftWidth(newWidth);
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  if (steps.length === 0 && visibleActivities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
        暂无工具调用
      </div>
    );
  }

  return (
    <div className="h-full flex bg-white">
      {/* Left sidebar - step list */}
      <div
        className="flex-shrink-0 border-r border-[#e5e5e5] flex flex-col"
        style={{ width: `${leftWidth}px` }}
      >
        <div className="px-3 py-2 border-b border-[#e5e5e5]">
          <div className="text-xs text-[#737373] font-medium">
            全部步骤 ({steps.length})
          </div>
        </div>
        <div ref={listRef} className="flex-1 overflow-y-auto">
          {/* Running Activities section */}
          {visibleActivities.length > 0 && (
            <ActivitySection
              activities={visibleActivities}
              onCancelCommand={onCancelCommand}
              onCancelTask={onCancelTask}
            />
          )}
          {reversedSteps.map((step) => (
            <StepListItem
              key={step.id}
              step={step}
              isSelected={step.id === focusedStepId}
              onClick={() => onFocusStep(step.id)}
            />
          ))}
        </div>
      </div>

      {/* Resizable divider */}
      <div
        className={`w-1 flex-shrink-0 cursor-col-resize hover:bg-blue-400 transition-colors ${
          isDragging ? "bg-blue-500" : "bg-transparent"
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Right detail */}
      <div className="flex-1 flex flex-col min-w-0">
        {!focused ? (
          <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
            选择一个步骤查看详情
          </div>
        ) : (
          <>
            <StepDetailHeader step={focused} />
            <div ref={detailRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {/* Expanded renderer */}
              <div className="border border-[#e5e5e5] rounded-lg p-3">
                <StepRendererWrapper step={focused} />
              </div>
              {/* Result text */}
              {focused.result && (
                <div className="text-xs text-[#525252]">
                  <div className="text-[10px] text-[#a3a3a3] font-medium mb-1">输出</div>
                  <pre className="whitespace-pre-wrap break-words font-mono bg-[#fafafa] rounded-lg p-3 max-h-[400px] overflow-y-auto border border-[#f0f0f0]">
                    {focused.result}
                  </pre>
                </div>
              )}
            </div>
          </>
        )}
      </div>
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
    <div className="border-b border-[#e5e5e5]">
      <div className="px-3 py-1.5 bg-[#fafafa]">
        <div className="text-[10px] text-[#a3a3a3] font-medium uppercase tracking-wide">
          Running Activities
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
  if (elapsed < 60) return `${elapsed}s ago`;
  const mins = Math.floor(elapsed / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ago`;
}

function ActivityItem({
  activity,
  onCancel,
}: {
  activity: Activity;
  onCancel: () => void;
}) {
  return (
    <div className="px-3 py-2 border-b border-[#f5f5f5] bg-[#fefefe]">
      <div className="flex items-center gap-2">
        <ActivityStatusIcon status={activity.status} />
        <span className="text-[11px] font-mono text-[#525252] truncate flex-1 min-w-0">
          {activity.label}
        </span>
        {activity.status === "running" ? (
          <button
            onClick={onCancel}
            className="flex-shrink-0 p-0.5 rounded hover:bg-red-50 text-red-400 hover:text-red-600 transition-colors"
            title="Cancel"
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

/* -- Step list item -- */

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

function getStepSummary(step: ToolStep): string {
  const args = step.args as Record<string, unknown> | null;
  if (!args) return step.name;

  // File operations: show path
  const filePath =
    (args.FilePath as string) ??
    (args.file_path as string) ??
    (args.path as string);
  if (filePath) {
    const parts = filePath.split("/");
    return parts[parts.length - 1] || filePath;
  }

  // Commands: show command
  const cmd =
    (args.CommandLine as string) ??
    (args.command as string) ??
    (args.cmd as string);
  if (cmd) {
    return cmd.length > 60 ? cmd.slice(0, 57) + "..." : cmd;
  }

  // Search: show pattern/query
  const pattern =
    (args.Pattern as string) ??
    (args.pattern as string) ??
    (args.query as string) ??
    (args.SearchPath as string);
  if (pattern) {
    return pattern.length > 60 ? pattern.slice(0, 57) + "..." : pattern;
  }

  // Task: show description
  const desc = (args.description as string) ?? (args.prompt as string);
  if (desc) {
    return desc.length > 60 ? desc.slice(0, 57) + "..." : desc;
  }

  return step.name;
}

function StepListItem({
  step,
  isSelected,
  onClick,
}: {
  step: ToolStep;
  isSelected: boolean;
  onClick: () => void;
}) {
  const badge = TOOL_BADGE_STYLES[step.name] ?? { ...DEFAULT_BADGE, label: step.name };
  const summary = getStepSummary(step);

  return (
    <button
      data-step-id={step.id}
      className={`w-full text-left px-3 py-2 border-b border-[#f5f5f5] transition-colors ${
        isSelected ? "bg-blue-50" : "hover:bg-[#f5f5f5]"
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-1">
        <StatusIcon status={step.status} />
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}
        >
          {badge.label || step.name}
        </span>
      </div>
      <div className="text-[10px] text-[#737373] truncate pl-5.5 font-mono">{summary}</div>
    </button>
  );
}

/* -- Step detail header -- */

function StepDetailHeader({ step }: { step: ToolStep }) {
  const badge = TOOL_BADGE_STYLES[step.name] ?? { ...DEFAULT_BADGE, label: step.name };
  const statusText =
    step.status === "calling"
      ? "执行中"
      : step.status === "done"
        ? "已完成"
        : step.status === "error"
          ? "出错"
          : "已取消";

  return (
    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#e5e5e5] bg-[#fafafa] flex-shrink-0">
      <StatusIcon status={step.status} />
      <span
        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.bg} ${badge.text}`}
      >
        {badge.label || step.name}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-[#737373] font-mono truncate">{step.name}</div>
      </div>
      <span className="text-[10px] text-[#a3a3a3]">{statusText}</span>
    </div>
  );
}

/* -- Step renderer wrapper -- */

function StepRendererWrapper({ step }: { step: ToolStep }) {
  const Renderer = getToolRenderer(step);
  return <Renderer step={step} expanded={true} />;
}
