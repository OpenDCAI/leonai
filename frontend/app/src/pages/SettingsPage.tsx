import { ArrowLeft, Box, Cpu } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ModelMappingSection from "../components/ModelMappingSection";
import ModelPoolSection from "../components/ModelPoolSection";
import ProvidersSection from "../components/ProvidersSection";
import SandboxSection from "../components/SandboxSection";

interface AvailableModelsData {
  models: Array<{
    id: string;
    name: string;
    custom?: boolean;
  }>;
  virtual_models: Array<{
    id: string;
    name: string;
    description: string;
    icon: string;
  }>;
}

interface Settings {
  model_mapping: Record<string, string>;
  enabled_models: string[];
  providers: Record<string, { api_key: string | null; base_url: string | null }>;
  default_workspace: string | null;
}

type Tab = "model" | "sandbox";

const TABS: { id: Tab; label: string; icon: typeof Cpu; desc: string }[] = [
  { id: "model", label: "Model", icon: Cpu, desc: "Models, providers & mapping" },
  { id: "sandbox", label: "Sandbox", icon: Box, desc: "Execution environments" },
];

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("model");
  const [availableModels, setAvailableModels] = useState<AvailableModelsData | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [sandboxes, setSandboxes] = useState<Record<string, Record<string, unknown>>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [modelsRes, settingsRes, sandboxesRes] = await Promise.all([
          fetch("http://127.0.0.1:8001/api/settings/available-models"),
          fetch("http://127.0.0.1:8001/api/settings"),
          fetch("http://127.0.0.1:8001/api/settings/sandboxes"),
        ]);

        const modelsData = await modelsRes.json();
        const settingsData = await settingsRes.json();
        const sandboxesData = await sandboxesRes.json();

        setAvailableModels(modelsData);
        setSettings(settingsData);
        setSandboxes(sandboxesData.sandboxes || {});
      } catch (error) {
        console.error("Failed to load settings:", error);
      } finally {
        setLoading(false);
      }
    }

    void loadData();
  }, []);

  const handleAddCustomModel = async (modelId: string, provider?: string) => {
    const res = await fetch("http://127.0.0.1:8001/api/settings/models/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId, provider: provider || null }),
    });
    const data = await res.json();
    if (data.success) {
      const [modelsRes, settingsRes] = await Promise.all([
        fetch("http://127.0.0.1:8001/api/settings/available-models"),
        fetch("http://127.0.0.1:8001/api/settings"),
      ]);
      setAvailableModels(await modelsRes.json());
      setSettings(await settingsRes.json());
    }
  };

  if (loading || !availableModels || !settings) {
    return (
      <div className="h-screen w-screen bg-gradient-to-br from-[#f8f9fa] to-[#e9ecef] flex items-center justify-center">
        <div className="text-[#a3a3a3]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-[#f8f9fa] to-[#e9ecef] flex items-center justify-center relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle at 2px 2px, #0ea5e9 1px, transparent 0)',
          backgroundSize: '40px 40px',
          animation: 'patternMove 30s linear infinite'
        }} />
      </div>

      {/* Floating centered panel */}
      <div
        className="relative w-[960px] max-w-[95vw] h-[85vh] rounded-2xl border border-[#e2e8f0] bg-white/90 backdrop-blur-xl shadow-xl flex overflow-hidden"
        style={{ animation: 'scaleIn 0.3s ease-out' }}
      >
        {/* Left nav */}
        <div className="w-[200px] shrink-0 border-r border-[#e2e8f0] bg-[#f8f9fa]/80 flex flex-col">
          <div className="px-4 py-5 border-b border-[#e2e8f0]">
            <div className="flex items-center gap-2 mb-1">
              <Link
                to="/app"
                className="w-7 h-7 rounded-lg flex items-center justify-center text-[#94a3b8] hover:bg-[#0ea5e9]/10 hover:text-[#0ea5e9] transition-all duration-200"
              >
                <ArrowLeft className="w-4 h-4" />
              </Link>
              <span className="text-sm font-bold text-[#0ea5e9] tracking-tight" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                Settings
              </span>
            </div>
          </div>

          <div className="flex-1 px-3 py-4 space-y-1">
            {TABS.map((t) => {
              const Icon = t.icon;
              const active = tab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                    active
                      ? "bg-white shadow-sm border border-[#e2e8f0]"
                      : "hover:bg-white/60"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${active ? "text-[#0ea5e9]" : "text-[#94a3b8] group-hover:text-[#64748b]"}`} />
                    <span className={`text-sm font-medium ${active ? "text-[#1e293b]" : "text-[#64748b] group-hover:text-[#1e293b]"}`}>
                      {t.label}
                    </span>
                  </div>
                  <p className={`text-[11px] mt-0.5 ml-[26px] ${active ? "text-[#94a3b8]" : "text-[#cbd5e1]"}`}>
                    {t.desc}
                  </p>
                </button>
              );
            })}
          </div>

          <div className="px-4 py-3 border-t border-[#e2e8f0]">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
              <span className="text-[11px] text-[#94a3b8]">Connected</span>
            </div>
          </div>
        </div>

        {/* Right content */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-8 py-8 space-y-6">
            {tab === "model" && (
              <>
                <ModelMappingSection
                  virtualModels={availableModels.virtual_models}
                  availableModels={availableModels.models}
                  modelMapping={settings.model_mapping}
                  enabledModels={settings.enabled_models}
                  onUpdate={(mapping) => setSettings({ ...settings, model_mapping: mapping })}
                />
                <ModelPoolSection
                  models={availableModels.models}
                  enabledModels={settings.enabled_models}
                  providers={settings.providers}
                  onToggle={(modelId, enabled) => {
                    const newEnabled = enabled
                      ? [...settings.enabled_models, modelId]
                      : settings.enabled_models.filter((id) => id !== modelId);
                    setSettings({ ...settings, enabled_models: newEnabled });
                  }}
                  onAddCustomModel={handleAddCustomModel}
                  onRemoveCustomModel={async (modelId) => {
                    const res = await fetch(`http://127.0.0.1:8001/api/settings/models/custom?model_id=${encodeURIComponent(modelId)}`, {
                      method: "DELETE",
                    });
                    const data = await res.json();
                    if (data.success) {
                      const [modelsRes, settingsRes] = await Promise.all([
                        fetch("http://127.0.0.1:8001/api/settings/available-models"),
                        fetch("http://127.0.0.1:8001/api/settings"),
                      ]);
                      setAvailableModels(await modelsRes.json());
                      setSettings(await settingsRes.json());
                    }
                  }}
                />
                <ProvidersSection
                  providers={settings.providers}
                  onUpdate={(provider, config) => {
                    setSettings({
                      ...settings,
                      providers: { ...settings.providers, [provider]: config },
                    });
                  }}
                />
              </>
            )}

            {tab === "sandbox" && (
              <SandboxSection
                sandboxes={sandboxes}
                defaultWorkspace={settings.default_workspace}
                onUpdate={(name, config) => {
                  setSandboxes({ ...sandboxes, [name]: config });
                }}
                onWorkspaceChange={(ws) => setSettings({ ...settings, default_workspace: ws })}
              />
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes patternMove {
          0% { transform: translate(0, 0); }
          100% { transform: translate(40px, 40px); }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.97); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
