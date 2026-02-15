import { ChevronDown, ChevronRight } from "lucide-react";
import { memo, useEffect, useState } from "react";
import type { ToolSegment } from "../../api";
import { getToolRenderer } from "../tool-renderers";
import { DEFAULT_BADGE, TOOL_BADGE_STYLES } from "./constants";

interface ToolStepBlockProps {
  seg: ToolSegment;
  onFocusAgent?: (stepId: string) => void;
}

export const ToolStepBlock = memo(function ToolStepBlock({ seg, onFocusAgent }: ToolStepBlockProps) {
  const isCalling = seg.step.status === "calling";
  const isCancelled = seg.step.status === "cancelled";
  const isWriteTool = seg.step.name === "Write" || seg.step.name === "write_file";

  // Auto-expand write_file when calling, collapse when done
  const [expanded, setExpanded] = useState(isWriteTool && isCalling);

  // Update expanded state when status changes
  useEffect(() => {
    if (isWriteTool) {
      setExpanded(isCalling);
    }
  }, [isWriteTool, isCalling]);

  const Renderer = getToolRenderer(seg.step);
  const badge = TOOL_BADGE_STYLES[seg.step.name] ?? { ...DEFAULT_BADGE, label: seg.step.name };

  // Task (sub-agent) gets a clickable card that opens the Agents panel
  if (seg.step.name === "Task") {
    return (
      <div
        className={`rounded-lg border bg-white animate-fade-in cursor-pointer hover:border-[#a3a3a3] transition-colors ${
          isCalling ? "tool-card-calling border-[#d4d4d4]" : isCancelled ? "border-gray-300 opacity-60" : "border-[#e5e5e5]"
        }`}
        onClick={() => onFocusAgent?.(seg.step.id)}
      >
        <div className="flex items-center gap-1.5 w-full text-left px-2.5 py-1.5">
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          <div className={`flex-1 min-w-0 ${isCalling ? "tool-shimmer" : ""}`}>
            <Renderer step={seg.step} expanded={false} />
          </div>
          {isCancelled && (
            <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-[10px] font-medium">已取消</span>
          )}
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0">
            <polyline points="6,3 11,8 6,13" />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border bg-white animate-fade-in ${
        isCalling ? "tool-card-calling border-[#d4d4d4]" : isCancelled ? "border-gray-300 opacity-60" : "border-[#e5e5e5]"
      }`}
    >
      <div
        role="button"
        tabIndex={0}
        className="flex items-center gap-1.5 w-full text-left px-2.5 py-1.5 hover:bg-[#fafafa] rounded-lg transition-colors"
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((v) => !v);
          }
        }}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        )}
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}>
          {badge.label}
        </span>
        <div className={`flex-1 min-w-0 ${isCalling ? "tool-shimmer" : ""}`}>
          <Renderer step={seg.step} expanded={false} />
        </div>
        {isCancelled && (
          <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-[10px] font-medium">Cancelled</span>
        )}
      </div>
      {expanded && (
        <div className="px-2.5 pb-2.5 pt-0 animate-scale-in">
          <Renderer step={seg.step} expanded={true} />
          {isCancelled && (
            <div className="text-xs text-gray-500 mt-2 italic">
              {seg.step.result || "任务被用户取消"}
            </div>
          )}
        </div>
      )}
    </div>
  );
});
