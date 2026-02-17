import { Check, ChevronDown, Cpu, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface ModelOption {
  id: string;
  name: string;
  description: string;
  provider?: string;
}

const VIRTUAL_MODELS: ModelOption[] = [
  { id: "leon:mini", name: "Mini", description: "快速响应，简单任务" },
  { id: "leon:medium", name: "Medium", description: "平衡性能，日常任务" },
  { id: "leon:large", name: "Large", description: "复杂推理，困难任务" },
  { id: "leon:max", name: "Max", description: "极限性能，最难任务" },
];

interface ModelSelectorProps {
  currentModel: string;
  threadId: string | null;
  onModelChange?: (model: string) => void;
}

export default function ModelSelector({
  currentModel,
  threadId,
  onModelChange,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCustomModels, setShowCustomModels] = useState(
    () => !VIRTUAL_MODELS.some((m) => m.id === currentModel) && !!currentModel
  );
  const [enabledModels, setEnabledModels] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  // Fetch enabled models when dropdown opens
  useEffect(() => {
    if (!isOpen) return;
    fetch("http://127.0.0.1:8001/api/settings")
      .then((r) => r.json())
      .then((d) => setEnabledModels(d.enabled_models || []))
      .catch(() => {});
  }, [isOpen]);

  async function handleModelSelect(model: string) {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8001/api/settings/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, thread_id: threadId }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to update model");
      }

      const result = await response.json();
      onModelChange?.(result.model || model);
      setIsOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update model");
    } finally {
      setLoading(false);
    }
  }

  const currentModelDisplay = VIRTUAL_MODELS.find((m) => m.id === currentModel)?.name || currentModel;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen((v) => !v)}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#e5e5e5] text-sm text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717] disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Cpu className="w-3.5 h-3.5" />
        <span className="max-w-[120px] truncate">{currentModelDisplay}</span>
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-10 w-64 bg-white rounded-xl border border-[#e5e5e5] shadow-lg z-50 py-1">
          {VIRTUAL_MODELS.map((model) => (
            <button
              key={model.id}
              onClick={() => handleModelSelect(model.id)}
              disabled={loading}
              className="w-full flex items-center justify-between py-2 px-3 hover:bg-[#f5f5f5] disabled:opacity-50 text-left"
            >
              <div>
                <div className="text-sm text-[#171717] font-medium">{model.name}</div>
                <div className="text-[11px] text-[#a3a3a3]">{model.description}</div>
              </div>
              {currentModel === model.id && (
                <Check className="w-4 h-4 text-primary flex-shrink-0 ml-2" />
              )}
            </button>
          ))}

          <div className="border-t my-1" />
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-sm text-muted-foreground">Custom</span>
            <button
              onClick={() => setShowCustomModels(!showCustomModels)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${showCustomModels ? "bg-primary" : "bg-muted"}`}
            >
              <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${showCustomModels ? "translate-x-4" : "translate-x-0.5"}`} />
            </button>
          </div>
          {showCustomModels && enabledModels.map((id) => (
            <button
              key={id}
              onClick={() => handleModelSelect(id)}
              disabled={loading}
              className="w-full flex items-center justify-between py-2 px-3 hover:bg-[#f5f5f5] disabled:opacity-50 text-left"
            >
              <span className="text-sm text-[#171717] truncate">{id}</span>
              {currentModel === id && (
                <Check className="w-4 h-4 text-primary flex-shrink-0 ml-2" />
              )}
            </button>
          ))}

          {error && (
            <div className="mx-3 mt-1 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs text-red-600">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
