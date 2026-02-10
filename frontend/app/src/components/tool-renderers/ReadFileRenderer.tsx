import { memo } from "react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { file_path?: string; limit?: number; offset?: number } {
  if (args && typeof args === "object") return args as { file_path?: string; limit?: number; offset?: number };
  return {};
}

export default memo(function ReadFileRenderer({ step, expanded }: ToolRendererProps) {
  const { file_path, limit, offset } = parseArgs(step.args);
  const shortPath = file_path?.split("/").filter(Boolean).pop() ?? "file";
  const rangeHint = offset && limit ? ` L${offset}-${offset + limit}` : limit ? ` L1-${limit}` : "";

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <span className="text-[#525252]">读取</span>
        <code className="font-mono text-[#737373] truncate max-w-[280px]">{file_path ?? shortPath}</code>
        {rangeHint && <span className="text-[#a3a3a3]">{rangeHint}</span>}
        {step.status === "calling" && <span className="text-[#a3a3a3]">...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {step.result && (
        <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
          {step.result}
        </pre>
      )}
    </div>
  );
});
