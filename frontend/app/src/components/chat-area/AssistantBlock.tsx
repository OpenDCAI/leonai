import { ExternalLink } from "lucide-react";
import { memo } from "react";
import type { AssistantTurn, StreamStatus } from "../../api";
import MarkdownContent from "../MarkdownContent";
import { CopyButton } from "./CopyButton";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ToolStepLine } from "./ToolStepLine";
import { formatTime } from "./utils";

interface AssistantBlockProps {
  entry: AssistantTurn;
  isStreamingThis?: boolean;
  runtimeStatus?: StreamStatus | null;
  onFocusAgent?: (stepId: string) => void;
  onFocusStep?: (stepId: string) => void;
}

export const AssistantBlock = memo(function AssistantBlock({ entry, isStreamingThis, runtimeStatus, onFocusAgent, onFocusStep }: AssistantBlockProps) {
  const fullText = entry.segments
    .filter((s) => s.type === "text")
    .map((s) => s.content)
    .join("\n");

  const hasVisible = entry.segments.some((s) => {
    if (s.type === "text") return s.content.trim().length > 0;
    return s.type === "tool";
  });

  // First tool step id for block-level "view in panel" jump
  const firstToolStepId = entry.segments.find((s) => s.type === "tool")?.step?.id ?? null;
  const hasTools = firstToolStepId !== null;

  if (!hasVisible && !isStreamingThis) return null;

  return (
    <div className="flex gap-2.5 animate-fade-in group/block">
      <div className="w-6 h-6 rounded-full bg-[#171717] flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-[11px] font-semibold text-white">L</span>
      </div>
      <div className="flex-1 max-w-[calc(100%-36px)] space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-[#171717]">Leon</span>
          {entry.timestamp && (
            <span className="text-[10px] text-[#d4d4d4]">{formatTime(entry.timestamp)}</span>
          )}
          {!isStreamingThis && hasTools && onFocusStep && (
            <button
              className="opacity-0 group-hover/block:opacity-100 p-0.5 hover:bg-[#f0f0f0] rounded transition-opacity"
              onClick={() => onFocusStep(firstToolStepId!)}
              title="在面板中查看细节"
            >
              <ExternalLink className="w-3 h-3 text-[#a3a3a3]" />
            </button>
          )}
        </div>

        {isStreamingThis && !hasVisible && (
          <ThinkingIndicator runtimeStatus={runtimeStatus} />
        )}

        {entry.segments.map((seg, i) => {
          if (seg.type === "text" && seg.content.trim()) {
            if (isStreamingThis) {
              return (
                <div key={`seg-${i}`} className="text-[13px] leading-[1.55] text-[#404040] whitespace-pre-wrap">
                  {seg.content}
                </div>
              );
            }
            return <MarkdownContent key={`seg-${i}`} content={seg.content} />;
          }
          if (seg.type === "tool") {
            return <ToolStepLine key={seg.step.id} seg={seg} onFocusAgent={onFocusAgent} />;
          }
          return null;
        })}

        {!isStreamingThis && fullText.trim() && (
          <div className="flex justify-start mt-0.5">
            <CopyButton text={fullText} />
          </div>
        )}
      </div>
    </div>
  );
});
