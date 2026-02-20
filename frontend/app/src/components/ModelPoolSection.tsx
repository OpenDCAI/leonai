
import { useState } from "react";

interface Model {
  id: string;
  name: string;
  custom?: boolean;
  provider?: string;
}

interface ModelPoolSectionProps {
  models: Model[];
  enabledModels: string[];
  providers: Record<string, { api_key: string | null; base_url: string | null }>;
  onToggle: (modelId: string, enabled: boolean) => void;
  onAddCustomModel: (modelId: string, provider?: string) => Promise<void>;
  onRemoveCustomModel: (modelId: string) => Promise<void>;
}

export default function ModelPoolSection({ models, enabledModels, providers, onToggle, onAddCustomModel, onRemoveCustomModel }: ModelPoolSectionProps) {
  const [toggling, setToggling] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [testStatus, setTestStatus] = useState<Record<string, "idle" | "testing" | "ok" | "fail">>({});
  const [testError, setTestError] = useState<Record<string, string>>({});
  const [selectedProvider, setSelectedProvider] = useState("");

  const handleToggle = async (modelId: string, enabled: boolean) => {
    setToggling(modelId);
    onToggle(modelId, enabled);

    try {
      await fetch("/api/settings/models/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, enabled }),
      });

      // Show success feedback
      setSuccessMessage(enabled ? "Model enabled" : "Model disabled");
      setTimeout(() => setSuccessMessage(null), 2000);
    } catch (error) {
      console.error("Failed to toggle model:", error);
    } finally {
      setToggling(null);
    }
  };

  const handleTest = async (modelId: string) => {
    setTestStatus((s) => ({ ...s, [modelId]: "testing" }));
    setTestError((s) => ({ ...s, [modelId]: "" }));
    try {
      const res = await fetch("/api/settings/models/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId }),
      });
      const data = await res.json();
      if (data.success) {
        setTestStatus((s) => ({ ...s, [modelId]: "ok" }));
      } else {
        setTestStatus((s) => ({ ...s, [modelId]: "fail" }));
        setTestError((s) => ({ ...s, [modelId]: data.error || "Unknown error" }));
      }
    } catch {
      setTestStatus((s) => ({ ...s, [modelId]: "fail" }));
      setTestError((s) => ({ ...s, [modelId]: "Network error" }));
    }
    setTimeout(() => setTestStatus((s) => ({ ...s, [modelId]: "idle" })), 5000);
  };

  const filteredModels = models.filter((model) =>
    model.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 已启用的排在前面
  const sortedModels = [...filteredModels].sort((a, b) => {
    const aEnabled = enabledModels.includes(a.id);
    const bEnabled = enabledModels.includes(b.id);
    if (aEnabled && !bEnabled) return -1;
    if (!aEnabled && bEnabled) return 1;
    return 0;
  });

  return (
    <div className="space-y-4 relative">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Model Pool
          </h2>
        </div>
        <div className="flex items-center gap-3">
          {successMessage && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#10b981]/10 rounded-full animate-fadeIn">
              <svg className="w-4 h-4 text-[#10b981]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-xs text-[#10b981] font-medium">{successMessage}</span>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0ea5e9]/10 rounded-full">
            <span className="text-xs text-[#64748b] font-medium">Active:</span>
            <span className="text-sm font-bold text-[#0ea5e9]">{enabledModels.length}</span>
            <span className="text-xs text-[#cbd5e1]">/</span>
            <span className="text-sm font-bold text-[#64748b]">{models.length}</span>
          </div>
        </div>
      </div>

      {/* Search bar with helper text */}
      <div className="space-y-2">
        <div className="relative">
          <input
            type="text"
            placeholder="Search models..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-4 pr-4 py-2.5 text-sm border-2 border-[#e2e8f0] rounded-lg bg-white text-[#1e293b] placeholder:text-[#cbd5e1] hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20 transition-all duration-200"
          />
        </div>
        <p className="text-xs text-[#94a3b8]">Enable models to use them in virtual model mappings</p>
      </div>

      {/* Model list container */}
      <div className="border border-[#e2e8f0] rounded-xl bg-white shadow-sm">
        <div style={{ maxHeight: '400px', overflowY: 'auto', overflowX: 'visible' }} className="custom-scrollbar rounded-xl">
          {sortedModels.map((model, index) => {
            const isEnabled = enabledModels.includes(model.id);
            const isToggling = toggling === model.id;

            return (
              <div
                key={model.id}
                className="group flex items-center gap-4 px-4 py-3 border-b border-[#f1f5f9] last:border-b-0 hover:bg-[#f8fafc] transition-all duration-200"
                style={{
                  animation: `slideIn 0.3s ease-out ${index * 0.02}s both`
                }}
              >
                {/* Toggle switch - MOVED TO LEFT */}
                <button
                  onClick={() => void handleToggle(model.id, !isEnabled)}
                  disabled={isToggling}
                  style={{
                    backgroundColor: isEnabled ? '#0ea5e9' : '#e2e8f0',
                    opacity: isToggling ? 0.5 : 1,
                    cursor: isToggling ? 'not-allowed' : 'pointer'
                  }}
                  className="relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/20 focus:ring-offset-2 flex-shrink-0"
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full transition-all duration-300 shadow-sm bg-white ${
                      isEnabled
                        ? "translate-x-5"
                        : "translate-x-0.5"
                    }`}
                  />
                </button>

                <span className={`text-sm font-mono transition-colors duration-200 flex-1 ${
                  isEnabled ? 'text-[#0ea5e9] font-medium' : 'text-[#64748b]'
                }`}>
                  {model.id}
                </span>
                {model.custom && (
                  <>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#f1f5f9] text-[#94a3b8] font-medium">
                      custom · {model.provider || "auto"}
                    </span>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        await onRemoveCustomModel(model.id);
                      }}
                      className="text-[11px] text-[#94a3b8] hover:text-[#ef4444] opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                    >
                      Remove
                    </button>
                  </>
                )}

                {/* Test button */}
                {(() => {
                  const status = testStatus[model.id] || "idle";
                  if (status === "testing") {
                    return <span className="text-[11px] text-[#94a3b8] animate-pulse flex-shrink-0">Testing...</span>;
                  }
                  if (status === "ok") {
                    return <span className="text-[11px] text-[#10b981] flex-shrink-0" title="Model is reachable">OK</span>;
                  }
                  if (status === "fail") {
                    return <span className="text-[11px] text-[#ef4444] flex-shrink-0" title={testError[model.id]}>Fail</span>;
                  }
                  return (
                    <button
                      onClick={(e) => { e.stopPropagation(); void handleTest(model.id); }}
                      className="text-[11px] text-[#94a3b8] hover:text-[#0ea5e9] opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                    >
                      Test
                    </button>
                  );
                })()}
              </div>
            );
          })}
        </div>
      </div>

      {filteredModels.length === 0 && searchQuery.trim() && (
        <div className="text-center py-12 px-4">
          <p className="text-sm font-medium text-[#64748b] mb-1">No models found for "{searchQuery}"</p>
          <p className="text-xs text-[#94a3b8] mb-4">You can add it as a custom model</p>
          <div className="flex items-center justify-center gap-2 mb-3">
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="h-9 px-3 text-sm border-2 border-[#e2e8f0] rounded-lg bg-white text-[#1e293b] focus:outline-none focus:border-[#0ea5e9]"
            >
              <option value="">Auto-detect provider</option>
              {Object.keys(providers).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <button
              onClick={async () => {
                setAdding(true);
                try {
                  await onAddCustomModel(searchQuery.trim(), selectedProvider || undefined);
                  setSearchQuery("");
                  setSelectedProvider("");
                  setSuccessMessage("Model added");
                  setTimeout(() => setSuccessMessage(null), 2000);
                } catch (e) {
                  console.error("Failed to add custom model:", e);
                } finally {
                  setAdding(false);
                }
              }}
              disabled={adding}
              className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-all duration-200 hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: '#0ea5e9' }}
            >
              {adding ? "Adding..." : `Add "${searchQuery.trim()}" to pool`}
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
          background: #f8fafc;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #0ea5e9;
        }
      `}</style>
    </div>
  );
}
