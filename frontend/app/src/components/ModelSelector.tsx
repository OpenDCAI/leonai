import { Check, ChevronDown, Cpu, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface ModelOption {
  id: string;
  name: string;
  description: string;
  provider?: string;
}

const VIRTUAL_MODELS: ModelOption[] = [
  { id: "leon:fast", name: "Fast", description: "快速响应，适合简单任务" },
  { id: "leon:balanced", name: "Balanced", description: "平衡性能与成本" },
  { id: "leon:powerful", name: "Powerful", description: "强大推理能力" },
  { id: "leon:coding", name: "Coding", description: "代码生成优化" },
  { id: "leon:research", name: "Research", description: "深度分析研究" },
  { id: "leon:creative", name: "Creative", description: "创意内容生成" },
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
  const [customModel, setCustomModel] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setShowCustomInput(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
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
      setShowCustomInput(false);
      setCustomModel("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update model");
    } finally {
      setLoading(false);
    }
  }

  function handleCustomModelSubmit() {
    if (customModel.trim()) {
      handleModelSelect(customModel.trim());
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
        <div className="absolute right-0 top-10 w-80 bg-white rounded-xl border border-[#e5e5e5] shadow-lg z-50 py-2">
          {/* Virtual Models */}
          <div className="px-4 py-2">
            <div className="text-xs font-medium text-[#a3a3a3] uppercase tracking-wider mb-2">
              预设模型
            </div>
            <div className="space-y-1">
              {VIRTUAL_MODELS.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  disabled={loading}
                  className="w-full flex items-center justify-between py-2 px-2 hover:bg-[#f5f5f5] rounded-lg disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  <div className="text-left flex-1">
                    <div className="text-sm text-[#171717] font-medium">{model.name}</div>
                    <div className="text-[11px] text-[#a3a3a3] mt-0.5">{model.description}</div>
                  </div>
                  {currentModel === model.id && (
                    <Check className="w-4 h-4 text-amber-500 flex-shrink-0 ml-2" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Custom Model Input */}
          <div className="border-t border-[#e5e5e5] mt-2 pt-2 px-4 py-2">
            {!showCustomInput ? (
              <button
                onClick={() => setShowCustomInput(true)}
                className="w-full text-left text-sm text-[#525252] hover:text-[#171717] py-2 px-2 hover:bg-[#f5f5f5] rounded-lg"
              >
                自定义模型...
              </button>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleCustomModelSubmit();
                    } else if (e.key === "Escape") {
                      setShowCustomInput(false);
                      setCustomModel("");
                    }
                  }}
                  placeholder="输入模型名称 (如 gpt-4)"
                  className="w-full px-3 py-2 text-sm border border-[#e5e5e5] rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleCustomModelSubmit}
                    disabled={!customModel.trim() || loading}
                    className="flex-1 px-3 py-1.5 text-sm bg-amber-400 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    确认
                  </button>
                  <button
                    onClick={() => {
                      setShowCustomInput(false);
                      setCustomModel("");
                    }}
                    className="px-3 py-1.5 text-sm border border-[#e5e5e5] rounded-lg hover:bg-[#f5f5f5]"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="mx-4 mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs text-red-600">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
