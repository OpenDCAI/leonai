import { Search } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { pattern?: string; path?: string; glob?: string } {
  if (args && typeof args === "object") return args as { pattern?: string; path?: string; glob?: string };
  return {};
}

export default function SearchRenderer({ step, expanded }: ToolRendererProps) {
  const { pattern, path, glob: globPattern } = parseArgs(step.args);
  const query = pattern || globPattern || "";
  const shortPath = path?.split("/").filter(Boolean).pop() ?? "";

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
        <Search className="w-3 h-3 text-[#d4d4d4] flex-shrink-0" />
        <span>搜索 {query}{shortPath ? ` in ${shortPath}` : ""}</span>
        {step.status === "calling" && <span>...</span>}
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
}
