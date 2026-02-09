import { Eye } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { file_path?: string; limit?: number; offset?: number } {
  if (args && typeof args === "object") return args as { file_path?: string; limit?: number; offset?: number };
  return {};
}

export default function ReadFileRenderer({ step, expanded }: ToolRendererProps) {
  const { file_path, limit, offset } = parseArgs(step.args);
  const shortPath = file_path?.split("/").slice(-2).join("/") ?? "file";
  const rangeHint = limit ? `行 ${offset ?? 1}-${(offset ?? 1) + limit}` : "";

  return (
    <>
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <Eye className="w-3 h-3 text-violet-500" />
        <span className="font-medium text-[#525252]">读取文件</span>
        <span className="text-[#a3a3a3] truncate max-w-[200px]">{shortPath}</span>
        {rangeHint && <span className="text-[#d4d4d4]">{rangeHint}</span>}
        {step.status === "calling" && <span className="text-[#a3a3a3] animate-pulse-slow">读取中...</span>}
      </div>
      {expanded && step.result && (
        <div className="mt-2">
          <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
            {step.result}
          </pre>
        </div>
      )}
    </>
  );
}
