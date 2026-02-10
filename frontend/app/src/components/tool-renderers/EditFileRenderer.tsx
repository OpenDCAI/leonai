import { Pencil } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { file_path?: string; old_string?: string; new_string?: string } {
  if (args && typeof args === "object") return args as { file_path?: string; old_string?: string; new_string?: string };
  return {};
}

export default function EditFileRenderer({ step, expanded }: ToolRendererProps) {
  const { file_path, old_string, new_string } = parseArgs(step.args);
  const shortPath = file_path?.split("/").filter(Boolean).pop() ?? "file";

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <Pencil className="w-3 h-3 text-amber-500 flex-shrink-0" />
        <span className="font-medium text-[#525252]">编辑文件</span>
        <span className="text-[#a3a3a3] truncate max-w-[200px]">{shortPath}</span>
        {step.status === "calling" && <span className="text-[#a3a3a3]">...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {old_string && (
        <div className="rounded-lg overflow-hidden border border-[#e5e5e5]">
          <div className="px-3 py-1.5 bg-red-50 text-[10px] font-medium text-red-400 border-b border-[#e5e5e5]">删除</div>
          <pre className="p-3 text-xs overflow-x-auto max-h-[120px] overflow-y-auto font-mono bg-red-50/30 text-red-700">
            {old_string}
          </pre>
        </div>
      )}
      {new_string && (
        <div className="rounded-lg overflow-hidden border border-[#e5e5e5]">
          <div className="px-3 py-1.5 bg-green-50 text-[10px] font-medium text-green-500 border-b border-[#e5e5e5]">新增</div>
          <pre className="p-3 text-xs overflow-x-auto max-h-[120px] overflow-y-auto font-mono bg-green-50/30 text-green-700">
            {new_string}
          </pre>
        </div>
      )}
      {step.result && (
        <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[100px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
          {step.result}
        </pre>
      )}
    </div>
  );
}
