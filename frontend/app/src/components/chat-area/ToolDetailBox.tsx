import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { memo, useEffect, useRef } from "react";
import type { ToolSegment } from "../../api";
import { DEFAULT_BADGE, TOOL_BADGE_STYLES } from "./constants";
import { getStepSummary } from "./utils";

interface ToolDetailBoxProps {
  toolSegments: ToolSegment[];
  isStreaming: boolean;
  onFocusStep?: (stepId: string) => void;
}

function MiniStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "calling":
      return <Loader2 className="w-3 h-3 text-blue-500 animate-spin flex-shrink-0" />;
    case "done":
      return <CheckCircle2 className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />;
    case "error":
      return <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />;
    case "cancelled":
      return <XCircle className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />;
    default:
      return <CheckCircle2 className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />;
  }
}

export const ToolDetailBox = memo(function ToolDetailBox({
  toolSegments,
  isStreaming,
  onFocusStep,
}: ToolDetailBoxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [toolSegments.length]);

  const firstStepId = toolSegments[0]?.step.id;
  const hasRunning = toolSegments.some((s) => s.step.status === "calling");

  return (
    <div
      className={`rounded-lg border bg-[#fafafa] cursor-pointer transition-colors ${
        hasRunning ? "detail-box-glow" : "border-[#e5e5e5] hover:border-[#d4d4d4]"
      }`}
      onClick={() => firstStepId && onFocusStep?.(firstStepId)}
      title="点击查看详情"
    >
      <div
        ref={scrollRef}
        className="relative z-[1] max-h-[80px] overflow-y-auto detail-box-scroll detail-box-mask px-2.5 py-1.5"
      >
        <div className="flex flex-col gap-0.5">
          {toolSegments.map((seg) => {
            const { step } = seg;
            const badge = TOOL_BADGE_STYLES[step.name] ?? { ...DEFAULT_BADGE, label: step.name };
            const isCalling = step.status === "calling";

            return (
              <div
                key={step.id}
                className="flex items-center gap-1.5 h-6 min-w-0 animate-fade-in"
              >
                <MiniStatusIcon status={step.status} />
                <span
                  className={`inline-flex items-center px-1 py-0 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}
                >
                  {badge.label || step.name}
                </span>
                <span
                  className={`text-[11px] text-[#737373] font-mono truncate min-w-0 ${isCalling ? "animate-pulse-slow" : ""}`}
                >
                  {getStepSummary(step)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});
