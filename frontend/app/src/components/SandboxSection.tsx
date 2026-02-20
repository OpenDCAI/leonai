import { Eye, EyeOff, Folder, Check } from "lucide-react";
import { useState } from "react";
import { saveSandboxConfig } from "../api";

interface SandboxSectionProps {
  sandboxes: Record<string, Record<string, unknown>>;
  defaultWorkspace: string | null;
  onUpdate: (name: string, config: Record<string, unknown>) => void;
  onWorkspaceChange: (workspace: string) => void;
}

interface FieldDef {
  key: string;
  label: string;
  type: "text" | "password" | "number" | "select";
  options?: string[];
  placeholder?: string;
  nested?: string;
}

const SANDBOX_PROVIDERS: {
  id: string;
  name: string;
  fields: FieldDef[];
}[] = [
  {
    id: "agentbay",
    name: "AgentBay",
    fields: [
      { key: "api_key", label: "API Key", type: "password", nested: "agentbay" },
      { key: "region_id", label: "Region ID", type: "text", placeholder: "ap-southeast-1", nested: "agentbay" },
      { key: "context_path", label: "Context Path", type: "text", placeholder: "/home/wuying", nested: "agentbay" },
      { key: "image_id", label: "Image ID", type: "text", nested: "agentbay" },
    ],
  },
  {
    id: "docker",
    name: "Docker",
    fields: [
      { key: "image", label: "Image", type: "text", placeholder: "python:3.12-slim", nested: "docker" },
      { key: "mount_path", label: "Mount Path", type: "text", placeholder: "/workspace", nested: "docker" },
    ],
  },
  {
    id: "e2b",
    name: "E2B",
    fields: [
      { key: "api_key", label: "API Key", type: "password", nested: "e2b" },
      { key: "template", label: "Template", type: "text", placeholder: "base", nested: "e2b" },
      { key: "cwd", label: "Working Directory", type: "text", placeholder: "/home/user", nested: "e2b" },
      { key: "timeout", label: "Timeout (s)", type: "number", nested: "e2b" },
    ],
  },
  {
    id: "daytona",
    name: "Daytona",
    fields: [
      { key: "api_key", label: "API Key", type: "password", nested: "daytona" },
      { key: "api_url", label: "API URL", type: "text", placeholder: "https://app.daytona.io/api", nested: "daytona" },
      { key: "target", label: "Target", type: "text", placeholder: "local", nested: "daytona" },
      { key: "cwd", label: "Working Directory", type: "text", placeholder: "/home/daytona", nested: "daytona" },
    ],
  },
];

const COMMON_FIELDS: FieldDef[] = [
  { key: "on_exit", label: "On Exit", type: "select", options: ["pause", "destroy"] },
  { key: "init_commands", label: "Init Commands", type: "text", placeholder: "comma-separated commands" },
];

function getNestedValue(config: Record<string, unknown>, field: FieldDef): string {
  if (field.nested) {
    const nested = config[field.nested] as Record<string, unknown> | undefined;
    return String(nested?.[field.key] ?? "");
  }
  if (field.key === "init_commands") {
    const cmds = config[field.key];
    return Array.isArray(cmds) ? cmds.join(", ") : "";
  }
  return String(config[field.key] ?? "");
}

function setNestedValue(config: Record<string, unknown>, field: FieldDef, value: string): Record<string, unknown> {
  const updated = { ...config };
  if (field.nested) {
    const nested = { ...(config[field.nested] as Record<string, unknown> || {}) };
    nested[field.key] = field.type === "number" ? (Number(value) || 0) : (value || undefined);
    updated[field.nested] = nested;
  } else if (field.key === "init_commands") {
    updated[field.key] = value ? value.split(",").map((s) => s.trim()).filter(Boolean) : [];
  } else {
    updated[field.key] = value || undefined;
  }
  return updated;
}

export default function SandboxSection({ sandboxes, defaultWorkspace, onUpdate, onWorkspaceChange }: SandboxSectionProps) {
  const [saving, setSaving] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [workspacePath, setWorkspacePath] = useState(defaultWorkspace || "");
  const [wsSaving, setWsSaving] = useState(false);
  const [wsSuccess, setWsSuccess] = useState(false);
  const [wsError, setWsError] = useState("");

  const handleWorkspaceSave = async () => {
    if (!workspacePath.trim()) return;
    setWsSaving(true);
    setWsError("");
    try {
      const res = await fetch("/api/settings/workspace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace: workspacePath.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Save failed");
      }
      const data = await res.json();
      onWorkspaceChange(data.workspace);
      setWorkspacePath(data.workspace);
      setWsSuccess(true);
      setTimeout(() => setWsSuccess(false), 2000);
    } catch (err) {
      setWsError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setWsSaving(false);
    }
  };

  const handleSave = async (providerId: string, config: Record<string, unknown>) => {
    setSaving(providerId);
    onUpdate(providerId, config);
    try {
      await saveSandboxConfig(providerId, { ...config, provider: providerId });
      setSuccessMessage(providerId);
      setTimeout(() => setSuccessMessage(null), 2000);
    } catch (error) {
      console.error("Failed to save sandbox config:", error);
    } finally {
      setSaving(null);
    }
  };

  const maskValue = (val: string) => {
    if (!val || val.length <= 8) return "*".repeat(val?.length || 0);
    return val.slice(0, 4) + "*".repeat(Math.min(val.length - 8, 20)) + val.slice(-4);
  };

  const renderField = (providerId: string, field: FieldDef, config: Record<string, unknown>) => {
    const value = getNestedValue(config, field);
    const showKeyId = `${providerId}-${field.key}`;
    const isSecret = field.type === "password";
    const showKey = showKeys[showKeyId] || false;

    if (field.type === "select") {
      return (
        <select
          value={value || field.options?.[0] || ""}
          onChange={(e) => void handleSave(providerId, setNestedValue(config, field, e.target.value))}
          className="w-full px-3 py-2 border border-[#e2e8f0] rounded-lg text-sm text-[#1e293b] bg-[#f8fafc] hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20 transition-all duration-200"
        >
          {field.options?.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    }

    return (
      <div className="relative">
        <input
          type={isSecret && !showKey ? "password" : "text"}
          value={isSecret && !showKey ? maskValue(value) : value}
          onChange={(e) => void handleSave(providerId, setNestedValue(config, field, e.target.value))}
          placeholder={field.placeholder}
          className="w-full px-3 py-2 pr-10 border border-[#e2e8f0] rounded-lg text-sm text-[#1e293b] bg-[#f8fafc] font-mono hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20 transition-all duration-200"
        />
        {isSecret && value && (
          <button
            onClick={() => setShowKeys({ ...showKeys, [showKeyId]: !showKey })}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-[#94a3b8] hover:text-[#0ea5e9] rounded transition-colors"
          >
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Default Local Folder Path */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Default Local Folder
          </h2>
        </div>

        <div className="border border-[#e2e8f0] rounded-xl p-5 bg-white hover:border-[#0ea5e9] hover:shadow-lg hover:shadow-[#0ea5e9]/10 transition-all duration-300 space-y-3">
          <label className="text-xs font-medium text-[#64748b]">Workspace Path</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Folder className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
              <input
                type="text"
                value={workspacePath}
                onChange={(e) => { setWorkspacePath(e.target.value); setWsError(""); }}
                placeholder="~/Projects or /Users/username/workspace"
                className="w-full pl-9 pr-3 py-2 border border-[#e2e8f0] rounded-lg text-sm text-[#1e293b] bg-[#f8fafc] font-mono hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20 transition-all duration-200"
                onKeyDown={(e) => { if (e.key === "Enter") void handleWorkspaceSave(); }}
              />
            </div>
            <button
              onClick={() => void handleWorkspaceSave()}
              disabled={wsSaving || !workspacePath.trim()}
              className="px-4 py-2 bg-[#0ea5e9] text-white text-sm font-medium rounded-lg hover:bg-[#0284c7] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shrink-0"
            >
              {wsSaving ? "Saving..." : "Save"}
            </button>
          </div>
          {wsSuccess && (
            <div className="flex items-center gap-2 text-xs text-[#10b981] font-medium animate-fadeIn">
              <Check className="w-4 h-4" />
              <span>Saved</span>
            </div>
          )}
          {wsError && (
            <p className="text-xs text-red-500">{wsError}</p>
          )}
          <p className="text-xs text-[#94a3b8]">
            Default folder for local agent execution. Use ~ for home directory.
          </p>
        </div>
      </div>

      {/* Sandbox Providers */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Sandbox Providers
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {SANDBOX_PROVIDERS.map((provider, index) => {
            const config = (sandboxes[provider.id] || {}) as Record<string, unknown>;
            const isSaving = saving === provider.id;

            return (
              <div
                key={provider.id}
                className="border border-[#e2e8f0] rounded-xl p-5 bg-white hover:border-[#0ea5e9] hover:shadow-lg hover:shadow-[#0ea5e9]/10 transition-all duration-300 space-y-4"
                style={{ animation: `fadeInUp 0.5s ease-out ${index * 0.1}s both` }}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                    {provider.name}
                  </h3>
                  {isSaving && (
                    <span className="text-xs text-[#0ea5e9] font-medium animate-pulse">Saving...</span>
                  )}
                  {successMessage === provider.id && !isSaving && (
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-[#10b981]/10 rounded-full animate-fadeIn">
                      <svg className="w-4 h-4 text-[#10b981]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-xs text-[#10b981] font-medium">Saved</span>
                    </div>
                  )}
                </div>

                {provider.fields.map((field) => (
                  <div key={field.key} className="space-y-1">
                    <label className="text-xs font-medium text-[#64748b]">{field.label}</label>
                    {renderField(provider.id, field, config)}
                  </div>
                ))}

                {COMMON_FIELDS.map((field) => (
                  <div key={field.key} className="space-y-1">
                    <label className="text-xs font-medium text-[#64748b]">{field.label}</label>
                    {renderField(provider.id, field, config)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
