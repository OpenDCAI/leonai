import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ModelMappingSection from "../components/ModelMappingSection";
import ModelPoolSection from "../components/ModelPoolSection";
import ProvidersSection from "../components/ProvidersSection";

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
}

export default function SettingsPage() {
  const [availableModels, setAvailableModels] = useState<AvailableModelsData | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [modelsRes, settingsRes] = await Promise.all([
          fetch("http://127.0.0.1:8001/api/settings/available-models"),
          fetch("http://127.0.0.1:8001/api/settings"),
        ]);

        const modelsData = await modelsRes.json();
        const settingsData = await settingsRes.json();

        setAvailableModels(modelsData);
        setSettings(settingsData);
      } catch (error) {
        console.error("Failed to load settings:", error);
      } finally {
        setLoading(false);
      }
    }

    void loadData();
  }, []);

  const handleAddCustomModel = async (modelId: string) => {
    const res = await fetch("http://127.0.0.1:8001/api/settings/models/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId }),
    });
    const data = await res.json();
    if (data.success) {
      // Refresh available models and settings
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
      <div className="h-screen w-screen bg-white flex items-center justify-center">
        <div className="text-[#a3a3a3]">加载中...</div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-[#f8f9fa] to-[#e9ecef] flex flex-col relative overflow-hidden">
      {/* Animated background pattern */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle at 2px 2px, #0ea5e9 1px, transparent 0)',
          backgroundSize: '40px 40px',
          animation: 'patternMove 30s linear infinite'
        }} />
      </div>

      {/* Header */}
      <div className="relative border-b border-[#dee2e6] px-6 py-4 flex items-center gap-4 backdrop-blur-md bg-white/80 shadow-sm">
        <Link
          to="/app"
          className="w-9 h-9 rounded-lg flex items-center justify-center text-[#6c757d] hover:bg-[#0ea5e9]/10 hover:text-[#0ea5e9] transition-all duration-200"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-[#0ea5e9] tracking-tight" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
          Configuration
        </h1>
        <div className="ml-auto flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
          <span className="text-xs text-[#6c757d] font-medium">Connected</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto relative">
        <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
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
            onToggle={(modelId, enabled) => {
              const newEnabled = enabled
                ? [...settings.enabled_models, modelId]
                : settings.enabled_models.filter((id) => id !== modelId);
              setSettings({ ...settings, enabled_models: newEnabled });
            }}
            onAddCustomModel={handleAddCustomModel}
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
        </div>
      </div>

      <style>{`
        @keyframes patternMove {
          0% { transform: translate(0, 0); }
          100% { transform: translate(40px, 40px); }
        }
      `}</style>
    </div>
  );
}
