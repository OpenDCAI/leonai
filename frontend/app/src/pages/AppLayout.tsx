import { useState } from "react";
import { Outlet } from "react-router-dom";
import { DragHandle } from "../components/DragHandle";
import NewThreadModal from "../components/NewThreadModal";
import SandboxSessionsModal from "../components/SandboxSessionsModal";
import SearchModal from "../components/SearchModal";
import Sidebar from "../components/Sidebar";
import { useResizableX } from "../hooks/use-resizable-x";
import { useThreadManager } from "../hooks/use-thread-manager";

export default function AppLayout() {
  const tm = useThreadManager();
  const {
    threads, sandboxTypes, loading,
    refreshThreads, handleCreateThread, handleDeleteThread,
  } = tm;

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [newThreadOpen, setNewThreadOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);

  const sidebarResize = useResizableX(272, 200, 420);

  return (
    <div className="h-full w-full bg-background flex overflow-hidden">
      <Sidebar
        threads={threads}
        collapsed={sidebarCollapsed}
        loading={loading}
        width={sidebarResize.width}
        onDeleteThread={(id) => void handleDeleteThread(id)}
        onSearchClick={() => setSearchOpen(true)}
      />
      {!sidebarCollapsed && <DragHandle onMouseDown={sidebarResize.onMouseDown} />}

      <div className="flex-1 flex flex-col min-w-0">
        <Outlet context={{ tm, sidebarCollapsed, setSidebarCollapsed, setSessionsOpen }} />
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
        onSelectThread={() => {}}
      />

      <SandboxSessionsModal
        isOpen={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        onSessionMutated={() => {
          void refreshThreads();
        }}
      />
    </div>
  );
}
