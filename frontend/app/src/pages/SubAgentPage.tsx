import { useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Bot, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import ChatArea from "@/components/ChatArea";
import { useThreadData } from "@/hooks/use-thread-data";
import type { ChatEntry, AssistantTurn } from "@/api";

type AgentStatus = "running" | "completed" | "error" | "unknown";

function inferStatus(entries: ChatEntry[], loading: boolean): AgentStatus {
  if (loading) return "unknown";
  if (entries.length === 0) return "running";
  const last = entries[entries.length - 1];
  if (last.role === "assistant") {
    const turn = last as AssistantTurn;
    if (turn.streaming) return "running";
    const hasError = turn.segments.some(
      (s) => s.type === "tool" && s.step.status === "error",
    );
    if (hasError) return "error";
    return "completed";
  }
  if (last.role === "notice") {
    const content = last.content.toLowerCase();
    if (content.includes("error") || content.includes("failed")) return "error";
    if (content.includes("completed") || content.includes("done")) return "completed";
  }
  return "running";
}

const STATUS_CONFIG: Record<AgentStatus, { label: string; className: string; icon: typeof Loader2 | null }> = {
  running: { label: "Running", className: "bg-blue-100 text-blue-700", icon: Loader2 },
  completed: { label: "Completed", className: "bg-green-100 text-green-700", icon: CheckCircle2 },
  error: { label: "Error", className: "bg-red-100 text-red-700", icon: XCircle },
  unknown: { label: "Loading", className: "bg-gray-100 text-gray-500", icon: null },
};

export default function SubAgentPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const threadId = `subagent_${taskId}`;
  const { entries, loading, refreshThread } = useThreadData(threadId);

  const status = inferStatus(entries, loading);

  // Auto-refresh while running
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (status === "running") {
      intervalRef.current = setInterval(() => {
        void refreshThread();
      }, 2000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [status, refreshThread]);

  const handleNavigateAgent = useCallback(
    (id: string) => navigate(`/agents/${id}`),
    [navigate],
  );

  const statusCfg = STATUS_CONFIG[status];
  const StatusIcon = statusCfg.icon;

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b shrink-0">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Bot className="h-5 w-5 text-primary" />
        <span className="font-medium text-sm font-mono">Task {taskId}</span>
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${statusCfg.className}`}>
          {StatusIcon && <StatusIcon className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />}
          {statusCfg.label}
        </span>
      </div>

      {/* Chat area */}
      <ChatArea
        entries={entries}
        isStreaming={status === "running"}
        runtimeStatus={null}
        loading={loading}
        onNavigateAgent={handleNavigateAgent}
      />
    </div>
  );
}
