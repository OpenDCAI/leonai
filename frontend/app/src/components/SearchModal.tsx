import { Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ThreadSummary } from "../api";

interface SearchModalProps {
  isOpen: boolean;
  threads: ThreadSummary[];
  onClose: () => void;
  onSelectThread: (threadId: string) => void;
}

export default function SearchModal({ isOpen, threads, onClose, onSelectThread }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter((t) => t.thread_id.toLowerCase().includes(q) || (t.sandbox ?? "local").toLowerCase().includes(q));
  }, [query, threads]);

  useEffect(() => {
    if (!isOpen) return;
    setQuery("");
    setSelectedIndex(0);
  }, [isOpen]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (filtered.length === 0 ? 0 : (prev + 1) % filtered.length));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (filtered.length === 0 ? 0 : (prev - 1 + filtered.length) % filtered.length));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        onSelectThread(filtered[selectedIndex].thread_id);
        onClose();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [filtered, isOpen, onClose, onSelectThread, selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-[640px] max-h-[520px] bg-[#242424] border border-[#333] rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333]">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="搜索 thread id 或 sandbox..."
            className="flex-1 bg-transparent text-white text-sm placeholder-gray-500 outline-none"
          />
          <button className="w-6 h-6 rounded hover:bg-[#333] flex items-center justify-center transition-colors" onClick={onClose}>
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
        <div className="max-h-[440px] overflow-y-auto py-2">
          {filtered.map((thread, index) => (
            <button
              key={thread.thread_id}
              className={`w-full px-4 py-2.5 text-left transition-colors ${index === selectedIndex ? "bg-[#2a2a2a]" : "hover:bg-[#2a2a2a]"}`}
              onClick={() => {
                onSelectThread(thread.thread_id);
                onClose();
              }}
            >
              <div className="text-sm text-white font-mono">{thread.thread_id}</div>
              <div className="text-xs text-gray-500 mt-0.5">{thread.sandbox ?? "local"}</div>
            </button>
          ))}
          {filtered.length === 0 && <p className="px-4 py-8 text-center text-sm text-gray-500">未找到匹配线程</p>}
        </div>
      </div>
    </div>
  );
}
