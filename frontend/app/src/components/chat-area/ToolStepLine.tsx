import { ChevronDown, ChevronRight, ExternalLink, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { memo, useEffect, useState } from "react";
import type { ToolSegment } from "../../api";
import { getToolRenderer } from "../tool-renderers";
import { DEFAULT_BADGE, TOOL_BADGE_STYLES } from "./constants";

interface ToolStepLineProps {
  seg: ToolSegment;
  onFocusAgent?: (stepId: string) => void;
  onFocusStep?: (stepId: string) => void;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "calling":
      return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />;
    case "done":
      return <CheckCircle2 className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
    case "error":
      return <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />;
    case "cancelled":
      return <XCircle className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
    default:
      return <CheckCircle2 className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
  }
}

export const ToolStepLine = memo(function ToolStepLine({
  seg,
  onFocusAgent,
  onFocusStep,
}: ToolStepLineProps) {
  const { step } = seg;
  const isCalling = step.status === "calling";
  const isWriteTool = step.name === "Write" || step.name === "write_file";
  const isTaskTool = step.name === "Task";

  const [expanded, setExpanded] = useState(isWriteTool && isCalling);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    if (isWriteTool) {
      setExpanded(isCalling);
    }
  }, [isWriteTool, isCalling]);

  const Renderer = getToolRenderer(step);
  const badge = TOOL_BADGE_STYLES[step.name] ?? { ...DEFAULT_BADGE, label: step.name };

  // Task tool: click navigates to agent panel
  if (isTaskTool) {
    return (
      <div
        className="flex items-center gap-1.5 py-0.5 cursor-pointer group animate-fade-in"
        onClick={() => onFocusAgent?.(step.id)}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <StatusIcon status={step.status} />
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}
        >
          {badge.label}
        </span>
        <div className={`flex-1 min-w-0 text-sm text-gray-700 ${isCalling ? "tool-shimmer" : ""}`}>
          <Renderer step={step} expanded={false} />
        </div>
        <ChevronRight
          className={`w-3.5 h-3.5 flex-shrink-0 transition-colors ${
            hovered ? "text-gray-500" : "text-gray-300"
          }`}
        />
      </div>
    );
  }

  // All other tools: click to toggle expand/collapse
  return (
    <div
      className="animate-fade-in"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        role="button"
        tabIndex={0}
        className="flex items-center gap-1.5 py-0.5 cursor-pointer group"
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((v) => !v);
          }
        }}
      >
        <StatusIcon status={step.status} />
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}
        >
          {badge.label}
        </span>
        <div className={`flex-1 min-w-0 text-sm text-gray-700 ${isCalling ? "tool-shimmer" : ""}`}>
          <Renderer step={step} expanded={false} />
        </div>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
        )}
        {hovered && onFocusStep && (
          <button
            type="button"
            className="p-0.5 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onFocusStep(step.id);
            }}
          >
            <ExternalLink className="w-3 h-3 text-gray-400" />
          </button>
        )}
      </div>
      {expanded && (
        <div className="ml-5 pl-3 border-l border-gray-200 mt-0.5 mb-1 animate-scale-in">
          <Renderer step={step} expanded={true} />
          {step.status === "cancelled" && (
            <div className="text-xs text-gray-500 mt-1 italic">
              {step.result || "Cancelled"}
            </div>
          )}
        </div>
      )}
    </div>
  );
});
