import { ExternalLink, Terminal } from "lucide-react";

interface TaskProgressProps {
  isStreaming: boolean;
  sandboxType: string | null;
  sandboxStatus: string | null;
  onOpenComputer?: () => void;
}

function statusTone(status: string | null): string {
  if (status === "running") return "bg-green-500";
  if (status === "paused") return "bg-yellow-500";
  if (status === "detached") return "bg-gray-500";
  return "bg-red-500";
}

export default function TaskProgress({ isStreaming, sandboxType, sandboxStatus, onOpenComputer }: TaskProgressProps) {
  return (
    <div className="bg-[#1a1a1a]">
      <div className="max-w-3xl mx-auto px-4">
        <div className="px-2 py-2">
          <div className="w-full flex items-center gap-3 p-2.5 rounded-lg bg-[#1e1e1e] border border-[#333]">
            <div className="w-7 h-7 rounded-lg bg-[#2a2a2a] flex items-center justify-center flex-shrink-0">
              <Terminal className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full ${statusTone(sandboxStatus)}`} />
                <span className="text-gray-200">
                  {sandboxType ?? "local"} {sandboxStatus ?? "unknown"}
                </span>
                <span className="text-gray-500">·</span>
                <span className={`${isStreaming ? "text-blue-400" : "text-gray-400"}`}>
                  Agent {isStreaming ? "running" : "idle"}
                </span>
              </div>
            </div>
            <button
              onClick={onOpenComputer}
              className="px-2.5 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-xs transition-colors flex items-center justify-center gap-1.5"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
