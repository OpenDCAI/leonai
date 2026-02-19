import { useEffect, useRef, useState } from "react";
import { useParams, useOutletContext, useLocation } from "react-router-dom";
import ChatArea from "../components/ChatArea";
import ComputerPanel from "../components/ComputerPanel";
import { DragHandle } from "../components/DragHandle";
import Header from "../components/Header";
import InputBox from "../components/InputBox";
import TaskProgress from "../components/TaskProgress";
import TokenStats from "../components/TokenStats";
import { useAppActions } from "../hooks/use-app-actions";
import { useResizableX } from "../hooks/use-resizable-x";
import { useSandboxManager } from "../hooks/use-sandbox-manager";
import { useStreamHandler } from "../hooks/use-stream-handler";
import { useThreadData } from "../hooks/use-thread-data";
import type { ThreadManagerState, ThreadManagerActions } from "../hooks/use-thread-manager";

interface OutletContext {
  tm: ThreadManagerState & ThreadManagerActions;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  setSessionsOpen: (value: boolean) => void;
}

export default function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const location = useLocation();
  const { tm, setSidebarCollapsed } = useOutletContext<OutletContext>();
  const initialMessageSent = useRef(false);
  const [currentModel, setCurrentModel] = useState<string>("");

  // Check if we have an initial message to send
  const state = location.state as { initialMessage?: string; selectedModel?: string } | null;
  const hasInitialMessage = !!state?.initialMessage;

  // Set initial model from location state, then thread runtime, then global settings
  useEffect(() => {
    if (state?.selectedModel) {
      setCurrentModel(state.selectedModel);
      // Persist to thread metadata
      if (threadId) {
        void fetch("http://127.0.0.1:8001/api/settings/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: state.selectedModel, thread_id: threadId }),
        });
      }
    } else if (threadId) {
      // Try thread-specific model first
      fetch(`http://127.0.0.1:8001/api/threads/${threadId}/runtime`)
        .then((r) => r.json())
        .then((d) => {
          if (d.model) {
            setCurrentModel(d.model);
          } else {
            // Fallback to global default model
            return fetch("http://127.0.0.1:8001/api/settings")
              .then((r) => r.json())
              .then((d) => setCurrentModel(d.default_model || "leon:large"));
          }
        })
        .catch(() => setCurrentModel("leon:large"));
    }
  }, [state?.selectedModel, threadId]);

  const { entries, activeSandbox, loading, setEntries, setActiveSandbox, refreshThread } = useThreadData(threadId, hasInitialMessage);

  const { isStreaming, streamTurnId, runtimeStatus, handleSendMessage, handleStopStreaming } =
    useStreamHandler({
      threadId: threadId ?? "",
      refreshThreads: tm.refreshThreads,
      onUpdate: (updater) => setEntries(updater),
      loading,
    });

  // Handle initial message - send immediately without waiting for loading
  useEffect(() => {
    if (state?.initialMessage && threadId && !initialMessageSent.current) {
      initialMessageSent.current = true;
      const message = state.initialMessage;
      console.log('[ChatPage] Sending initial message immediately:', message);
      window.history.replaceState({}, document.title);
      void handleSendMessage(message);
    }
  }, [state?.initialMessage, threadId, handleSendMessage, setEntries]);

  const { sandboxActionError, handlePauseSandbox, handleResumeSandbox } =
    useSandboxManager({
      activeThreadId: threadId ?? null,
      isStreaming,
      activeSandbox,
      setActiveSandbox,
      loadThread: refreshThread,
    });

  const ui = useAppActions({ activeThreadId: threadId ?? null, setEntries });
  const {
    queueEnabled, computerOpen, computerTab, focusedAgentStepId,
    setComputerOpen, setComputerTab, setFocusedAgentStepId,
    handleFocusAgent, handleSendQueueMessage, handleToggleQueue,
  } = ui;

  const computerResize = useResizableX(600, 360, 1200, true);

  if (!threadId) {
    return null;
  }

  return (
    <>
      <Header
        activeThreadId={threadId}
        threadPreview={tm.threads.find((t) => t.thread_id === threadId)?.preview ?? null}
        sandboxInfo={activeSandbox}
        queueEnabled={queueEnabled}
        currentModel={currentModel}
        onToggleSidebar={() => setSidebarCollapsed(v => !v)}
        onPauseSandbox={() => void handlePauseSandbox()}
        onResumeSandbox={() => void handleResumeSandbox()}
        onToggleQueue={() => void handleToggleQueue()}
        onModelChange={setCurrentModel}
      />

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 flex flex-col min-w-0">
          {sandboxActionError && (
            <div className="px-3 py-2 text-xs bg-red-50 text-red-600 border-b border-red-200">
              {sandboxActionError}
            </div>
          )}
          <ChatArea
            entries={entries}
            isStreaming={isStreaming}
            streamTurnId={streamTurnId}
            runtimeStatus={runtimeStatus}
            loading={loading}
            onFocusAgent={handleFocusAgent}
          />
          <TaskProgress
            isStreaming={isStreaming}
            runtimeStatus={runtimeStatus}
            sandboxType={activeSandbox?.type ?? "local"}
            sandboxStatus={activeSandbox?.status ?? (activeSandbox?.type === "local" ? "running" : null)}
            computerOpen={computerOpen}
            onToggleComputer={() => setComputerOpen((v) => !v)}
          />
          <InputBox
            disabled={isStreaming}
            isStreaming={isStreaming}
            queueEnabled={queueEnabled}
            placeholder="告诉 Leon 你需要什么帮助..."
            onSendMessage={(msg) => void handleSendMessage(msg)}
            onSendQueueMessage={handleSendQueueMessage}
            onStop={handleStopStreaming}
          />
          <TokenStats runtimeStatus={runtimeStatus} />
        </div>

        {computerOpen && (
          <>
            <DragHandle onMouseDown={computerResize.onMouseDown} />
            <ComputerPanel
              key={threadId}
              isOpen={computerOpen}
              onClose={() => setComputerOpen(false)}
              threadId={threadId}
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
    </>
  );
}
