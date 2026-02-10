import { memo } from "react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { file_path?: string; old_string?: string; new_string?: string } {
  if (args && typeof args === "object") return args as { file_path?: string; old_string?: string; new_string?: string };
  return {};
}

export default memo(function EditFileRenderer({ step, expanded }: ToolRendererProps) {
  const { file_path, old_string, new_string } = parseArgs(step.args);
  const shortPath = file_path?.split("/").filter(Boolean).pop() ?? "file";

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <span className="text-[#525252]">编辑</span>
        <code className="font-mono text-[#737373] truncate max-w-[280px]">{file_path ?? shortPath}</code>
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
});
