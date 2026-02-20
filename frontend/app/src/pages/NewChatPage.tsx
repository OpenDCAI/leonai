import { useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { postRun } from "../api";
import CenteredInputBox from "../components/CenteredInputBox";
import WorkspaceSetupModal from "../components/WorkspaceSetupModal";
import type { ThreadManagerState, ThreadManagerActions } from "../hooks/use-thread-manager";
import { useWorkspaceSettings } from "../hooks/use-workspace-settings";

interface OutletContext {
  tm: ThreadManagerState & ThreadManagerActions;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (value: boolean) => void;
  setSessionsOpen: (value: boolean) => void;
}

export default function NewChatPage() {
  const navigate = useNavigate();
  const { tm } = useOutletContext<OutletContext>();
  const { sandboxTypes, selectedSandbox, handleCreateThread } = tm;
  const { settings, loading, setDefaultWorkspace, hasWorkspace } = useWorkspaceSettings();
  const [showWorkspaceSetup, setShowWorkspaceSetup] = useState(false);

  async function handleSend(message: string, sandbox: string, model: string, workspace?: string) {
    // For local sandbox, check if workspace is set
    if (sandbox === "local" && !workspace && !hasWorkspace) {
      setShowWorkspaceSetup(true);
      return;
    }

    const cwd = workspace || settings?.default_workspace || undefined;
    const threadId = await handleCreateThread(sandbox, cwd);
    console.log('[NewChatPage] Created thread:', threadId, 'posting run:', message);
    await postRun(threadId, message, undefined, model ? { model } : undefined);
    navigate(`/app/${threadId}`, {
      state: { selectedModel: model, runStarted: true },
    });
  }

  function handleWorkspaceSet(workspace: string) {
    setShowWorkspaceSetup(false);
    // Workspace is now set, user can try sending again
  }

  if (loading) {
    return null;
  }

  return (
    <div className="flex-1 flex items-center justify-center relative">
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px]">
        {/* Welcome Section */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-medium text-[#171717] mb-2">
            你好，我是 Leon
          </h1>
          <p className="text-sm text-[#737373] mb-6">
            你的通用数字员工，随时准备为你工作
          </p>

          {/* Capability Tags */}
          <div className="flex flex-wrap justify-center gap-2">
            <div className="px-3 py-1.5 bg-[#fafafa] border border-[#e5e5e5] rounded-lg text-xs text-[#525252]">
              文件操作
            </div>
            <div className="px-3 py-1.5 bg-[#fafafa] border border-[#e5e5e5] rounded-lg text-xs text-[#525252]">
              代码探索
            </div>
            <div className="px-3 py-1.5 bg-[#fafafa] border border-[#e5e5e5] rounded-lg text-xs text-[#525252]">
              命令执行
            </div>
            <div className="px-3 py-1.5 bg-[#fafafa] border border-[#e5e5e5] rounded-lg text-xs text-[#525252]">
              信息检索
            </div>
          </div>
        </div>

        {/* Input Box */}
        <CenteredInputBox
          sandboxTypes={sandboxTypes}
          defaultSandbox={selectedSandbox}
          defaultWorkspace={settings?.default_workspace || undefined}
          defaultModel={settings?.default_model || "leon:large"}
          recentWorkspaces={settings?.recent_workspaces || []}
          enabledModels={settings?.enabled_models || []}
          onSend={handleSend}
        />
      </div>

      <WorkspaceSetupModal
        open={showWorkspaceSetup}
        onClose={() => setShowWorkspaceSetup(false)}
        onWorkspaceSet={handleWorkspaceSet}
      />
    </div>
  );
}
