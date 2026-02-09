import { Search } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { pattern?: string; path?: string; glob?: string } {
  if (args && typeof args === "object") return args as { pattern?: string; path?: string; glob?: string };
  return {};
}

export default function SearchRenderer({ step, expanded }: ToolRendererProps) {
  const { pattern, path, glob: globPattern } = parseArgs(step.args);
  const query = pattern || globPattern || "";

  return (
    <>
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <Search className="w-3 h-3 text-cyan-500" />
        <span className="font-medium text-[#525252]">搜索</span>
        {query && <code className="text-[10px] px-1.5 py-0.5 rounded bg-[#f5f5f5] border border-[#e5e5e5] text-[#525252]">{query}</code>}
        {path && <span className="text-[#a3a3a3] truncate max-w-[140px]">{path}</span>}
        {step.status === "calling" && <span className="text-[#a3a3a3] animate-pulse-slow">搜索中...</span>}
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
