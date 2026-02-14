import "./App.css";
import ChatArea from "./components/ChatArea";
import ComputerPanel from "./components/ComputerPanel";
import { DragHandle } from "./components/DragHandle";
import Header from "./components/Header";
import InputBox from "./components/InputBox";
import NewThreadModal from "./components/NewThreadModal";
import SandboxSessionsModal from "./components/SandboxSessionsModal";
import SearchModal from "./components/SearchModal";
import Sidebar from "./components/Sidebar";
import TaskProgress from "./components/TaskProgress";
import { useAppActions } from "./hooks/use-app-actions";
import { useResizableX } from "./hooks/use-resizable-x";
import { useSandboxManager } from "./hooks/use-sandbox-manager";
import { useStreamHandler } from "./hooks/use-stream-handler";
import { useThreadManager } from "./hooks/use-thread-manager";

export default function App() {
  // --- Data layer ---
  const tm = useThreadManager();
  const {
    threads, activeThreadId, entries, activeSandbox, sandboxTypes, loading,
    setActiveThreadId, setEntries, setThreads,
    loadThread, refreshThreads, handleCreateThread, handleDeleteThread,
  } = tm;

  // --- Streaming ---
  const { isStreaming, streamTurnId, runtimeStatus, handleSendMessage, handleStopStreaming } =
    useStreamHandler({
      activeThreadId,
      selectedSandbox: tm.selectedSandbox,
      setEntries,
      setThreads,
      setActiveThreadId,
      loadThread,
      refreshThreads,
    });

  // --- Sandbox actions ---
  const { sandboxActionError, handlePauseSandbox, handleResumeSandbox } =
    useSandboxManager({
      activeThreadId,
      isStreaming,
      activeSandbox,
      setActiveSandbox: tm.setActiveSandbox,
      loadThread,
    });

  // --- UI state + misc actions ---
  const ui = useAppActions({ activeThreadId, setEntries });
  const {
    queueEnabled, computerOpen, computerTab, focusedAgentStepId,
    sidebarCollapsed, searchOpen, newThreadOpen, sessionsOpen,
    setComputerOpen, setComputerTab, setFocusedAgentStepId,
    setSidebarCollapsed, setSearchOpen, setNewThreadOpen, setSessionsOpen,
    handleFocusAgent, handleSendQueueMessage, handleToggleQueue,
  } = ui;

  // --- Resize handles ---
  const sidebarResize = useResizableX(272, 200, 420);
  const computerResize = useResizableX(600, 360, 1200, true);

  return (
    <div className="h-screen w-screen bg-white flex overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        collapsed={sidebarCollapsed}
        loading={loading}
        width={sidebarResize.width}
        onSelectThread={setActiveThreadId}
        onCreateThread={() => setNewThreadOpen(true)}
        onDeleteThread={(id) => void handleDeleteThread(id)}
        onSearchClick={() => setSearchOpen(true)}
      />
      {!sidebarCollapsed && <DragHandle onMouseDown={sidebarResize.onMouseDown} />}

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activeThreadId={activeThreadId}
          threadPreview={threads.find((t) => t.thread_id === activeThreadId)?.preview ?? null}
          sandboxInfo={activeSandbox}
          queueEnabled={queueEnabled}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          onPauseSandbox={() => void handlePauseSandbox()}
          onResumeSandbox={() => void handleResumeSandbox()}
          onToggleQueue={() => void handleToggleQueue()}
        />

        <div className="flex-1 flex min-h-0">
          <div className="flex-1 flex flex-col min-w-0">
            {sandboxActionError && (
              <div className="px-3 py-2 text-xs bg-red-50 text-red-600 border-b border-red-200">
                {sandboxActionError}
              </div>
            )}
            <ChatArea entries={entries} isStreaming={isStreaming} streamTurnId={streamTurnId} runtimeStatus={runtimeStatus} loading={loading} onFocusAgent={handleFocusAgent} />
            {activeThreadId && (
              <TaskProgress
                isStreaming={isStreaming}
                runtimeStatus={runtimeStatus}
                sandboxType={activeSandbox?.type ?? "local"}
                sandboxStatus={activeSandbox?.status ?? (activeSandbox?.type === "local" ? "running" : null)}
                computerOpen={computerOpen}
                onToggleComputer={() => setComputerOpen((v) => !v)}
              />
            )}
            <InputBox
              disabled={isStreaming}
              isStreaming={isStreaming}
              queueEnabled={queueEnabled}
              placeholder={activeThreadId ? "告诉 Leon 你需要什么帮助..." : "新建会话后开始对话"}
              onSendMessage={handleSendMessage}
              onSendQueueMessage={activeThreadId ? handleSendQueueMessage : undefined}
              onStop={handleStopStreaming}
            />
          </div>

          {computerOpen && (
            <>
              <DragHandle onMouseDown={computerResize.onMouseDown} />
              <ComputerPanel
                isOpen={computerOpen}
                onClose={() => setComputerOpen(false)}
                threadId={activeThreadId}
                sandboxType={activeSandbox?.type ?? null}
                chatEntries={entries}
                width={computerResize.width}
                activeTab={computerTab}
                onTabChange={setComputerTab}
                focusedAgentStepId={focusedAgentStepId}
                onFocusAgent={setFocusedAgentStepId}
              />
            </>
          )}
        </div>
      </div>

      <NewThreadModal
        open={newThreadOpen}
        sandboxTypes={sandboxTypes}
        onClose={() => setNewThreadOpen(false)}
        onCreate={(sandbox, cwd) => {
          setNewThreadOpen(false);
          void handleCreateThread(sandbox, cwd);
        }}
      />

      <SearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        threads={threads}
        onSelectThread={(threadId) => setActiveThreadId(threadId)}
      />

      <SandboxSessionsModal
        isOpen={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        onSessionMutated={(threadId) => {
          if (activeThreadId === threadId) {
            void loadThread(threadId);
          }
          void refreshThreads();
        }}
      />
    </div>
  );
}
