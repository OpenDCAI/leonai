import { useState } from "react";
import { X, Circle, Eye, EyeOff, Copy, Shield } from "lucide-react";
import { toast } from "sonner";

interface Props {
  mcp: { id: string; name: string; desc: string; category: string };
  onClose: () => void;
}

const mockCredentials = [
  { label: "API Key", value: "sk-proj-abc123...xyz789", masked: true },
  { label: "Access Token", value: "ghp_1234567890abcdef", masked: true },
];

const mockScopes = ["repo:read", "repo:write", "issues:read", "pull_requests:write"];

export default function MCPDetail({ mcp, onClose }: Props) {
  const [connected, setConnected] = useState(mcp.id === "1");
  const [revealed, setRevealed] = useState<Set<number>>(new Set());

  const toggleReveal = (i: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const handleCopy = (value: string) => {
    navigator.clipboard.writeText(value);
    toast.success("已复制到剪贴板");
  };

  return (
    <div className="w-[400px] shrink-0 border-l border-border bg-card flex flex-col overflow-hidden">
      <div className="h-12 flex items-center justify-between px-4 border-b border-border shrink-0">
        <h3 className="text-sm font-semibold text-foreground">{mcp.name}</h3>
        <button onClick={onClose} className="p-1 rounded-md hover:bg-muted transition-colors">
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <p className="text-sm text-muted-foreground">{mcp.desc}</p>

        {/* Connection status */}
        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
          <div className="flex items-center gap-2">
            <Circle className={`w-2.5 h-2.5 ${connected ? "fill-success text-success" : "fill-muted-foreground text-muted-foreground"}`} />
            <span className="text-sm text-foreground">{connected ? "已连接" : "未连接"}</span>
          </div>
          <button
            onClick={() => setConnected(!connected)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              connected
                ? "bg-destructive/10 text-destructive hover:bg-destructive/20"
                : "bg-primary text-primary-foreground hover:opacity-90"
            }`}
          >
            {connected ? "断开连接" : "连接"}
          </button>
        </div>

        {/* Credentials */}
        {connected && (
          <div>
            <p className="text-xs font-medium text-foreground mb-2">凭证</p>
            <div className="space-y-2">
              {mockCredentials.map((cred, i) => (
                <div key={i} className="rounded-lg border border-border p-3">
                  <p className="text-[11px] text-muted-foreground mb-1.5">{cred.label}</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs font-mono text-foreground bg-background px-2 py-1.5 rounded border border-border truncate">
                      {revealed.has(i) ? cred.value : "••••••••••••••••••••"}
                    </code>
                    <button onClick={() => toggleReveal(i)} className="p-1.5 rounded hover:bg-muted transition-colors" title={revealed.has(i) ? "隐藏" : "显示"}>
                      {revealed.has(i) ? <EyeOff className="w-3.5 h-3.5 text-muted-foreground" /> : <Eye className="w-3.5 h-3.5 text-muted-foreground" />}
                    </button>
                    <button onClick={() => handleCopy(cred.value)} className="p-1.5 rounded hover:bg-muted transition-colors" title="复制">
                      <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scopes */}
        <div>
          <p className="text-xs font-medium text-foreground mb-2 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-muted-foreground" />
            权限范围
          </p>
          <div className="flex flex-wrap gap-1.5">
            {mockScopes.map((scope) => (
              <span key={scope} className="px-2 py-1 rounded bg-muted text-xs font-mono text-muted-foreground">
                {scope}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
