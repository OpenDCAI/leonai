import { Folder, Settings as SettingsIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import WorkspaceSetupModal from "./WorkspaceSetupModal";
import { useWorkspaceSettings } from "../hooks/use-workspace-settings";

export default function SettingsPanel() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);
  const { settings, refreshSettings } = useWorkspaceSettings();

  // Close popover on outside click
  useEffect(() => {
    if (!settingsOpen) return;
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [settingsOpen]);

  async function handleWorkspaceSet(_workspace: string) {
    await refreshSettings();
    setWorkspaceModalOpen(false);
    setSettingsOpen(false);
  }

  return (
    <>
      <div className="relative" ref={settingsRef}>
        <button
          onClick={() => setSettingsOpen((v) => !v)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717]"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>

        {settingsOpen && (
          <div className="absolute right-0 top-10 w-72 bg-white rounded-xl border border-[#e5e5e5] shadow-lg z-50 py-2">
            {/* Workspace Section */}
            <div className="px-4 py-2">
              <div className="text-xs font-medium text-[#a3a3a3] uppercase tracking-wider mb-3">
                工作区设置
              </div>
              <button
                onClick={() => {
                  setWorkspaceModalOpen(true);
                  setSettingsOpen(false);
                }}
                className="w-full flex items-center gap-3 py-2 hover:bg-[#f5f5f5] rounded-lg px-2 -mx-2"
              >
                <Folder className="w-4 h-4 text-[#737373]" />
                <div className="text-left flex-1">
                  <div className="text-sm text-[#171717]">默认工作区</div>
                  <div className="text-[11px] text-[#a3a3a3] mt-0.5 truncate">
                    {settings?.default_workspace || "未设置"}
                  </div>
                </div>
              </button>
            </div>
          </div>
        )}
      </div>

      <WorkspaceSetupModal
        open={workspaceModalOpen}
        onClose={() => setWorkspaceModalOpen(false)}
        onWorkspaceSet={handleWorkspaceSet}
      />
    </>
  );
}
