import { useState } from "react";

interface VirtualModel {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface Model {
  id: string;
  name: string;
}

interface ModelMappingValue {
  model: string;
  alias?: string | null;
  context_limit?: number | null;
}

interface ModelMappingSectionProps {
  virtualModels: VirtualModel[];
  availableModels: Model[];
  modelMapping: Record<string, ModelMappingValue>;
  enabledModels: string[];
  onUpdate: (mapping: Record<string, ModelMappingValue>) => void;
}

export default function ModelMappingSection({
  virtualModels,
  availableModels,
  modelMapping,
  enabledModels,
  onUpdate,
}: ModelMappingSectionProps) {
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState(false);

  const saveMapping = async (newMapping: Record<string, ModelMappingValue>) => {
    onUpdate(newMapping);
    setSaving(true);
    try {
      await fetch("/api/settings/model-mapping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mapping: newMapping }),
      });
      setSuccessMessage(true);
      setTimeout(() => setSuccessMessage(false), 2000);
    } catch (error) {
      console.error("Failed to save mapping:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleMappingChange = async (virtualId: string, modelId: string) => {
    const prev = modelMapping[virtualId] || { model: "" };
    const newMapping = { ...modelMapping, [virtualId]: { ...prev, model: modelId } };
    await saveMapping(newMapping);
  };

  const handleFieldChange = async (virtualId: string, field: "alias" | "context_limit", value: string) => {
    const prev = modelMapping[virtualId] || { model: "" };
    const parsed = field === "context_limit" ? (value ? Number(value) : null) : (value || null);
    const newMapping = { ...modelMapping, [virtualId]: { ...prev, [field]: parsed } };
    await saveMapping(newMapping);
  };

  const enabledModelsList = availableModels.filter((m) => enabledModels.includes(m.id));

  return (
    <div className="space-y-4 relative">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Virtual Models
          </h2>
        </div>
        {saving && (
          <span className="text-xs text-[#0ea5e9] font-medium animate-pulse">Syncing...</span>
        )}
        {successMessage && !saving && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#10b981]/10 rounded-full animate-fadeIn">
            <svg className="w-4 h-4 text-[#10b981]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-xs text-[#10b981] font-medium">Saved</span>
          </div>
        )}
      </div>

      {/* Virtual models grid */}
      <div className="grid grid-cols-2 gap-4">
        {virtualModels.map((vm, index) => {
          const entry = modelMapping[vm.id] || { model: "" };
          const currentModel = entry.model || "";
          return (
            <div
              key={vm.id}
              className="group relative border border-[#e2e8f0] rounded-xl p-5 bg-white hover:border-[#0ea5e9] hover:shadow-lg hover:shadow-[#0ea5e9]/10 transition-all duration-300"
              style={{
                animation: `fadeInUp 0.5s ease-out ${index * 0.1}s both`
              }}
            >
              {/* Gradient overlay on hover */}
              <div className="absolute inset-0 bg-gradient-to-br from-[#0ea5e9]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />

              <div className="relative flex items-start gap-3 mb-4">
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                    {vm.name}
                  </h3>
                  <p className="text-xs text-[#64748b] mt-1">{vm.description}</p>
                </div>
              </div>

              {enabledModelsList.length === 0 ? (
                <div className="w-full px-3 py-2.5 border border-[#e2e8f0] rounded-lg text-sm bg-[#f8fafc] text-[#94a3b8] flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Enable models in Model Pool section below</span>
                </div>
              ) : (
                <>
                <select
                  value={currentModel}
                  onChange={(e) => void handleMappingChange(vm.id, e.target.value)}
                  className="relative w-full px-3 py-2.5 border border-[#e2e8f0] rounded-lg text-sm text-[#1e293b] bg-[#f8fafc] font-mono hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20 transition-all duration-200"
                >
                  {!currentModel && <option value="">Select model...</option>}
                  {enabledModelsList.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.id}
                    </option>
                  ))}
                </select>
                <div className="relative flex gap-2 mt-2">
                  <input
                    type="text"
                    placeholder="alias (e.g. claude-sonnet-4.5)"
                    value={entry.alias || ""}
                    onBlur={(e) => void handleFieldChange(vm.id, "alias", e.target.value)}
                    onChange={(e) => {
                      const newMapping = { ...modelMapping, [vm.id]: { ...entry, alias: e.target.value || null } };
                      onUpdate(newMapping);
                    }}
                    className="flex-1 px-2 py-1.5 border border-[#e2e8f0] rounded-lg text-xs text-[#475569] bg-[#f8fafc] font-mono placeholder:text-[#cbd5e1] hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-1 focus:ring-[#0ea5e9]/20 transition-all duration-200"
                  />
                  <input
                    type="number"
                    placeholder="context limit"
                    value={entry.context_limit ?? ""}
                    onBlur={(e) => void handleFieldChange(vm.id, "context_limit", e.target.value)}
                    onChange={(e) => {
                      const val = e.target.value ? Number(e.target.value) : null;
                      const newMapping = { ...modelMapping, [vm.id]: { ...entry, context_limit: val } };
                      onUpdate(newMapping);
                    }}
                    className="w-28 px-2 py-1.5 border border-[#e2e8f0] rounded-lg text-xs text-[#475569] bg-[#f8fafc] font-mono placeholder:text-[#cbd5e1] hover:border-[#0ea5e9] focus:outline-none focus:border-[#0ea5e9] focus:ring-1 focus:ring-[#0ea5e9]/20 transition-all duration-200"
                  />
                </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
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
      `}</style>
    </div>
  );
}
