import { memo } from "react";
import type { AssistantTurn, StreamStatus, ToolSegment } from "../../api";
import MarkdownContent from "../MarkdownContent";
import { CopyButton } from "./CopyButton";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ToolDetailBox } from "./ToolDetailBox";
import { formatTime } from "./utils";

/** Tools whose results are self-contained content that the AI often echoes verbatim. */
const CONTENT_HEAVY_TOOLS = new Set([
  "WebFetch", "web_search", "WebSearch", "read_url_content",
  "load_skill",
  "Task",
]);

/** Check if text substantially duplicates a content-heavy tool's result. */
function isToolResultEcho(text: string, toolSegs: ToolSegment[]): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 100) return false;

  for (const seg of toolSegs) {
    if (!CONTENT_HEAVY_TOOLS.has(seg.step.name)) continue;
    const result = seg.step.result?.trim();
    if (!result || result.length < 100) continue;

    const resultSample = result.slice(0, 200);
    if (trimmed.includes(resultSample)) return true;

    const textSample = trimmed.slice(0, 200);
    if (result.includes(textSample)) return true;
  }

  return false;
}

interface AssistantBlockProps {
  entry: AssistantTurn;
  isStreamingThis?: boolean;
  runtimeStatus?: StreamStatus | null;
  onFocusStep?: (stepId: string) => void;
}

export const AssistantBlock = memo(function AssistantBlock({ entry, isStreamingThis, runtimeStatus, onFocusStep }: AssistantBlockProps) {
  const fullText = entry.segments
    .filter((s) => s.type === "text")
    .map((s) => s.content)
    .join("\n");

  const toolSegs = entry.segments.filter((s) => s.type === "tool") as ToolSegment[];
  const textSegs = entry.segments.filter((s) => s.type === "text" && s.content.trim());
  const finalText = textSegs.length > 0 ? textSegs[textSegs.length - 1] : null;

  // Suppress finalText when it echoes a content-heavy tool's result (completed turns only)
  const resultEcho = !isStreamingThis && finalText != null && isToolResultEcho(finalText.content, toolSegs);
  const visibleText = resultEcho ? null : finalText;

  const hasVisible = toolSegs.length > 0 || textSegs.length > 0;

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
        </div>

        {isStreamingThis && !hasVisible && (
          <ThinkingIndicator runtimeStatus={runtimeStatus} />
        )}

        {toolSegs.length > 0 && (
          <ToolDetailBox
            toolSegments={toolSegs}
            isStreaming={!!isStreamingThis}
            onFocusStep={onFocusStep}
          />
        )}

        {visibleText && (isStreamingThis
          ? <div className="text-[13px] leading-[1.55] text-[#404040] whitespace-pre-wrap">{visibleText.content}</div>
          : <MarkdownContent content={visibleText.content} />
        )}

        {!isStreamingThis && visibleText && fullText.trim() && (
          <div className="flex justify-start mt-0.5">
            <CopyButton text={fullText} />
          </div>
        )}
      </div>
    </div>
  );
});
