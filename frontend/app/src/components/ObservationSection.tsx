import { Eye, EyeOff, Check, AlertCircle, Loader2 } from "lucide-react";
import { useState } from "react";
import { saveObservationConfig, verifyObservation } from "../api";

interface ObservationSectionProps {
  config: Record<string, unknown>;
  onUpdate: (config: Record<string, unknown>) => void;
}

interface FieldDef {
  key: string;
  label: string;
  type: "text" | "password";
  placeholder?: string;
  nested: string;
}

const OBSERVATION_PROVIDERS: {
  id: string;
  name: string;
  fields: FieldDef[];
}[] = [
  {
    id: "langfuse",
    name: "Langfuse",
    fields: [
      { key: "secret_key", label: "Secret Key", type: "password", nested: "langfuse" },
      { key: "public_key", label: "Public Key", type: "password", nested: "langfuse" },
      { key: "host", label: "Host", type: "text", placeholder: "https://cloud.langfuse.com", nested: "langfuse" },
    ],
  },
  {
    id: "langsmith",
    name: "LangSmith",
    fields: [
      { key: "api_key", label: "API Key", type: "password", nested: "langsmith" },
      { key: "project", label: "Project", type: "text", placeholder: "default", nested: "langsmith" },
      { key: "endpoint", label: "Endpoint", type: "text", placeholder: "https://api.smith.langchain.com", nested: "langsmith" },
    ],
  },
];

function getNestedValue(config: Record<string, unknown>, field: FieldDef): string {
  const nested = config[field.nested] as Record<string, unknown> | undefined;
  return String(nested?.[field.key] ?? "");
}

function setNestedValue(config: Record<string, unknown>, field: FieldDef, value: string): Record<string, unknown> {
  const updated = { ...config };
  const nested = { ...((config[field.nested] as Record<string, unknown>) || {}) };
  nested[field.key] = value || undefined;
  updated[field.nested] = nested;
  return updated;
}

export default function ObservationSection({ config, onUpdate }: ObservationSectionProps) {
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ success: boolean; error?: string; traces?: unknown[] } | null>(null);

  const active = (config.active as string | null) ?? null;

  const handleActiveChange = async (provider: string | null) => {
    setSaving(true);
    const updated = { ...config, active: provider };
    onUpdate(updated);
    try {
      await saveObservationConfig(provider);
      setSuccessMsg("Saved");
      setTimeout(() => setSuccessMsg(null), 2000);
    } catch (err) {
      console.error("Failed to save observation config:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleFieldSave = async (providerId: string, updatedConfig: Record<string, unknown>) => {
    setSaving(true);
    onUpdate(updatedConfig);
    try {
      await saveObservationConfig(
        updatedConfig.active as string | null,
        { [providerId]: updatedConfig[providerId] },
      );
      setSuccessMsg(providerId);
      setTimeout(() => setSuccessMsg(null), 2000);
    } catch (err) {
      console.error("Failed to save observation config:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const result = await verifyObservation();
      setVerifyResult(result);
    } catch (err) {
      setVerifyResult({ success: false, error: err instanceof Error ? err.message : "Verify failed" });
    } finally {
      setVerifying(false);
    }
  };

  const maskValue = (val: string) => {
    if (!val || val.length <= 8) return "*".repeat(val?.length || 0);
    return val.slice(0, 4) + "*".repeat(Math.min(val.length - 8, 20)) + val.slice(-4);
  };

  const renderField = (providerId: string, field: FieldDef) => {
    const value = getNestedValue(config, field);
    const showKeyId = `${providerId}-${field.key}`;
    const isSecret = field.type === "password";
    const showKey = showKeys[showKeyId] || false;

    return (
      <div className="relative">
        <input
          type={isSecret && !showKey ? "password" : "text"}
          value={isSecret && !showKey ? maskValue(value) : value}
          onChange={(e) => void handleFieldSave(providerId, setNestedValue(config, field, e.target.value))}
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
      {/* Active Provider Selector */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Active Provider
          </h2>
          {saving && <span className="text-xs text-[#0ea5e9] font-medium animate-pulse">Saving...</span>}
          {successMsg === "Saved" && !saving && (
            <div className="flex items-center gap-1 text-xs text-[#10b981] font-medium animate-fadeIn">
              <Check className="w-3.5 h-3.5" /> Saved
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {[{ id: null, label: "None" }, ...OBSERVATION_PROVIDERS.map((p) => ({ id: p.id, label: p.name }))].map((opt) => (
            <button
              key={opt.id ?? "none"}
              onClick={() => void handleActiveChange(opt.id)}
              className={`px-4 py-2 text-sm rounded-lg border transition-all ${
                active === opt.id
                  ? "bg-[#0ea5e9]/10 border-[#0ea5e9] text-[#0ea5e9] font-medium"
                  : "border-[#e2e8f0] text-[#64748b] hover:border-[#94a3b8]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Provider Cards */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-6 bg-gradient-to-b from-[#0ea5e9] to-[#0284c7] rounded-full" />
          <h2 className="text-lg font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            Provider Configuration
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {OBSERVATION_PROVIDERS.map((provider, index) => (
            <div
              key={provider.id}
              className={`border rounded-xl p-5 bg-white transition-all duration-300 space-y-4 ${
                active === provider.id
                  ? "border-[#0ea5e9] shadow-lg shadow-[#0ea5e9]/10"
                  : "border-[#e2e8f0] hover:border-[#0ea5e9] hover:shadow-lg hover:shadow-[#0ea5e9]/10"
              }`}
              style={{ animation: `fadeInUp 0.5s ease-out ${index * 0.1}s both` }}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#1e293b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                  {provider.name}
                </h3>
                {active === provider.id && (
                  <span className="text-xs text-[#0ea5e9] font-medium px-2 py-0.5 bg-[#0ea5e9]/10 rounded-full">Active</span>
                )}
                {successMsg === provider.id && !saving && (
                  <div className="flex items-center gap-1 text-xs text-[#10b981] font-medium animate-fadeIn">
                    <Check className="w-3.5 h-3.5" /> Saved
                  </div>
                )}
              </div>
              {provider.fields.map((field) => (
                <div key={field.key} className="space-y-1">
                  <label className="text-xs font-medium text-[#64748b]">{field.label}</label>
                  {renderField(provider.id, field)}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Verify Button */}
      {active && (
        <div className="space-y-3">
          <button
            onClick={() => void handleVerify()}
            disabled={verifying}
            className="px-4 py-2 bg-[#0ea5e9] text-white text-sm font-medium rounded-lg hover:bg-[#0284c7] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2"
          >
            {verifying ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {verifying ? "Verifying..." : "Verify Connection"}
          </button>
          {verifyResult && (
            <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
              verifyResult.success ? "bg-[#10b981]/10 text-[#10b981]" : "bg-red-50 text-red-600"
            }`}>
              {verifyResult.success ? <Check className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
              <div>
                {verifyResult.success
                  ? `Connected. Found ${(verifyResult.traces as unknown[])?.length ?? 0} recent traces.`
                  : verifyResult.error}
              </div>
            </div>
          )}
        </div>
      )}

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
