import { FolderOpen } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { path?: string; dir_path?: string } {
  if (args && typeof args === "object") return args as { path?: string; dir_path?: string };
  return {};
}

export default function ListDirRenderer({ step, expanded }: ToolRendererProps) {
  const { path, dir_path } = parseArgs(step.args);
  const dirPath = path || dir_path || ".";
  const shortPath = dirPath.split("/").filter(Boolean).pop() || dirPath;

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
        <FolderOpen className="w-3 h-3 text-[#d4d4d4] flex-shrink-0" />
        <span>浏览目录 {shortPath}</span>
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
